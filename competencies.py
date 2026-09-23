"""
Reference data for the 8 NACE Career Readiness Competencies.

This module is intentionally simple: a name + short definition for each
competency. It's used to (a) ground the AI prompts so the model knows
exactly what it's mapping to, and (b) validate/format the model's output
in agent.py.
"""

import json
from pathlib import Path

GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth" / "nace_competencies.json"

FALLBACK_COMPETENCIES = {
    "Career & Self-Development": {
        "definition": (
            "Proactively develops oneself and one's career through continual "
            "personal and professional learning, awareness of one's strengths "
            "and weaknesses, navigation of career opportunities, and networking "
            "to build relationships within and beyond one's organization."
        ),
        "observable_behaviors": []
    },
    "Communication": {
        "definition": (
            "Clearly and effectively exchanges information, ideas, facts, and "
            "perspectives with persons inside and outside of an organization, "
            "through speaking, writing, and listening."
        ),
        "observable_behaviors": []
    },
    "Critical Thinking": {
        "definition": (
            "Identifies and responds to needs based upon an understanding of "
            "situational context and logical analysis of relevant information."
        ),
        "observable_behaviors": []
    },
    "Advocacy & Compassion": {
        "definition": (
            "Demonstrate the awareness, attitude, knowledge, and skills "
            "required to compassionately engage people from different backgrounds. "
            "The ability to empathize with others, overcome challenges, and diffuse conflict."
        ),
        "observable_behaviors": []
    },
    "Leadership": {
        "definition": (
            "Recognizes and capitalizes on personal and team strengths to "
            "achieve organizational goals, and uses interpersonal skills to "
            "coach and develop others."
        ),
        "observable_behaviors": []
    },
    "Professionalism": {
        "definition": (
            "Knows how to demonstrate personal accountability and effective "
            "work habits (e.g., punctuality, meeting deadlines, and time "
            "management), understands the impact of nonverbal communication on "
            "professional work image, and is able to learn from mistakes."
        ),
        "observable_behaviors": []
    },
    "Teamwork": {
        "definition": (
            "Builds and maintains collaborative relationships to work "
            "effectively toward common goals, while appreciating diverse "
            "viewpoints and shared responsibilities."
        ),
        "observable_behaviors": []
    },
    "Technology": {
        "definition": (
            "Understands and leverages technologies ethically to enhance "
            "efficiencies, complete tasks, and accomplish goals; demonstrates "
            "effective adaptability to new and emerging technologies."
        ),
        "observable_behaviors": []
    },
}


def _load_ground_truth_competencies() -> dict:
    """Load canonical competencies and behavior indicators from ground_truth/."""
    if GROUND_TRUTH_PATH.exists():
        try:
            with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                loaded = data.get("competencies", {})
                if loaded:
                    return loaded
        except Exception:
            pass
    return FALLBACK_COMPETENCIES


NACE_COMPETENCIES = _load_ground_truth_competencies()


def format_competency_list() -> str:
    """Return the competencies formatted as a numbered list with definitions and observable behaviors."""
    lines = []
    for i, (name, info) in enumerate(NACE_COMPETENCIES.items(), start=1):
        if isinstance(info, dict):
            definition = info.get("definition", "")
            behaviors = info.get("observable_behaviors", [])
            lines.append(f"{i}. {name}: {definition}")
            if behaviors:
                lines.append(f"   Observable behaviors: {'; '.join(behaviors)}")
        else:
            lines.append(f"{i}. {name}: {info}")
    return "\n".join(lines)


def valid_competency_names():
    return set(NACE_COMPETENCIES.keys())
