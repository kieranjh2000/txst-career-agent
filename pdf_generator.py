"""
PDF Generation Module for TXST Career Readiness Discovery Agent.

Produces a branded, professional Career Readiness Audit & Student Growth Plan PDF:
- TXST Maroon (#501214) & Gold (#8D734A) palette.
- NACE Career Readiness Framework alignment.
- Unofficial student self-reflection disclaimer.
- Section 1: Earned competencies with quotes, justifications, and action-verb resume bullets.
- Section 2: Competency gap analysis with actionable NACE-aligned next steps for unearned competencies.
- Section 3: Human Career Advising referral and Handshake scheduling details.
"""

import datetime
from fpdf import FPDF
from competencies import NACE_COMPETENCIES, valid_competency_names

# TXST Palette (RGB)
TXST_MAROON = (80, 18, 20)      # #501214
TXST_GOLD = (141, 115, 74)       # #8D734A
DARK_GRAY = (31, 41, 55)        # #1F2937
MEDIUM_GRAY = (75, 85, 99)      # #4B5563
LIGHT_BG = (248, 249, 250)      # #F8F9FA
BORDER_GRAY = (229, 231, 235)   # #E5E7EB
WHITE = (255, 255, 255)

# Actionable NACE guidance for each of the 8 competencies
NACE_DEVELOPMENT_GUIDE = {
    "Career & Self-Development": [
        "Take a career or strengths assessment (e.g. CliftonStrengths) via TXST Career Services to clarify core talents.",
        "Set 2-3 SMART personal development goals each semester and track milestone achievements.",
        "Attend McCoy Career Center networking nights or connect with Bobcat alumni on LinkedIn for informational interviews."
    ],
    "Communication": [
        "Deliver class presentations or join a campus organization like Toastmasters at TXST to refine public speaking.",
        "Practice synthesizing complex ideas into concise executive summaries or written project briefs.",
        "Exercise active listening in group projects: summarize peer perspectives before responding to ensure clarity."
    ],
    "Critical Thinking": [
        "Tackle multi-variable analytical case studies in your coursework or participate in 3-Day Startup / business pitch events.",
        "Practice evaluating competing solutions using objective decision matrices, cost-benefit models, or risk analyses.",
        "Synthesize academic research or quantitative survey data to back up strategic project recommendations."
    ],
    "Advocacy & Compassion": [
        "Engage in community outreach through university service initiatives like Bobcat Build or local community non-profits.",
        "Participate in student organization dialogue forums to broaden awareness of diverse lived experiences.",
        "Practice empathetic problem-solving and de-escalation techniques when mediating differing viewpoints in group work."
    ],
    "Leadership": [
        "Volunteer to serve as project manager or milestone coordinator for an academic team project.",
        "Seek an officer or committee chair position within a TXST student organization or Greek life chapter.",
        "Participate in the TXST Leadership Institute workshops to cultivate coaching, delegation, and team empowerment skills."
    ],
    "Professionalism": [
        "Attend McCoy Career Fairs dressed in professional business attire with an updated resume.",
        "Establish disciplined personal accountability: meet deadlines early and proactively communicate project status updates.",
        "Seek candid constructive feedback from professors or supervisors after major projects and implement suggestions."
    ],
    "Teamwork": [
        "Collaborate deliberately with peers possessing complementary skillsets on multi-disciplinary team projects.",
        "Establish shared team norms, transparent division of responsibilities, and collaborative documentation tools early.",
        "Acknowledge and praise teammates' contributions regularly to build high psychological safety and trust."
    ],
    "Technology": [
        "Pursue in-demand digital certifications (e.g., Excel Specialist, Google Analytics, SQL, Python, or AWS fundamentals).",
        "Automate a repetitive academic or workplace workflow using spreadsheet macros, scripting, or no-code productivity tools.",
        "Explore and ethically leverage modern cloud collaboration platforms and AI productivity tools in coursework."
    ],
}


