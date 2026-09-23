"""
Prompt templates for the NACE Career Competency Discovery Agent.

Kept separate from agent.py so prompt wording can be iterated on without
touching the control-flow logic.
"""

from pathlib import Path

from competencies import format_competency_list

RULES_PATH = Path(__file__).parent / "ground_truth" / "evaluation_rules.md"


def load_evaluation_rules() -> str:
    """Load approved evaluation and grounding rules from ground_truth/."""
    if RULES_PATH.exists():
        try:
            return RULES_PATH.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return ""

# ---------------------------------------------------------------------------
# Step 1: Completeness check
# ---------------------------------------------------------------------------
# Decides whether the student's description has enough detail to analyze,
# or whether the agent should ask a follow-up question first.

COMPLETENESS_CHECK_PROMPT = """You are helping a college student reflect on a \
personal experience so it can later be analyzed for career-readiness \
competencies. The experience could be a job, internship, campus event, \
job interview, leadership role, volunteer work, class project, personal \
challenge, or any other experience -- it does NOT have to be formal \
work-based learning.

Here is what the student has shared so far:
---
{experience_text}
---

Decide whether this description has ENOUGH concrete detail to analyze for \
career competencies (specifics about what the student actually did, how \
they interacted with others, what problems came up, decisions they made, \
etc.) or whether it is too vague/short to say anything meaningful.

Respond with ONLY a JSON object, no other text, no markdown fences, in \
exactly this shape:

{{
  "complete": true or false,
  "follow_up_questions": ["question 1", "question 2"]
}}

Rules:
- If complete is true, follow_up_questions must be an empty list.
- If complete is false, give 1 to 3 short, specific, friendly follow-up \
questions that would help draw out concrete detail (what they did day to \
day, who they worked with, what problems or conflicts came up, what \
decisions they made, what the outcome was).
- Do not ask more than 3 questions at once.
"""

# ---------------------------------------------------------------------------
# Step 2: Competency mapping
# ---------------------------------------------------------------------------
# Takes the full experience description and maps it to the 8 NACE
# competencies with evidence grounded in the student's own words.

COMPETENCY_MAPPING_PROMPT = """You are a career-readiness advisor helping a \
college student recognize which NACE Career Readiness Competencies they \
demonstrated in an experience they described. Students often develop these \
competencies without realizing it -- your job is to point them out clearly \
and specifically, grounded in what the student actually said.

The 8 NACE Career Readiness Competencies are:
{competency_list}

{evaluation_rules}

Here is the student's full description of their experience. It may include \
follow-up answers or later updates/corrections they added after their \
first response:
---
{experience_text}
---

Important: any text labeled "Follow-up", "Answer", or "Update" was added \
by the student AFTER their original description, often to add detail or \
correct something they said earlier. If a later update contradicts or \
changes something from earlier in the text (e.g., a different role, a \
different outcome, a detail that was wrong), treat the LATEST version as \
correct and base your analysis on the corrected version of events, not \
the outdated detail it replaced.

Identify which of the 8 competencies are genuinely evidenced by this \
description adhering strictly to the evaluation rules above. Only include a \
competency if there is real, specific evidence for it -- do not force all 8 in \
if they aren't supported. For each competency you include, quote or closely \
paraphrase the specific part of what the student said that shows it.

Respond with ONLY a JSON object, no other text, no markdown fences, in \
exactly this shape:

{{
  "competencies": [
    {{
      "name": "exact competency name from the list above",
      "evidence": "the specific detail from the student's description that shows this",
      "justification": "one short sentence explaining why this counts as that competency"
    }}
  ],
  "summary": "one encouraging sentence summarizing what this experience shows about the student overall"
}}

If truly nothing in the description supports any competency, or if the \
information is fundamentally inconclusive or conflicting, return an empty \
"competencies" list and explain that clearly in "summary", recommending \
that the student consult with a Texas State Career Services advisor for \
personalized human review.
"""


def build_completeness_prompt(experience_text: str) -> str:
    return COMPLETENESS_CHECK_PROMPT.format(experience_text=experience_text)


def build_mapping_prompt(experience_text: str) -> str:
    rules = load_evaluation_rules()
    rules_block = (
        f"Approved Ground Truth Evaluation Rules:\n{rules}\n"
        if rules
        else ""
    )
    return COMPETENCY_MAPPING_PROMPT.format(
        competency_list=format_competency_list(),
        evaluation_rules=rules_block,
        experience_text=experience_text,
    )
