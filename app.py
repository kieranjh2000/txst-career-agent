"""
TXST Career Readiness Competency Discovery Agent -- Web Application (Streamlit)

A web interface that helps Texas State University students identify which of the
8 Career Readiness Competencies (grounded in TXST Career Services terminology,
including Advocacy & Compassion) their experiences demonstrate, backed by exact
evidence quotes and behavioral justifications.
"""

import csv
import datetime
import json
import os
import re
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
import streamlit as st

from competencies import valid_competency_names
from prompts import (
    build_completeness_prompt,
    build_completeness_user_content,
    build_mapping_prompt,
    build_mapping_user_content,
    get_completeness_system_instruction,
    get_mapping_system_instruction,
)

# ---------------------------------------------------------------------------
# Configuration & Credentials
# ---------------------------------------------------------------------------
load_dotenv()


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Safely fetch a key from environment variables or Streamlit secrets without crashing."""
    val = os.environ.get(key)
    if val:
        return val
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return default


API_KEY = get_secret("GEMINI_API_KEY")
ACCESS_CODE = get_secret("APP_ACCESS_CODE", "BOBCATS2026")
DEV_ACCESS_CODE = get_secret("APP_DEV_CODE", "DEV2026")
STAFF_ACCESS_CODE = get_secret("APP_STAFF_CODE", "TXSTSTAFF2026")

# Rate limiting & token drainage protection parameters
MAX_INPUT_CHARS = 3500  # Character ceiling (protects against token drainage)
SUBMISSION_COOLDOWN_SECONDS = 15  # Cooldown between API calls for standard users

PRIMARY_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")



FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.6-flash")
MAX_API_RETRIES = 2

LOGS_DIR = Path(__file__).parent / "logs"
LOG_FILE_TXT = LOGS_DIR / "interactions.log"
LOG_FILE_JSONL = LOGS_DIR / "interactions.jsonl"
CSV_REPORTS_FILE = LOGS_DIR / "internship_connections_reports.csv"
CSV_HEADERS = [
    "Timestamp",
    "NetID",
    "Major",
    "Semester",
    "Organization",
    "Role_Title",
    "Competencies_Identified",
    "Executive_Summary",
    "Consent_Granted",
]


# ---------------------------------------------------------------------------
# Page Styling & Title
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="TXST Career Competency Discovery Agent",
    page_icon="🎓",
    layout="wide",
)

# Custom TXST Maroon accent styling
st.markdown(
    """
    <style>
    .main-header {
        color: #501214;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #4a4a4a;
        font-size: 1.1rem;
        margin-bottom: 1.5rem;
    }
    .competency-card {
        background-color: #ffffff !important;
        color: #111827 !important;
        border-left: 6px solid #501214 !important;
        padding: 1.2rem !important;
        border-radius: 6px !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2) !important;
    }
    .competency-card h3 {
        color: #501214 !important;
        font-size: 1.3rem !important;
        font-weight: 700 !important;
        margin-top: 0 !important;
        margin-bottom: 0.5rem !important;
    }
    .competency-card p, 
    .competency-card strong, 
    .competency-card span, 
    .competency-card div {
        color: #1f2937 !important;
    }
    .quote-box {
        background-color: #f3f4f6 !important;
        color: #111827 !important;
        border-left: 4px solid #501214 !important;
        padding: 0.75rem 1rem !important;
        margin: 0.5rem 0 !important;
        font-style: italic !important;
        border-radius: 4px !important;
        line-height: 1.5 !important;
    }
    .advisor-callout {
        background-color: #ffffff !important;
        color: #111827 !important;
        border: 2px solid #501214 !important;
        padding: 1.2rem !important;
        border-radius: 6px !important;
        margin-top: 1rem !important;
    }
    .advisor-callout h4, 
    .advisor-callout p, 
    .advisor-callout a {
        color: #111827 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Backend AI Engine & Resilient Fallback
# ---------------------------------------------------------------------------
def get_client(api_key: str) -> Optional[genai.Client]:
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        st.error(f"Error initializing Gemini client: {e}")
        return None


def is_daily_quota_error(e: genai_errors.APIError) -> bool:
    code = getattr(e, "code", None) or getattr(e, "status_code", None)
    message = str(e).lower()
    return code == 429 and "per day" in message.replace("perday", "per day")


def try_model(
    client: genai.Client,
    model: str,
    prompt: str,
    json_mode: bool = True,
    system_instruction: Optional[str] = None,
) -> Optional[str]:
    config = {"response_mime_type": "application/json"} if json_mode else {}
    if system_instruction:
        config["system_instruction"] = system_instruction
    cfg = config if config else None

    for attempt in range(1, MAX_API_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=cfg,
            )
            return response.text or ""
        except genai_errors.APIError as e:
            if is_daily_quota_error(e):
                return None
            if attempt < MAX_API_RETRIES:
                time.sleep(2 * attempt)
        except Exception:
            if attempt < MAX_API_RETRIES:
                time.sleep(2 * attempt)
    return None


def call_gemini(
    client: genai.Client,
    prompt: str,
    json_mode: bool = True,
    system_instruction: Optional[str] = None,
) -> str:
    result = try_model(client, PRIMARY_MODEL, prompt, json_mode=json_mode, system_instruction=system_instruction)
    if result is not None:
        return result

    if FALLBACK_MODEL and FALLBACK_MODEL != PRIMARY_MODEL:
        result = try_model(client, FALLBACK_MODEL, prompt, json_mode=json_mode, system_instruction=system_instruction)
        if result is not None:
            return result

    raise RuntimeError("Gemini API unavailable after retries and fallback")


def parse_json_response(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}


def check_completeness(client: genai.Client, experience_text: str) -> dict:
    try:
        raw = call_gemini(
            client,
            prompt=build_completeness_user_content(experience_text),
            system_instruction=get_completeness_system_instruction(),
        )
        result = parse_json_response(raw)
    except Exception:
        try:
            raw = call_gemini(client, build_completeness_prompt(experience_text))
            result = parse_json_response(raw)
        except Exception:
            return {"complete": True, "follow_up_questions": []}
    if not isinstance(result, dict) or "complete" not in result:
        return {"complete": True, "follow_up_questions": []}
    return result


def map_competencies(client: genai.Client, experience_text: str) -> dict:
    try:
        raw = call_gemini(
            client,
            prompt=build_mapping_user_content(experience_text),
            system_instruction=get_mapping_system_instruction(),
        )
        result = parse_json_response(raw)
    except Exception:
        try:
            raw = call_gemini(client, build_mapping_prompt(experience_text))
            result = parse_json_response(raw)
        except Exception:
            return {
                "competencies": [],
                "summary": "Service was temporarily unavailable to complete the competency analysis.",
            }
    if not isinstance(result, dict):
        result = {}
    result.setdefault("competencies", [])
    result.setdefault("summary", "")

    valid_names = valid_competency_names()
    result["competencies"] = [
        c for c in result["competencies"] if isinstance(c, dict) and c.get("name") in valid_names
    ]
    return result
def log_interaction(initial_text: str, final_text: str, results: dict, updates: Optional[list] = None) -> None:
    try:
        LOGS_DIR.mkdir(exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        competencies = results.get("competencies", [])

        with open(LOG_FILE_TXT, "a", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write(f"SESSION TIMESTAMP: {timestamp}\n")
            f.write("=" * 70 + "\n")
            f.write(f"INITIAL EXPERIENCE:\n{initial_text.strip()}\n\n")
            if updates:
                f.write("UPDATES / CORRECTIONS:\n")
                for u in updates:
                    f.write(f"  * {u}\n")
                f.write("\n")
            f.write("IDENTIFIED COMPETENCIES:\n")
            if not competencies:
                f.write("  (No competencies identified)\n")
            for c in competencies:
                f.write(f"  * {c.get('name')}\n")
                f.write(f"      Evidence: {c.get('evidence')}\n")
                f.write(f"      Why it counts: {c.get('justification')}\n")
            if results.get("summary"):
                f.write(f"\nSUMMARY:\n{results.get('summary')}\n")
            f.write("=" * 70 + "\n\n")

        with open(LOG_FILE_JSONL, "a", encoding="utf-8") as f:
            record = {
                "timestamp": timestamp,
                "initial_experience": initial_text,
                "final_experience": final_text,
                "updates": updates or [],
                "results": results,
            }
            f.write(json.dumps(record) + "\n")
    except Exception:
        # Logging failure should never crash the user-facing web app
        pass


def save_internship_report(
    net_id: str,
    major: str,
    semester: str,
    organization: str,
    role_title: str,
    competencies_list: list,
    executive_summary: str,
) -> bool:
    """Save an authorized student internship record to the Internship Connections CSV file."""
    try:
        LOGS_DIR.mkdir(exist_ok=True)
        file_exists = CSV_REPORTS_FILE.exists()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        competencies_str = "; ".join(competencies_list) if isinstance(competencies_list, list) else str(competencies_list)

        with open(CSV_REPORTS_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(CSV_HEADERS)
            writer.writerow([
                timestamp,
                net_id.strip(),
                major.strip(),
                semester.strip(),
                organization.strip(),
                role_title.strip(),
                competencies_str,
                executive_summary.strip(),
                "TRUE",
            ])
        return True
    except Exception:
        return False


def is_valid_txst_netid(net_id: str) -> tuple[bool, str]:
    """Validate Texas State University NetID format.
    
    A valid TXST NetID consists of 2 to 4 letters (student initials),
    optionally an underscore, followed by 1 to 6 digits (e.g., abc123, zz99, kjh12, k_j123).
    """
    cleaned = net_id.strip()
    if not cleaned:
        return False, "NetID cannot be blank."

    # Detect if user accidentally entered a TXST Student ID (A-number, e.g., A01234567)
    if re.match(r"^[aA]\d{8}$", cleaned):
        return (
            False,
            "That looks like your Texas State Student ID (A-Number, e.g. A01234567). "
            "Please enter your Texas State NetID instead (e.g. abc123 or kjh12).",
        )

    # Standard Texas State NetID pattern: 2 to 4 letters, optional underscore, 1 to 6 digits
    pattern = r"^[a-zA-Z]{2,4}_?\d{1,6}$"
    if not re.match(pattern, cleaned):
        return (
            False,
            f"'{cleaned}' is not a valid Texas State NetID. "
            "NetIDs start with 2 to 4 letters followed by numbers (such as abc123 or kjh12). "
            "Please correct your NetID to proceed.",
        )

    return True, ""


if "staff_authenticated" not in st.session_state:
    st.session_state.staff_authenticated = False

# ---------------------------------------------------------------------------
# Sidebar UI: Framework & Configuration
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image(
        "https://www.txst.edu/etc.clientlibs/txstate-platform/clientlibs/clientlib-site/resources/img/txstate-logo.svg",
        width=200,
    )
    st.title("TXST Career Services")
    st.markdown(
        "This tool helps Bobcat students identify and articulate **Career Readiness Competencies** developed through internships, coursework, jobs, and leadership."
    )

    st.markdown("---")
    st.subheader("8 Approved Competencies")
    with st.expander("View Approved Rubric"):
        st.markdown(
            """
            * **Career & Self-Development**
            * **Communication**
            * **Critical Thinking**
            * **Leadership**
            * **Professionalism**
            * **Teamwork**
            * **Technology**
            * **Advocacy & Compassion** *(TXST adaptation)*
            """
        )

    st.markdown("---")
    st.subheader("Human Career Advising")
    st.markdown("Need personalized 1-on-1 resume coaching or interview prep?")
    st.link_button(
        "📅 Book an Advisor Appointment",
        "https://www.careerservices.txst.edu/students-alumni/appointments.html",
        use_container_width=True,
    )

    # ---------------------------------------------------------------------------
    # Staff Portal: Role-Based Access Control (FERPA Protection)
    # ---------------------------------------------------------------------------
    st.markdown("---")
    with st.expander("🔒 Career Services Staff Portal", expanded=st.session_state.staff_authenticated):
        st.caption("🛡️ **FERPA Protected:** Access to student NetIDs and internship records requires a staff PIN.")
        if not st.session_state.staff_authenticated:
            staff_pin = st.text_input(
                "Enter Staff PIN:",
                type="password",
                key="staff_pin_input",
                placeholder="Staff PIN required",
            )
            if st.button("Unlock Staff Portal", type="secondary"):
                if staff_pin.strip() == STAFF_ACCESS_CODE:
                    st.session_state.staff_authenticated = True
                    st.toast("Staff access granted!")
                    st.rerun()
                else:
                    st.error("❌ Invalid Staff PIN.")
        else:
            st.success("✅ Authorized: Staff Access Active")
            if st.button("Lock Staff Portal", type="secondary"):
                st.session_state.staff_authenticated = False
                st.rerun()

            st.markdown("---")
            st.subheader("📊 Submitted Internship Records")
            if CSV_REPORTS_FILE.exists():
                with open(CSV_REPORTS_FILE, "r", encoding="utf-8") as f:
                    csv_data = f.read()
                st.download_button(
                    label="📥 Download All Records (CSV)",
                    data=csv_data,
                    file_name="txst_internship_connections_reports.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
                with st.expander("👀 View Records Table"):
                    try:
                        import pandas as pd
                        df_reports = pd.read_csv(CSV_REPORTS_FILE)
                        st.dataframe(df_reports, use_container_width=True)
                    except Exception:
                        st.text(csv_data)
            else:
                st.caption("No student reports submitted yet.")



    # API Key Input Override (useful if not preconfigured on the server)
    st.markdown("---")
    custom_key = st.text_input(
        "Gemini API Key (optional override)",
        value=API_KEY or "",
        type="password",
        help="Leave blank if preconfigured in server environment variables or .env",
    )
    effective_api_key = custom_key.strip() if custom_key else API_KEY


# ---------------------------------------------------------------------------
# Access Control (Restricted Test Environment)
# ---------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "is_developer" not in st.session_state:
    st.session_state.is_developer = False
if "last_api_call_time" not in st.session_state:
    st.session_state.last_api_call_time = 0.0

if not st.session_state.authenticated:
    st.markdown('<div class="main-header">🔒 Restricted Test Environment</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">TXST Career Readiness Discovery Agent (Evaluation Build)</div>',
        unsafe_allow_html=True,
    )
    
    st.info("This application is currently in an authorized testing phase. Please enter the test access code to proceed.")
    
    with st.form("access_gate_form"):
        entered_code = st.text_input("Enter Test Access Code:", type="password", placeholder="Enter code here")
        submitted = st.form_submit_button("Unlock Agent", type="primary")
        
        if submitted:
            cleaned_code = entered_code.strip()
            if cleaned_code == DEV_ACCESS_CODE:
                st.session_state.authenticated = True
                st.session_state.is_developer = True
                st.success("🛠️ Developer access granted! Rate limits and cooldowns disabled.")
                st.rerun()
            elif cleaned_code == ACCESS_CODE:
                st.session_state.authenticated = True
                st.session_state.is_developer = False
                st.success("Access granted!")
                st.rerun()
            else:
                st.error("❌ Incorrect access code. Please check with the project author or course instructor.")
    
    st.caption("⚠️ **Note:** This access code is a lightweight test gate intended for academic evaluation and course grading, not enterprise security.")
    st.stop()


# ---------------------------------------------------------------------------
# Main UI Application
# ---------------------------------------------------------------------------
with st.sidebar:
    if st.session_state.get("is_developer", False):
        st.markdown(
            """
            <div style="background-color:#FEF3C7; border-left:4px solid #D97706; padding:0.6rem; border-radius:4px; margin-bottom:0.8rem;">
                <strong style="color:#92400E;">🛠️ Developer Mode Active</strong><br>
                <small style="color:#B45309;">Rate limiting and cooldown timers bypassed for testing.</small>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.caption("🔒 **Test Session Active (Standard Rate Limits Apply)**")
    if st.button("Lock / Exit Session"):
        st.session_state.authenticated = False
        st.session_state.is_developer = False
        st.rerun()

st.markdown('<div class="main-header">TXST Career Readiness Discovery Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Discover which Career Competencies you developed in your experience, backed by concrete evidence for your resume and interviews.</div>',
    unsafe_allow_html=True,
)

if not effective_api_key:
    st.warning(
        "⚠️ No Gemini API key detected. Please configure `GEMINI_API_KEY` in your environment, Streamlit Secrets, or enter it in the sidebar to begin."
    )
    st.stop()

client = get_client(effective_api_key)


# Initialize Session State
if "experience_text" not in st.session_state:
    st.session_state.experience_text = ""
if "pending_questions" not in st.session_state:
    st.session_state.pending_questions = []
if "results" not in st.session_state:
    st.session_state.results = None
if "previous_names" not in st.session_state:
    st.session_state.previous_names = set()
if "updates_history" not in st.session_state:
    st.session_state.updates_history = []
if "show_diff" not in st.session_state:
    st.session_state.show_diff = False
if "internship_reported" not in st.session_state:
    st.session_state.internship_reported = False
if "followup_round" not in st.session_state:
    st.session_state.followup_round = 0


# Quick Sample Buttons
col_sample1, col_sample2, col_clear = st.columns([1.5, 1.5, 1])
with col_sample1:
    if st.button("💡 Example: Technical Project"):
        st.session_state.experience_text = (
            "During my summer analytics internship at a logistics company, I noticed the team spent 5 hours every Monday "
            "manually copying inventory numbers between Excel spreadsheets. I wrote a Python script using pandas to "
            "automate data extraction, cleaning, and reconciliation. This reduced our weekly reporting time from 5 hours to "
            "15 minutes and completely eliminated manual transcription errors."
        )
        st.session_state.results = None
        st.session_state.pending_questions = []
        st.session_state.show_diff = False
        st.session_state.internship_reported = False
with col_sample2:
    if st.button("💡 Example: Team Leadership"):
        st.session_state.experience_text = (
            "In my senior capstone project at Texas State, our 4-person team fell two weeks behind schedule due to confusion "
            "over project responsibilities. I organized weekly 15-minute standup meetings, established a shared Trello board "
            "to track deliverables, and facilitated a discussion to resolve conflicting opinions on our presentation slides. "
            "As a result, our team submitted the final deliverable 3 days ahead of the deadline and received an A."
        )
        st.session_state.results = None
        st.session_state.pending_questions = []
        st.session_state.show_diff = False
        st.session_state.internship_reported = False
with col_clear:
    if st.button("🔄 Reset"):
        st.session_state.experience_text = ""
        st.session_state.results = None
        st.session_state.pending_questions = []
        st.session_state.previous_names = set()
        st.session_state.updates_history = []
        st.session_state.show_diff = False
        st.session_state.internship_reported = False
        st.session_state.followup_round = 0
        st.rerun()


def check_rate_limits(user_text: str) -> tuple[bool, str]:
    """Enforce character ceilings and cooldown timers to prevent token drainage."""
    if st.session_state.get("is_developer", False):
        return True, ""  # Developer bypass

    # 1. Character Ceiling Check
    if len(user_text.strip()) > MAX_INPUT_CHARS:
        return (
            False,
            f"⚠️ Your description exceeds the maximum limit ({len(user_text.strip())} / {MAX_INPUT_CHARS} characters). "
            f"Please keep your text under {MAX_INPUT_CHARS} characters to protect server capacity."
        )

    # 2. Cooldown Timer Check
    now = time.time()
    elapsed = now - st.session_state.get("last_api_call_time", 0.0)
    if elapsed < SUBMISSION_COOLDOWN_SECONDS:
        remaining = int(SUBMISSION_COOLDOWN_SECONDS - elapsed)
        return (
            False,
            f"⏳ Cooldown active: Please wait {remaining} more second{'s' if remaining != 1 else ''} "
            f"before submitting another request to prevent token exhaustion."
        )

    return True, ""


def generate_portfolio_markdown(summary: str, competencies: list, experience_text: str) -> str:
    """Generate a clean, professional Texas State Career Readiness Portfolio export."""
    now_str = datetime.datetime.now().strftime("%B %d, %Y")
    lines = [
        "=" * 70,
        "TEXAS STATE UNIVERSITY - MCCOY COLLEGE OF BUSINESS",
        "CAREER READINESS COMPETENCY PORTFOLIO",
        f"Generated on: {now_str}",
        "=" * 70,
        "",
        "EXECUTIVE SUMMARY:",
        summary if summary else "Demonstrated career readiness competencies through real-world experience.",
        "",
        "-" * 70,
        "IDENTIFIED CAREER READINESS COMPETENCIES & RESUME BULLETS:",
        "-" * 70,
        "",
    ]

    for i, c in enumerate(competencies, start=1):
        name = c.get("name", "Competency")
        evidence = c.get("evidence", "").strip()
        justification = c.get("justification", "").strip()
        bullet = c.get("resume_bullet", "").strip()
        if not bullet:
            clean_just = justification[4:] if justification.lower().startswith("you ") else justification
            bullet = clean_just if clean_just else f"Demonstrated {name} through verifiable project experience."
        if not bullet.startswith("•") and not bullet.startswith("-"):
            bullet = f"• {bullet}"

        lines.extend([
            f"{i}. COMPETENCY: {name.upper()}",
            f"   Evidence Quote : \"{evidence}\"",
            f"   Why It Counts  : {justification}",
            f"   Resume Bullet  : {bullet}",
            "",
        ])

    lines.extend([
        "-" * 70,
        "ORIGINAL STUDENT EXPERIENCE DESCRIPTION:",
        "-" * 70,
        experience_text.strip(),
        "",
        "=" * 70,
        "Texas State Career Services | LBJ Student Center, 5th Floor",
        "Appointments & Handshake: https://www.careerservices.txst.edu/appointments.html",
        "=" * 70,
    ])

    return "\n".join(lines)

# Experience Input Form
user_input = st.text_area(
    "Describe your experience (job, internship, class project, student org, leadership moment, or volunteer work):",
    value=st.session_state.experience_text,
    height=160,
    placeholder="Example: What was your role? What challenges did you tackle? What tools did you use? What was the outcome?",
)

if st.button("🚀 Analyze Experience", type="primary"):
    if not user_input.strip():
        st.error("Please enter a description of your experience first.")
    else:
        can_proceed, limit_msg = check_rate_limits(user_input)
        if not can_proceed:
            st.warning(limit_msg)
        else:
            st.session_state.last_api_call_time = time.time()
            st.session_state.experience_text = user_input.strip()
            st.session_state.followup_round = 0
            with st.spinner("Checking completeness against Texas State Career evaluation rules..."):
                completeness = check_completeness(client, st.session_state.experience_text)

        if not completeness.get("complete", True) and completeness.get("follow_up_questions"):
            st.session_state.pending_questions = completeness["follow_up_questions"]
            st.session_state.results = None
        else:
            st.session_state.pending_questions = []
            with st.spinner("Evaluating career readiness competencies with Google Gemini..."):
                results = map_competencies(client, st.session_state.experience_text)
                st.session_state.results = results
                log_interaction(
                    st.session_state.experience_text,
                    st.session_state.experience_text,
                    results,
                    st.session_state.updates_history,
                )
        st.rerun()


# ---------------------------------------------------------------------------
# Follow-Up Probing Section (Rule 5: Completeness Threshold)
# ---------------------------------------------------------------------------
if st.session_state.pending_questions and st.session_state.results is None:
    round_label = f" (Round {st.session_state.followup_round + 1})" if st.session_state.followup_round > 0 else ""
    st.info(f"📋 **Follow-up Questions to Pin Down Strong Evidence{round_label}:**\n\nTake your time to share details. If you would rather proceed directly to analysis, click 'Skip to Analysis'.")
    followup_answers = []
    with st.form(f"followup_form_{st.session_state.followup_round}"):
        for idx, q in enumerate(st.session_state.pending_questions):
            ans = st.text_input(f"{idx + 1}. {q}", key=f"q_{st.session_state.followup_round}_{idx}")
            followup_answers.append(ans)
        
        c1, c2 = st.columns([1, 1])
        with c1:
            submit_followups = st.form_submit_button("Submit Answers & Continue", type="primary")
        with c2:
            skip_followups = st.form_submit_button("Skip to Analysis")

    if submit_followups:
        additional_info = " ".join([ans.strip() for ans in followup_answers if ans.strip()])
        if additional_info:
            full_narrative = f"{st.session_state.experience_text}\n\nAdditional details provided:\n{additional_info}"
            st.session_state.experience_text = full_narrative
            st.session_state.updates_history.append(f"Follow-up details (Round {st.session_state.followup_round + 1}): {additional_info}")
        else:
            full_narrative = st.session_state.experience_text

        st.session_state.followup_round += 1
        MAX_FOLLOWUP_ROUNDS = 3

        # Patient exploration: If below round ceiling, re-evaluate if more specifics are needed
        if st.session_state.followup_round < MAX_FOLLOWUP_ROUNDS and additional_info:
            with st.spinner("Reviewing your additional details for evidence completeness..."):
                completeness = check_completeness(client, full_narrative)
            if not completeness.get("complete", True) and completeness.get("follow_up_questions"):
                st.session_state.pending_questions = completeness["follow_up_questions"]
                st.rerun()

        # Narrative is substantive or round ceiling reached -> proceed to mapping
        with st.spinner("Mapping competencies with your additional details..."):
            results = map_competencies(client, full_narrative)
            st.session_state.results = results
            st.session_state.pending_questions = []
            log_interaction(
                st.session_state.experience_text,
                full_narrative,
                results,
                st.session_state.updates_history,
            )
            st.rerun()

    if skip_followups:
        with st.spinner("Mapping competencies based on current description..."):
            results = map_competencies(client, st.session_state.experience_text)
            st.session_state.results = results
            st.session_state.pending_questions = []
            log_interaction(
                st.session_state.experience_text,
                st.session_state.experience_text,
                results,
                st.session_state.updates_history,
            )
            st.rerun()


# ---------------------------------------------------------------------------
# Results Display
# ---------------------------------------------------------------------------
if st.session_state.results:
    results = st.session_state.results
    competencies = results.get("competencies", [])
    summary = results.get("summary", "")
    current_names = {c.get("name") for c in competencies}

    st.markdown("---")
    st.subheader("🎯 Career Competency Analysis")

    # Show Diff if this was an update
    if st.session_state.show_diff:
        added = current_names - st.session_state.previous_names
        removed = st.session_state.previous_names - current_names
        if added or removed:
            st.markdown("#### 🔄 What changed in this update:")
            if added:
                st.success(f"➕ **New Competency Added:** {', '.join(added)}")
            if removed:
                st.warning(f"➖ **Competency Removed:** {', '.join(removed)}")

        else:
            st.info("ℹ️ **Update Processed:** No change in identified competencies.")

    # Unsupported Case Handling (Rule 2 & Rule 6)
    if not competencies:
        st.warning(
            "**I couldn't clearly identify an approved TXST career competency in that description yet.**"
        )
        if summary:
            st.markdown(f"**Feedback:** {summary}")
        
        st.markdown(
            """
            <div class="advisor-callout">
                <h4 style="color:#501214 !important; margin-top:0;">🤝 Human Career Advising Referral</h4>
                <p style="color:#1f2937 !important;">If you're unsure how to frame this experience, or if it involves complex circumstances, 
                we recommend scheduling a 1-on-1 session with a Texas State Career Services advisor.</p>
                <p style="margin-top:0.5rem;"><a href="https://www.careerservices.txst.edu/students-alumni/appointments.html" target="_blank" style="color:#501214 !important; font-weight:bold; text-decoration:underline;">
                👉 Click here to schedule an appointment with a TXST Career Advisor</a></p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Supported Case Results Display
        if summary:
            st.markdown(f"**Executive Summary:** {summary}")
            st.markdown("")

        cols = st.columns(2)
        for i, comp in enumerate(competencies):
            with cols[i % 2]:
                with st.container():
                    st.markdown(
                        f"""
                        <div class="competency-card">
                            <h3 style="color:#501214 !important; margin-top:0;">🌟 {comp.get('name')}</h3>
                            <p style="color:#1f2937 !important; margin-bottom:0.2rem;"><strong style="color:#111827 !important;">Evidence:</strong></p>
                            <div class="quote-box" style="color:#111827 !important;">"{comp.get('evidence')}"</div>
                            <p style="color:#1f2937 !important; margin-top:0.6rem;"><strong style="color:#111827 !important;">Why it counts:</strong> {comp.get('justification')}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    # Ready-to-use professional resume bullet point (Action-Verb format)
                    raw_bullet = comp.get("resume_bullet", "").strip()
                    if raw_bullet:
                        if not raw_bullet.startswith("•") and not raw_bullet.startswith("-"):
                            bullet_value = f"• {raw_bullet}"
                        else:
                            bullet_value = raw_bullet
                    else:
                        # Fallback cleaner formula if model omits the key: Action verb without 'You'
                        clean_just = comp.get('justification', '').strip()
                        if clean_just.lower().startswith("you "):
                            clean_just = clean_just[4:]
                            clean_just = clean_just[0].upper() + clean_just[1:] if clean_just else clean_just
                        bullet_value = f"• {clean_just}" if clean_just else f"• Demonstrated {comp.get('name')} through: {comp.get('evidence')}"

                    st.text_input(
                        "📋 Copyable Resume Bullet (Action-Verb Format):",
                        value=bullet_value,
                        key=f"bullet_{i}",
                        help="Formatted using standard Career Services guidelines (Action Verb + Context + Result). No 'You' or personal pronouns.",
                    )

        # One-Click Export: Official TXST Career Readiness Portfolio
        st.markdown("")
        col_dl1, col_dl2 = st.columns([1.5, 1])
        with col_dl1:
            portfolio_text = generate_portfolio_markdown(summary, competencies, st.session_state.experience_text)
            st.download_button(
                label="📥 Download Official TXST Career Portfolio (.txt / Markdown)",
                data=portfolio_text,
                file_name=f"TXST_Career_Portfolio_{datetime.datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                help="Download a clean, structured copy of your competencies, verified evidence quotes, and ready-to-use resume bullets to bring to interviews or advising sessions.",
                type="secondary",
                use_container_width=True,
            )
        with col_dl2:
            st.caption("💡 *Take this portfolio to your 1-on-1 McCoy Career Center advising appointments or use it for job applications.*")

    # ---------------------------------------------------------------------------
    # Experiential Learning Reporting: TXST Internship Connections
    # ---------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("💼 Report Internship to TXST Career Services")
    st.markdown(
        "Did this experience take place as an **internship or co-op**? "
        "Texas State Career Services (**Internship Connections**) tracks experiential learning data to help future Bobcats connect with top employers and support university placement benchmarks."
    )

    if st.session_state.get("internship_reported", False):
        st.success("✅ **Thank you!** Your internship record has been submitted to the Texas State Internship Connections registry.")
    else:
        share_permission = st.checkbox(
            "🙋 Yes, I give permission to share this internship record with Texas State Career Services (Internship Connections).",
            key="share_internship_consent",
        )
        if share_permission:
            with st.form("internship_reporting_form"):
                st.markdown("##### 📝 Student & Internship Details (Mandatory for Institutional Records)")
                c_netid, c_major = st.columns(2)
                with c_netid:
                    net_id_input = st.text_input(
                        "Texas State NetID *",
                        placeholder="e.g., abc123 or kjh12",
                        help="Format: 2–4 letters followed by numbers (e.g. abc123 or kjh12)",
                    )
                with c_major:
                    major_input = st.text_input(
                        "Academic Major / Degree Program *",
                        placeholder="e.g., MS Data Analytics, Computer Science, Finance",
                    )

                c_term, c_org, c_role = st.columns([1.2, 1.4, 1.4])
                with c_term:
                    semester_input = st.selectbox(
                        "Semester Completed *",
                        ["Summer 2026", "Spring 2026", "Fall 2025", "Summer 2025", "Spring 2025", "Other / Prior"],
                    )
                with c_org:
                    org_input = st.text_input("Organization / Employer *", placeholder="e.g., Dell Technologies, H-E-B, Frost Bank")
                with c_role:
                    role_input = st.text_input("Role / Job Title *", placeholder="e.g., Data Analytics Intern")

                st.caption(
                    f"Validated Competencies to be recorded: **{', '.join(current_names) if current_names else 'General Experiential Learning'}**"
                )
                
                submit_report = st.form_submit_button("📤 Submit to TXST Internship Connections", type="primary")

                if submit_report:
                    if not net_id_input.strip() or not major_input.strip() or not org_input.strip() or not role_input.strip():
                        st.error("❌ Please complete all required fields: NetID, Major, Organization, and Role Title.")
                    else:
                        is_valid_netid, netid_error = is_valid_txst_netid(net_id_input)
                        if not is_valid_netid:
                            st.error(f"❌ {netid_error}")
                        else:
                            success = save_internship_report(
                                net_id=net_id_input.strip().lower(),
                                major=major_input,
                                semester=semester_input,
                                organization=org_input,
                                role_title=role_input,
                                competencies_list=list(current_names),
                                executive_summary=summary,
                            )
                            if success:
                                st.session_state.internship_reported = True
                                st.toast("Internship reported to TXST Career Services!")
                                st.rerun()
                            else:
                                st.error("Could not save the internship record. Please try again.")

    # ---------------------------------------------------------------------------
    # Iterative Refinement & Human Correction (Rule 3)
    # ---------------------------------------------------------------------------
    st.markdown("---")
    with st.expander("✏️ Add or Clarify Something About This Experience", expanded=True):

        st.markdown(
            "If you want to add more details, clarify a project responsibility, or correct an interpretation:"
        )
        update_text = st.text_area(
            "What would you like to add or change?",
            key="update_input",
            placeholder="Example: I forgot to mention that I also trained 3 interns on this process and created the documentation.",
        )
        if st.button("Update Analysis", type="secondary"):
            if not update_text.strip():
                st.warning("Please type what you would like to add or clarify before updating.")
            else:
                can_proceed, limit_msg = check_rate_limits(update_text)
                if not can_proceed:
                    st.warning(limit_msg)
                else:
                    st.session_state.last_api_call_time = time.time()
                    st.session_state.previous_names = current_names
                st.session_state.updates_history.append(update_text.strip())
                updated_narrative = (
                    f"{st.session_state.experience_text}\n\n"
                    f"Student clarification/update:\n{update_text.strip()}"
                )
                st.session_state.experience_text = updated_narrative

                # First run completeness check on the updated narrative.
                # If the update introduces a new, vague experience, probe with follow-ups rather than failing.
                with st.spinner("Checking completeness with your updates..."):
                    completeness = check_completeness(client, updated_narrative)

                if not completeness.get("complete", True) and completeness.get("follow_up_questions"):
                    st.session_state.pending_questions = completeness["follow_up_questions"]
                    st.session_state.results = None
                    st.session_state.show_diff = False
                    st.toast("Update received! A few quick questions to help unpack your experience.")
                    st.rerun()
                else:
                    with st.spinner("Re-evaluating with your updates..."):
                        updated_results = map_competencies(client, updated_narrative)
                        st.session_state.results = updated_results
                        st.session_state.show_diff = True
                        log_interaction(
                            st.session_state.experience_text,
                            updated_narrative,
                            updated_results,
                            st.session_state.updates_history,
                        )
                        st.toast("Analysis updated!")
                        st.rerun()