def sanitize_text(text: str) -> str:
    """Clean text to ensure 100% compatibility with standard Latin-1 PDF fonts."""
    if not text:
        return ""
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "--",
        "\u2022": "-",
        "\u2026": "...",
        "\u00a0": " ",
        "\u2122": "TM",
        "\u00ae": "(R)",
        "\u00a9": "(C)",
        "\u2011": "-",
        "\u2012": "-",
        "\u2015": "--",
        "\u2039": "<",
        "\u203a": ">",
        "\u00ab": "<<",
        "\u00bb": ">>",
        "\u00b4": "'",
        "`": "'",
        "•": "-",
        "🌟": "",
        "📋": "",
        "💼": "",
        "🤝": "",
        "ℹ️": "",
        "✅": "",
        "💡": "",
        "👉": "",
        "📄": "",
        "📥": "",
        "⏳": "",
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    
    # Strip any remaining characters outside latin-1
    return text.encode("latin-1", "replace").decode("latin-1")


class CareerRoadmapPDF(FPDF):
    """Custom FPDF document styled with TXST branding and NACE framework aesthetics."""

    def header(self):
        # We handle header manually on page 1 for a richer hero banner
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(*MEDIUM_GRAY)
        page_str = f"Page {self.page_no()} of {{nb}}"
        self.cell(0, 8, sanitize_text(page_str), align="C")


