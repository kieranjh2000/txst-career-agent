"""
PDF Generation Module for TXST Career Readiness Discovery Agent.

Produces a branded, professional Career Readiness Audit & Student Growth Plan PDF:
- TXST Maroon (#501214) & Gold (#8D734A) palette.
- NACE Career Readiness Framework alignment.
- Unofficial student self-reflection disclaimer.
- Section 1: Earned competencies with quotes, justifications, and action-verb resume bullets.
- Section 2: Competency gap analysis with concrete, step-by-step action plans for unearned competencies.
- Section 3: Recommended Texas State & NACE student career resources directory.
- Section 4: 1-on-1 Career Services appointment & experiential learning next steps.
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

# Concrete step-by-step action roadmaps and dedicated resources for each competency
COMPETENCY_ACTION_ROADMAP = {
    "Career & Self-Development": {
        "steps": [
            ("Step 1 - Self-Assessment", "Complete the CliftonStrengths assessment through TXST Career Services to identify your top signature themes and growth opportunities."),
            ("Step 2 - Goal Setting & Mentorship", "Define 2-3 semesterly SMART career goals and schedule an informational interview with a TXST Bobcat alumnus on Bobcat Network."),
            ("Step 3 - Resume & Handshake Profile", "Update your Handshake profile with target industries and document a 1-year Career Action Plan reviewed with a Career Advisor.")
        ],
        "primary_resource": "Handshake (txst.joinhandshake.com) & Bobcat Network (Alumni Mentoring)"
    },
    "Communication": {
        "steps": [
            ("Step 1 - Public Speaking", "Deliver project presentations in class or join Toastmasters at TXST to refine speech delivery, posture, and audience engagement."),
            ("Step 2 - Written Executive Summaries", "Practice condensing multi-page academic papers into 1-page executive memos with clear headings and bullet points."),
            ("Step 3 - Communication Review", "Visit the TXST Writing Center or Alkek Presentation Practice Rooms to record and critique your presentation timing and slides.")
        ],
        "primary_resource": "TXST Writing Center (ASB South 1st Floor) & Presentation Practice Rooms (Alkek Library)"
    },
    "Critical Thinking": {
        "steps": [
            ("Step 1 - Analytical Problem Framing", "Analyze complex multi-variable case studies in your coursework and formulate hypothesis-driven problem statements."),
            ("Step 2 - Decision Matrices & Risk Analysis", "Evaluate competing solutions using objective decision criteria, cost-benefit comparisons, and risk assessment matrices."),
            ("Step 3 - Pitch or Hackathon Participation", "Participate in 3-Day Startup (3DS), a hackathon, or a case competition through the TXST Center for Innovation & Entrepreneurship.")
        ],
        "primary_resource": "Center for Innovation & Entrepreneurship (3-Day Startup) & Alkek Library Research Data Services"
    },
    "Advocacy & Compassion": {
        "steps": [
            ("Step 1 - Community Service", "Register for Bobcat Build or volunteer with a local San Marcos non-profit through TXST Student Involvement."),
            ("Step 2 - Cross-Cultural Engagement", "Attend campus cultural dialogue forums or join student organizations dedicated to advocacy and community empowerment."),
            ("Step 3 - Empathetic Mediation", "Practice active listening and constructive conflict de-escalation when navigating differing perspectives in team projects.")
        ],
        "primary_resource": "Bobcat Build & TXST Student Involvement (LBJ Student Center 4th Floor)"
    },
    "Leadership": {
        "steps": [
            ("Step 1 - Project Ownership", "Volunteer to serve as project manager or milestone lead on a major academic group project, delegating tasks by strengths."),
            ("Step 2 - Student Organization Leadership", "Seek an executive board or committee chair role within a registered TXST student organization via Bobcat Organization Hub."),
            ("Step 3 - Leadership Certificate", "Participate in the TXST Leadership Institute workshops to develop coaching, ethical leadership, and conflict resolution skills.")
        ],
        "primary_resource": "TXST Leadership Institute & Bobcat Organization Hub (txstate.edu/involvement)"
    },
    "Professionalism": {
        "steps": [
            ("Step 1 - Workplace Accountability", "Establish reliable work habits: meet deadlines 24 hours early, maintain prompt attendance, and communicate delays proactively."),
            ("Step 2 - Professional Attire & Networking", "Visit the TXST Career Closet for professional interview attire and attend the McCoy College of Business Career Fair."),
            ("Step 3 - Constructive Feedback Review", "Request formal developmental feedback from professors or work supervisors after major milestones and implement refinements.")
        ],
        "primary_resource": "TXST Career Closet & McCoy College of Business Career Center (McCoy 115)"
    },
    "Teamwork": {
        "steps": [
            ("Step 1 - Team Charter & Norms", "Establish written team norms, shared expectations, and a collaborative workspace (e.g. Teams, Google Workspace) at project kickoff."),
            ("Step 2 - Collaborative Problem-Solving", "Actively solicit input from quieter team members, synthesize diverse opinions, and focus on shared project milestones."),
            ("Step 3 - Peer Feedback & Recognition", "Conduct a midpoint project check-in to recognize team member contributions and resolve workflow bottlenecks respectfully.")
        ],
        "primary_resource": "Alkek Collaborative Study Spaces & Student Organization Group Projects"
    },
    "Technology": {
        "steps": [
            ("Step 1 - Industry Certification", "Complete a free digital certification on LinkedIn Learning (e.g. Advanced Excel, SQL, Python, Tableau, or Google Analytics)."),
            ("Step 2 - Workflow Automation", "Automate a repetitive manual task in an academic assignment, student org, or part-time job using scripts, formulas, or no-code tools."),
            ("Step 3 - Technical Portfolio Artifact", "Create a public artifact (e.g. interactive dashboard, automated spreadsheet model, or GitHub repository) to demonstrate your skills.")
        ],
        "primary_resource": "LinkedIn Learning (Free access via TXST IT Assistance) & Alkek One Makerspace"
    },
}

# Dedicated directory of key student career resources available at Texas State University
TXST_CAREER_RESOURCES = [
    {
        "name": "Handshake (txst.joinhandshake.com)",
        "category": "Career Services & Jobs",
        "description": "Schedule 1-on-1 career advising sessions, attend university-wide & McCoy career fairs, and browse thousands of verified internships and full-time postings."
    },
    {
        "name": "LinkedIn Learning (Free for TXST Students)",
        "category": "Technical & Professional Certifications",
        "description": "Unlimited access to 16,000+ expert-led video courses and certifications in programming, data analytics, project management, and business acumen via TXST NetID."
    },
    {
        "name": "Bobcat Network (bobcatnetwork.txstate.edu)",
        "category": "Alumni Mentorship & Networking",
        "description": "Directly connect with Texas State alumni for informational interviews, career advice, job shadowing, and industry mentorship."
    },
    {
        "name": "VMock Smart Resume Platform",
        "category": "AI Resume Feedback",
        "description": "Instant, 24/7 online resume evaluation that scores your bullet points against TXST Career Services benchmarks and employer applicant tracking systems."
    },
    {
        "name": "Bobcat Organization Hub & Leadership Institute",
        "category": "Experiential & Leadership Development",
        "description": "Discover 400+ registered student organizations, apply for campus officer roles, participate in Bobcat Build, and complete leadership workshop series."
    },
    {
        "name": "McCoy Career Center & Career Closet",
        "category": "Advising & Professional Attire",
        "description": "Located in McCoy Hall 115. Access free professional business suit rentals for interviews, mock interview prep, and targeted business career coaching."
    },
]


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
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(*MEDIUM_GRAY)
        page_str = f"Page {self.page_no()} of {{nb}}  |  Texas State Career Readiness Discovery Agent"
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
        pdf.set_fill_color(254, 252, 243)  # warm tint
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
    # SECTION 2: COMPETENCY GAP ANALYSIS & ACTIONABLE STEPS
    # -------------------------------------------------------------------------
    all_competencies = sorted(list(valid_competency_names()))
    missing_competencies = [c for c in all_competencies if c not in earned_names]

    if pdf.get_y() > 230:
        pdf.add_page()

    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(*TXST_MAROON)
    pdf.cell(0, 7, sanitize_text(f"SECTION 2: COMPETENCY GAP ANALYSIS & ACTIONABLE ROADMAP"), ln=True)

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
            f"Employers seek well-rounded candidates across all 8 NACE Career Competencies. "
            f"In this evaluation, {len(earned_names)} of 8 competencies were demonstrated. "
            f"Below is a concrete, step-by-step development roadmap for the remaining {len(missing_competencies)} "
            f"competencies to help you systematically build and document them prior to graduation:"
        )
        pdf.multi_cell(page_width, 4.5, sanitize_text(intro_gap))
        pdf.ln(3)

        for gap_name in missing_competencies:
            # Check for page break safety before starting a block
            if pdf.get_y() > 220:
                pdf.add_page()

            # Competency Title Bar
            pdf.set_fill_color(243, 244, 246)
            pdf.set_draw_color(*BORDER_GRAY)
            pdf.set_font("helvetica", "B", 9.5)
            pdf.set_text_color(*TXST_MAROON)
            pdf.cell(page_width, 6, sanitize_text(f"  Target Competency: {gap_name.upper()}"), ln=True, fill=True, border=1)

            # Definition
            comp_info = NACE_COMPETENCIES.get(gap_name, {})
            comp_def = comp_info.get("definition", "") if isinstance(comp_info, dict) else ""
            if comp_def:
                pdf.set_font("helvetica", "I", 8)
                pdf.set_text_color(*MEDIUM_GRAY)
                pdf.multi_cell(page_width, 3.8, sanitize_text(f"Definition: {comp_def}"), border="LR")

            # Structured Action Steps
            roadmap_info = COMPETENCY_ACTION_ROADMAP.get(gap_name, {
                "steps": [
                    ("Action Plan", "Engage in relevant coursework, student leadership roles, or experiential internships to build observable skills.")
                ],
                "primary_resource": "TXST Career Services & Handshake"
            })

            pdf.set_font("helvetica", "", 8.5)
            for step_title, step_desc in roadmap_info.get("steps", []):
                # Step header
                pdf.set_font("helvetica", "B", 8)
                pdf.set_text_color(*TXST_MAROON)
                pdf.cell(page_width, 4.2, sanitize_text(f"    > {step_title}:"), ln=True, border="LR")
                # Step body
                pdf.set_font("helvetica", "", 8)
                pdf.set_text_color(*DARK_GRAY)
                pdf.multi_cell(page_width, 3.8, sanitize_text(f"      {step_desc}"), border="LR")

            # Dedicated Primary Resource Tag
            primary_res = roadmap_info.get("primary_resource", "")
            if primary_res:
                pdf.set_fill_color(254, 252, 243)  # subtle gold tint
                pdf.set_font("helvetica", "B", 8)
                pdf.set_text_color(*TXST_GOLD)
                pdf.cell(page_width, 4.5, sanitize_text(f"    [Key Campus Resource]: {primary_res}"), ln=True, fill=True, border="LR")

            # Close bottom border of card
            pdf.cell(page_width, 1, "", ln=True, border="T")
            pdf.ln(3)

    # -------------------------------------------------------------------------
    # SECTION 3: RECOMMENDED STUDENT CAREER RESOURCES DIRECTORY
    # -------------------------------------------------------------------------
    if pdf.get_y() > 200:
        pdf.add_page()

    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(*TXST_MAROON)
    pdf.cell(0, 7, sanitize_text("SECTION 3: RECOMMENDED TEXAS STATE CAREER RESOURCES"), ln=True)

    curr_x, curr_y = pdf.get_x(), pdf.get_y()
    pdf.set_draw_color(*TXST_GOLD)
    pdf.line(curr_x, curr_y, curr_x + page_width, curr_y)
    pdf.ln(2.5)

    pdf.set_font("helvetica", "", 8.8)
    pdf.set_text_color(*DARK_GRAY)
    res_intro = (
        "Take advantage of these high-impact career resources and platforms available free to Texas State students "
        "to accelerate your competency development and prepare for recruitment:"
    )
    pdf.multi_cell(page_width, 4.2, sanitize_text(res_intro))
    pdf.ln(2.5)

    for res in TXST_CAREER_RESOURCES:
        if pdf.get_y() > 250:
            pdf.add_page()

        pdf.set_fill_color(*LIGHT_BG)
        pdf.set_draw_color(*BORDER_GRAY)
        
        # Resource Name and Category
        pdf.set_font("helvetica", "B", 8.5)
        pdf.set_text_color(*TXST_MAROON)
        pdf.cell(page_width, 4.5, sanitize_text(f"  * {res['name']}  [{res['category']}]"), ln=True, fill=True, border="TLR")
        
        # Resource Description
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(*DARK_GRAY)
        pdf.multi_cell(page_width, 3.8, sanitize_text(f"    {res['description']}"), border="BLR", fill=True)
        pdf.ln(1.5)

    # -------------------------------------------------------------------------
    # SECTION 4: HUMAN ADVISING & NEXT STEPS
    # -------------------------------------------------------------------------
    if pdf.get_y() > 230:
        pdf.add_page()

    pdf.ln(2)
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(*TXST_MAROON)
    pdf.cell(0, 6, sanitize_text("SECTION 4: 1-ON-1 CAREER SERVICES APPOINTMENT"), ln=True)

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
