# TXST Career Readiness Competency Discovery Agent (v0.1)

A small AI agent built for ISAN 5318 to help TXST Career Services address a
real gap: students often develop Career Readiness Competencies without
realizing it, which means those competencies go untracked and unmentioned
on resumes, in interviews, and in career advising conversations.

This agent has a student describe an experience -- a job, internship,
event, job interview, leadership moment, class project, volunteer role,
or anything else -- and identifies which of the 8 Career Readiness
Competencies (grounded in Texas State University Career Services terminology,
including *Advocacy & Compassion*) that experience demonstrates, with evidence
grounded in the student's own words.

## What it does

1. Accepts a free-text description of an experience from the student.
2. Decides whether there's enough detail to analyze, and if not, asks up
   to a couple of short follow-up questions.
3. Sends the description to Gemini to map it against the 8 NACE
   competencies, with evidence and a short justification for each.
4. Displays the result in plain language.
5. Lets the student add/change details (the analysis updates) or start
   over with a new experience.

## Setup

1. **Install dependencies** (Python 3.9+ recommended):

   ```bash
   pip install -r requirements.txt
   ```

2. **Add your API key.** Copy `.env.example` to `.env` in the same folder
   and fill in your real Gemini API key (from Google AI Studio):

   ```bash
   cp .env.example .env
   ```

   Then edit `.env`:

   ```
   GEMINI_API_KEY=AIza...
   ```

   The app reads this automatically at startup -- your key is never
   hardcoded in the source files. `.env` should **not** be shared or
   committed anywhere; `.env.example` is the safe template to share instead.

3. **Run it:**

   ```bash
   python agent.py
   ```

## Files and Architecture

| Path / File | Purpose |
| :--- | :--- |
| `ground_truth/` | **Approved source of truth** containing canonical reference data and operational rules |
| `ground_truth/source_index.md` | Registry of approved sources, canonical URLs, author provenance, and trust justifications |
| `ground_truth/nace_competencies.json` | Official NACE definitions and observable behavioral indicators |
| `ground_truth/evaluation_rules.md` | Strict rules governing evidence grounding, student correction priority, and mapping constraints |
| `logs/` | Automatic audit logs: human-readable (`interactions.log`) and structured (`interactions.jsonl`) |
| `agent.py` | Main conversation loop, CLI interface, retry/fallback logic, and diff engine |
| `competencies.py` | Loads definitions and indicators from `ground_truth/` with resilient fallback |
| `prompts.py` | Prompt templates injecting ground-truth definitions and evaluation rules into Gemini |
| `.env.example` | Template showing the expected environment variable names |
| `requirements.txt` | Python dependencies (`google-genai`, `python-dotenv`) |

## Known limitations (v0.1)

- In-memory conversation state -- while interaction logs are recorded to `logs/`, active state is not restored across runs.
- No database or integration with actual TXST/Career Services systems.
- Command-line interface only (no web UI yet).
- Relies entirely on prompting Gemini; no fine-tuning or custom model.

These are intentional scope cuts for the first working version and are
natural next steps for later iterations of the project.