def generate_career_roadmap_pdf(summary: str, competencies: list, experience_text: str) -> bytes:
    """
    Generate a polished TXST Maroon & Gold PDF Career Readiness Audit & Growth Plan.
    Returns the binary PDF bytes ready for st.download_button.
    """
    pdf = CareerRoadmapPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.alias_nb_pages()
    pdf.add_page()

    page_width = 210 - (pdf.l_margin + pdf.r_margin)  # usable width (approx 190mm)

    # -------------------------------------------------------------------------
    # HERO HEADER BANNER (TXST Maroon with Gold Accent)
    # -------------------------------------------------------------------------
    pdf.set_fill_color(*TXST_MAROON)
    pdf.rect(0, 0, 210, 36, style="F")

    # Gold accent stripe
    pdf.set_fill_color(*TXST_GOLD)
    pdf.rect(0, 36, 210, 2.5, style="F")

    # Banner Title
    pdf.set_xy(10, 8)
    pdf.set_font("helvetica", "B", 15)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 8, sanitize_text("CAREER READINESS AUDIT & STUDENT GROWTH PLAN"), ln=True, align="C")

    # Banner Subtitle
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(240, 230, 210)  # Pale gold tint
    pdf.cell(0, 6, sanitize_text("In Alignment with NACE Career Competencies | Texas State University"), ln=True, align="C")

    pdf.set_y(43)

    # -------------------------------------------------------------------------
    # UNOFFICIAL DISCLAIMER CALLOUT
    # -------------------------------------------------------------------------
    now_str = datetime.datetime.now().strftime("%B %d, %Y")
    pdf.set_fill_color(*LIGHT_BG)
    pdf.set_draw_color(*BORDER_GRAY)
    pdf.set_line_width(0.3)
    
    disclaimer_text = (
        f"Date: {now_str}  |  Status: Completed Student Experience Evaluation\n"
        "Disclaimer: This document is an automated developmental reflection tool powered by the TXST "
        "Career Readiness Discovery Agent and the NACE (National Association of Colleges & Employers) "
        "Competency Framework. It is intended for student self-development, interview preparation, and "
        "career advising discussions. It is not an official Texas State University transcript or certification."
    )
    pdf.set_font("helvetica", "I", 8)
    pdf.set_text_color(*MEDIUM_GRAY)
    pdf.multi_cell(page_width, 4.2, sanitize_text(disclaimer_text), border=1, fill=True, align="L")
    pdf.ln(4)

    # -------------------------------------------------------------------------
    # EXECUTIVE SUMMARY SECTION
    # -------------------------------------------------------------------------
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(*TXST_MAROON)
    pdf.cell(0, 7, sanitize_text("EXECUTIVE SUMMARY"), ln=True)
    
    # Thin gold underline
    curr_x, curr_y = pdf.get_x(), pdf.get_y()
    pdf.set_draw_color(*TXST_GOLD)
    pdf.set_line_width(0.6)
    pdf.line(curr_x, curr_y, curr_x + page_width, curr_y)
    pdf.ln(2)

    summary_content = summary if summary else "Demonstrated career readiness competencies through verifiable experiential learning."
    pdf.set_font("helvetica", "", 9.5)
    pdf.set_text_color(*DARK_GRAY)
    pdf.multi_cell(page_width, 5, sanitize_text(summary_content))
    pdf.ln(5)

    # -------------------------------------------------------------------------
    # SECTION 1: DEMONSTRATED COMPETENCIES (EARNED)
    # -------------------------------------------------------------------------
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(*TXST_MAROON)
    pdf.cell(0, 7, sanitize_text(f"SECTION 1: DEMONSTRATED COMPETENCIES ({len(competencies)} Identified)"), ln=True)

    curr_x, curr_y = pdf.get_x(), pdf.get_y()
    pdf.set_draw_color(*TXST_GOLD)
    pdf.line(curr_x, curr_y, curr_x + page_width, curr_y)
    pdf.ln(3)

    earned_names = set()
    for i, comp in enumerate(competencies, start=1):
        name = comp.get("name", "Competency").strip()
        earned_names.add(name)
        evidence = comp.get("evidence", "").strip()
        justification = comp.get("justification", "").strip()
        raw_bullet = comp.get("resume_bullet", "").strip()

        # Build clean bullet
        if raw_bullet:
            bullet = raw_bullet if (raw_bullet.startswith("-") or raw_bullet.startswith("*")) else f"- {raw_bullet}"
        else:
            clean_just = justification[4:] if justification.lower().startswith("you ") else justification
            clean_just = clean_just[0].upper() + clean_just[1:] if clean_just else clean_just
            bullet = f"- {clean_just}" if clean_just else f"- Demonstrated {name} through project execution."

        # Competency Header Pill
        pdf.set_fill_color(*TXST_MAROON)
        pdf.set_text_color(*WHITE)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(page_width, 6.5, sanitize_text(f"  {i}. {name.upper()}"), ln=True, fill=True)

        # Content Box
        pdf.set_fill_color(*LIGHT_BG)
        pdf.set_draw_color(*BORDER_GRAY)
        pdf.set_font("helvetica", "B", 8.5)
        pdf.set_text_color(*DARK_GRAY)

        # Verified Evidence Quote
        pdf.ln(1.5)
        pdf.set_font("helvetica", "B", 8.5)
        pdf.cell(32, 5, sanitize_text("Verified Evidence: "), ln=False)
        pdf.set_font("helvetica", "I", 8.5)
        pdf.set_text_color(55, 65, 81)
        pdf.multi_cell(page_width - 32, 4.5, sanitize_text(f'"{evidence}"'))

        # Institutional Justification
        pdf.ln(1)
        pdf.set_font("helvetica", "B", 8.5)
        pdf.set_text_color(*DARK_GRAY)
        pdf.cell(32, 5, sanitize_text("Why It Counts: "), ln=False)
        pdf.set_font("helvetica", "", 8.5)
        pdf.set_text_color(55, 65, 81)
        pdf.multi_cell(page_width - 32, 4.5, sanitize_text(justification))

        # Resume Bullet Box (Highlighted with Gold accent border)
        pdf.ln(1.5)
        pdf.set_fill_color(254, 252, 243)  # very pale warm tint
        pdf.set_draw_color(*TXST_GOLD)
        pdf.set_line_width(0.4)
        pdf.set_font("helvetica", "B", 8.5)
        pdf.set_text_color(*TXST_MAROON)
        pdf.cell(page_width, 5, sanitize_text("  Action-Verb Resume Bullet (Ready for CV / LinkedIn):"), ln=True, fill=True, border="TLR")
        
        pdf.set_font("helvetica", "", 8.5)
        pdf.set_text_color(*DARK_GRAY)
        pdf.multi_cell(page_width, 4.5, sanitize_text(f"  {bullet}"), border="BLR", fill=True)
        pdf.ln(4)

    # -------------------------------------------------------------------------
    # SECTION 2: COMPETENCY GAP ANALYSIS & NEXT STEPS
    # -------------------------------------------------------------------------
    all_competencies = sorted(list(valid_competency_names()))
    missing_competencies = [c for c in all_competencies if c not in earned_names]

    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(*TXST_MAROON)
    pdf.cell(0, 7, sanitize_text(f"SECTION 2: COMPETENCY GAP ANALYSIS & GROWTH ROADMAP"), ln=True)

    curr_x, curr_y = pdf.get_x(), pdf.get_y()
    pdf.set_draw_color(*TXST_GOLD)
    pdf.line(curr_x, curr_y, curr_x + page_width, curr_y)
    pdf.ln(3)

    if not missing_competencies:
        # Student earned all 8!
        pdf.set_fill_color(*LIGHT_BG)
        pdf.set_font("helvetica", "B", 9.5)
        pdf.set_text_color(22, 101, 52)  # dark green
        pdf.multi_cell(
            page_width, 5,
            sanitize_text(
                "Outstanding Achievement! You have demonstrated observable evidence across all 8 Texas State / NACE "
                "Career Readiness Competencies. Focus on refining your resume bullets and conducting mock behavioral "
                "interviews with Career Services."
            ),
            border=1, fill=True
        )
        pdf.ln(4)
    else:
        pdf.set_font("helvetica", "", 9)
        pdf.set_text_color(*DARK_GRAY)
        intro_gap = (
            f"Employers seek well-rounded candidates across the 8 NACE Career Competencies. "
            f"In this evaluation, {len(earned_names)} of 8 competencies were demonstrated. "
            f"Below are career-educator recommended action steps at Texas State to develop the remaining {len(missing_competencies)}:"
        )
        pdf.multi_cell(page_width, 4.5, sanitize_text(intro_gap))
        pdf.ln(3)

        for gap_name in missing_competencies:
            # Check for page break safety
            if pdf.get_y() > 240:
                pdf.add_page()

            pdf.set_fill_color(243, 244, 246)
            pdf.set_draw_color(*BORDER_GRAY)
            pdf.set_font("helvetica", "B", 9.5)
            pdf.set_text_color(*TXST_MAROON)
            pdf.cell(page_width, 6, sanitize_text(f"  Target Competency: {gap_name}"), ln=True, fill=True, border=1)

            # Pull definition if available
            comp_info = NACE_COMPETENCIES.get(gap_name, {})
            comp_def = comp_info.get("definition", "") if isinstance(comp_info, dict) else ""
            if comp_def:
                pdf.set_font("helvetica", "I", 8)
                pdf.set_text_color(*MEDIUM_GRAY)
                pdf.multi_cell(page_width, 4, sanitize_text(f"Definition: {comp_def}"), border="LR")

            # Guidance bullets
            pdf.set_font("helvetica", "", 8.5)
            pdf.set_text_color(*DARK_GRAY)
            guidance_list = NACE_DEVELOPMENT_GUIDE.get(gap_name, [
                "Seek relevant coursework, student leadership roles, or experiential internships to build observable skills.",
                "Consult with a Texas State Career Advisor to identify targeted co-curricular development avenues."
            ])
            for step in guidance_list:
                pdf.multi_cell(page_width, 4.2, sanitize_text(f"   * {step}"), border="LR")
            
            # Close bottom border of card
            pdf.cell(page_width, 1, "", ln=True, border="T")
            pdf.ln(2.5)

    # -------------------------------------------------------------------------
    # SECTION 3: HUMAN ADVISING & NEXT STEPS
    # -------------------------------------------------------------------------
    if pdf.get_y() > 240:
        pdf.add_page()

    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(*TXST_MAROON)
    pdf.cell(0, 6, sanitize_text("NEXT STEPS: 1-ON-1 CAREER SERVICES APPOINTMENT"), ln=True)

    curr_x, curr_y = pdf.get_x(), pdf.get_y()
    pdf.set_draw_color(*TXST_GOLD)
    pdf.line(curr_x, curr_y, curr_x + page_width, curr_y)
    pdf.ln(2)

    advising_text = (
        "Take this growth plan to your next advising session to review resume phrasing, explore experiential "
        "learning programs, or map co-curricular activities to career opportunities.\n\n"
        "- Texas State Career Services: LBJ Student Center, 5th Floor | (512) 245-2645\n"
        "- McCoy College of Business Career Center: McCoy Hall 115\n"
        "- Handshake Scheduling: https://www.careerservices.txst.edu/students-alumni/appointments.html\n"
        "- Internship Connections: Report completed internships to strengthen TXST experiential benchmarking."
    )
    pdf.set_fill_color(*LIGHT_BG)
    pdf.set_draw_color(*BORDER_GRAY)
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(*DARK_GRAY)
    pdf.multi_cell(page_width, 4.2, sanitize_text(advising_text), border=1, fill=True)

    # Return raw PDF bytes
    return bytes(pdf.output())
