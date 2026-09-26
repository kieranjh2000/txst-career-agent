"""
TXST Career Readiness Competency Discovery Agent -- Web Application (Streamlit)

A web interface that helps Texas State University students identify which of the
8 Career Readiness Competencies (grounded in TXST Career Services terminology,
including Advocacy & Compassion) their experiences demonstrate, backed by exact
evidence quotes and behavioral justifications.
"""

import datetime
import json
import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
import streamlit as st

from competencies import valid_competency_names
from prompts import build_completeness_prompt, build_mapping_prompt

# ---------------------------------------------------------------------------
# Configuration & Credentials
# ---------------------------------------------------------------------------
load_dotenv()

# Check environment variables first, then fallback to Streamlit Cloud secrets
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY and hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]

# Test Access Control Configuration
ACCESS_CODE = os.environ.get("APP_ACCESS_CODE")
if not ACCESS_CODE and hasattr(st, "secrets") and "APP_ACCESS_CODE" in st.secrets:
    ACCESS_CODE = st.secrets["APP_ACCESS_CODE"]
if not ACCESS_CODE:
    ACCESS_CODE = "BOBCATS2026"  # Default test access code for class evaluation

PRIMARY_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.6-flash")
MAX_API_RETRIES = 2

LOGS_DIR = Path(__file__).parent / "logs"
LOG_FILE_TXT = LOGS_DIR / "interactions.log"
LOG_FILE_JSONL = LOGS_DIR / "interactions.jsonl"

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


def try_model(client: genai.Client, model: str, prompt: str, json_mode: bool = True) -> Optional[str]:
    config = {"response_mime_type": "application/json"} if json_mode else None
    for attempt in range(1, MAX_API_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
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


def call_gemini(client: genai.Client, prompt: str, json_mode: bool = True) -> str:
    result = try_model(client, PRIMARY_MODEL, prompt, json_mode=json_mode)
    if result is not None:
        return result

    if FALLBACK_MODEL and FALLBACK_MODEL != PRIMARY_MODEL:
        result = try_model(client, FALLBACK_MODEL, prompt, json_mode=json_mode)
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
        raw = call_gemini(client, build_completeness_prompt(experience_text))
        result = parse_json_response(raw)
    except Exception:
        return {"complete": True, "follow_up_questions": []}
    if not isinstance(result, dict) or "complete" not in result:
        return {"complete": True, "follow_up_questions": []}
    return result


def map_competencies(client: genai.Client, experience_text: str) -> dict:
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
            if entered_code.strip() == ACCESS_CODE:
                st.session_state.authenticated = True
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
    st.caption("🔒 **Test Session Active**")
    if st.button("Lock / Exit Session"):
        st.session_state.authenticated = False
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
with col_clear:
    if st.button("🔄 Reset"):
        st.session_state.experience_text = ""
        st.session_state.results = None
        st.session_state.pending_questions = []
        st.session_state.previous_names = set()
        st.session_state.updates_history = []
        st.session_state.show_diff = False
        st.rerun()

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
        st.session_state.experience_text = user_input.strip()
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
    st.info("📋 **A couple quick questions to help pin down your evidence:**")
    followup_answers = []
    with st.form("followup_form"):
        for idx, q in enumerate(st.session_state.pending_questions):
            ans = st.text_input(f"{idx + 1}. {q}", key=f"q_{idx}")
            followup_answers.append(ans)
        
        c1, c2 = st.columns([1, 1])
        with c1:
            submit_followups = st.form_submit_button("Submit Answers & Analyze", type="primary")
        with c2:
            skip_followups = st.form_submit_button("Skip to Analysis")

    if submit_followups:
        additional_info = " ".join([ans.strip() for ans in followup_answers if ans.strip()])
        if additional_info:
            full_narrative = f"{st.session_state.experience_text}\n\nAdditional details provided:\n{additional_info}"
            st.session_state.updates_history.append(f"Follow-up details: {additional_info}")
        else:
            full_narrative = st.session_state.experience_text

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
        with st.spinner("Mapping competencies based on initial description..."):
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
        elif not competencies:
            st.info(
                "ℹ️ **Update Processed:** We added your clarification, but simply stating 'I had an internship' "
                "still lacks specific projects, actions, tools, or measurable outcomes. "
                "Try describing what tasks you personally worked on or what problem you solved!"
            )
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
                    # Ready-to-use resume bullet point
                    bullet = f"• Demonstrated {comp.get('name')} by leveraging: {comp.get('evidence')} ({comp.get('justification')})"
                    st.text_input(
                        "📋 Copyable Resume Bullet:",
                        value=f"• {comp.get('justification')} as demonstrated when: \"{comp.get('evidence')}\"",
                        key=f"bullet_{i}",
                    )

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
                st.session_state.previous_names = current_names
                st.session_state.updates_history.append(update_text.strip())
                updated_narrative = (
                    f"{st.session_state.experience_text}\n\n"
                    f"Student clarification/update:\n{update_text.strip()}"
                )
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
