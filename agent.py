"""
NACE Career Competency Discovery Agent (v0.1)

A small command-line agent that helps a student figure out which NACE
Career Readiness Competencies they developed through an experience --
a job, internship, event, interview, leadership moment, or anything else.

Flow:
    1. Accept a user request (describe an experience)
    2. Decide if there's enough detail, or ask follow-up questions
    3. Call Gemini to map the experience to NACE competencies
    4. Display a clear, human-readable result
    5. Let the student add/edit details and re-analyze, or start over

Run with:  python agent.py
Requires:  GEMINI_API_KEY set via environment variable or a .env file.
"""

import json
import datetime
import os
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors

from competencies import valid_competency_names
from prompts import build_completeness_prompt, build_mapping_prompt

load_dotenv()  # pulls GEMINI_API_KEY (and optional GEMINI_MODEL) from .env

API_KEY = os.environ.get("GEMINI_API_KEY")
# gemini-3.5-flash-lite has a much higher free-tier daily request quota
# than gemini-3.6-flash, so it's used as the primary model to avoid
# burning through a small daily allowance during testing.
PRIMARY_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.6-flash")
MAX_FOLLOW_UP_ROUNDS = 2  # avoid an endless question loop
MAX_API_RETRIES = 2  # kept low -- retries on 503s may still burn quota

if not API_KEY:
    print(
        "No GEMINI_API_KEY found.\n"
        "Set it as an environment variable, or create a .env file "
        "(see .env.example) with:\n\n"
        "    GEMINI_API_KEY=your_key_here\n"
    )
    sys.exit(1)

client = genai.Client(api_key=API_KEY)


def _is_daily_quota_error(e: genai_errors.APIError) -> bool:
    """True if this is a 'requests per day' quota exhaustion -- retrying
    within seconds/minutes cannot fix this, only switching models or
    waiting until the daily reset (midnight Pacific time) can."""
    code = getattr(e, "code", None) or getattr(e, "status_code", None)
    message = str(e).lower()
    return code == 429 and "per day" in message.replace("perday", "per day")


def _try_model(model: str, prompt: str, json_mode: bool = True) -> Optional[str]:
    """Attempt one model with a few retries. Returns text on success,
    or None if the model is unavailable -- either a transient server-side
    overload (worth retrying) or a daily quota that's been used up (not
    worth retrying, so we bail out immediately to try the fallback)."""
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
            if _is_daily_quota_error(e):
                print(
                    f"\n[{model} has hit its free-tier daily request "
                    f"limit -- that only resets at midnight Pacific time, "
                    f"so retrying won't help. Trying a different model...]"
                )
                return None
            if attempt < MAX_API_RETRIES:
                wait_seconds = 3 * attempt
                print(
                    f"\n[{model} is busy -- retrying in {wait_seconds}s "
                    f"({attempt}/{MAX_API_RETRIES})...]"
                )
                time.sleep(wait_seconds)
            else:
                print(f"\n[{model} did not respond after {MAX_API_RETRIES} tries.]")
        except Exception as e:
            if attempt < MAX_API_RETRIES:
                wait_seconds = 3 * attempt
                print(
                    f"\n[Connection issue -- retrying in {wait_seconds}s "
                    f"({attempt}/{MAX_API_RETRIES})...]"
                )
                time.sleep(wait_seconds)
            else:
                print(f"\n[Unable to connect to {model}. Please check your internet connection.]")
    return None


def call_gemini(prompt: str, json_mode: bool = True) -> str:
    """Send a single-turn prompt to Gemini and return the raw text response.

    Tries the primary model with retries first. If it's persistently
    overloaded (503, "high demand") or has hit its free-tier daily quota
    (429, RESOURCE_EXHAUSTED), automatically falls back to a second model
    with a separate quota/capacity pool rather than giving up.
    """
    result = _try_model(PRIMARY_MODEL, prompt, json_mode=json_mode)
    if result is not None:
        return result

    if FALLBACK_MODEL and FALLBACK_MODEL != PRIMARY_MODEL:
        print(f"\nSwitching to backup model ({FALLBACK_MODEL})...\n")
        result = _try_model(FALLBACK_MODEL, prompt, json_mode=json_mode)
        if result is not None:
            return result

    print(
        "\nBoth the primary and backup models are currently unavailable -- "
        "either Google's servers are under heavy load, or both models' "
        "free-tier daily quotas are used up for today (that resets at "
        "midnight Pacific time). This is on Google's end, not a bug in "
        "the app.\n"
    )
    raise RuntimeError("Gemini API unavailable after retries and fallback")


def parse_json_response(raw_text: str) -> dict:
    """Strip any accidental markdown fences and parse JSON, with a clear error."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        print("\n[Warning] Could not parse the model's response as JSON.")
        print("Raw response was:\n", raw_text)
        return {}


def check_completeness(experience_text: str) -> dict:
    try:
        raw = call_gemini(build_completeness_prompt(experience_text))
        result = parse_json_response(raw)
    except Exception as e:
        # Fail safe: proceed directly to mapping rather than crashing
        print("\n[Notice] Could not verify completeness online right now. Proceeding directly to analysis...\n")
        return {"complete": True, "follow_up_questions": []}
    if not isinstance(result, dict) or "complete" not in result:
        return {"complete": True, "follow_up_questions": []}
    return result


def map_competencies(experience_text: str) -> dict:
    try:
        raw = call_gemini(build_mapping_prompt(experience_text))
        result = parse_json_response(raw)
    except Exception as e:
        print("\n[Notice] Could not complete competency mapping due to a temporary connection or server issue.")
        return {
            "competencies": [],
            "summary": "Service was temporarily unavailable to complete the competency analysis."
        }
    if not isinstance(result, dict):
        result = {}
    result.setdefault("competencies", [])
    result.setdefault("summary", "")
    # Drop any competency names the model may have hallucinated.
    valid_names = valid_competency_names()
    result["competencies"] = [
        c for c in result["competencies"] if isinstance(c, dict) and c.get("name") in valid_names
    ]
    return result


def display_results(result: dict, previous_names: Optional[set] = None) -> set:
    competencies = result.get("competencies", [])
    summary = result.get("summary", "")
    current_names = {c.get("name") for c in competencies}

    print("\n" + "=" * 60)
    if not competencies:
        print("I couldn't clearly identify an approved TXST career competency in that description yet.")
        print("\nTip: If you're unsure how to frame this experience, or if it involves complex circumstances,")
        print("consider scheduling a 1-on-1 session with a Texas State Career Services advisor:")
        print("https://www.careerservices.txst.edu/students-alumni/appointments.html\n")
    else:
        print(f"Here's what this experience shows about you:\n")
        for c in competencies:
            print(f"* {c.get('name')}")
            print(f"    Evidence: {c.get('evidence')}")
            print(f"    Why it counts: {c.get('justification')}\n")
    if summary:
        print(f"Summary: {summary}")

    if previous_names is not None:
        added = current_names - previous_names
        removed = previous_names - current_names
        if added or removed:
            print("\nWhat changed from the last analysis:")
            for name in added:
                print(f"  + Added: {name}")
            for name in removed:
                print(f"  - Removed: {name}")
        else:
            print("\n(No change in which competencies were identified.)")

    print("=" * 60 + "\n")
    return current_names


LOGS_DIR = Path(__file__).parent / "logs"
LOG_FILE_TXT = LOGS_DIR / "interactions.log"
LOG_FILE_JSONL = LOGS_DIR / "interactions.jsonl"


def log_interaction(
    initial_text: str,
    final_text: str,
    results: dict,
    updates: Optional[list] = None,
) -> None:
    """Append a human-readable and structured record of the interaction to logs/."""
    try:
        LOGS_DIR.mkdir(exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        competencies = results.get("competencies", [])

        # 1. Human-readable text log
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
            f.write("\n" + "-" * 70 + "\n\n")

        # 2. Structured JSON Lines log
        record = {
            "timestamp": timestamp,
            "initial_experience": initial_text,
            "final_experience": final_text,
            "updates": updates or [],
            "competencies": [c.get("name") for c in competencies if isinstance(c, dict)],
            "details": competencies,
            "summary": results.get("summary", ""),
        }
        with open(LOG_FILE_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    except Exception:
        # Logging should never interrupt or crash the application
        pass


def gather_initial_experience() -> str:
    print("=" * 60)
    print("TXST Career Readiness Competency Discovery Agent")
    print("=" * 60)
    print(
        "\nTell me about an experience -- a job, internship, event, "
        "interview, leadership moment, class project, volunteer work, "
        "or anything else that stands out to you.\n"
    )
    while True:
        text = input("You: ").strip()
        if text:
            return text
        print("Please enter a short description of an experience to get started (or press Ctrl+C to quit).\n")


EDIT_KEYWORDS = ("clarify", "update", "correct", "change", "edit", "fix")

EDIT_TRIGGER_PHRASES = (
    "something i said",
    "something i previously said",
    "what i said",
    "what i previously said",
    "what i told you",
    "can i update",
    "can i change",
    "can i clarify",
    "can i correct",
    "can i edit",
    "can i fix",
    "let me correct",
    "let me clarify",
    "let me change",
    "let me update",
    "i misspoke",
    "i meant to say",
    "that's not right",
    "that's wrong",
    "not what i meant",
)


def looks_like_edit_request(text: str) -> bool:
    """Heuristic: the student wants to change something they already said,
    rather than answering the question that was just asked."""
    lowered = text.lower()
    if any(phrase in lowered for phrase in EDIT_TRIGGER_PHRASES):
        return True
    # Fallback: a short question containing an edit-related keyword
    return "?" in text and any(word in lowered for word in EDIT_KEYWORDS)


def handle_correction(experience_text: str) -> str:
    correction = input(
        "Sure -- what would you like to clarify or change?\nYou: "
    ).strip()
    if correction:
        experience_text += f"\n\nUpdate: {correction}"
        print("\nGot it -- I've noted that change and will reconsider "
              "based on it.\n")
    return experience_text


def run_completeness_loop(experience_text: str) -> str:
    """Ask follow-up questions until the description is detailed enough
    (or we hit the round limit), returning the combined description."""
    rounds = 0
    while rounds < MAX_FOLLOW_UP_ROUNDS:
        check = check_completeness(experience_text)
        if check.get("complete", True) or not check.get("follow_up_questions"):
            break
        print(
            "\nA couple quick questions to help pin this down "
            "(if you want to clarify or change something you already "
            "said, just say so and I'll pause to update it):"
        )
        interrupted = False
        for q in check["follow_up_questions"]:
            q_text = q if isinstance(q, str) else (list(q.values())[0] if isinstance(q, dict) and q else str(q))
            answer = input(f"  - {q_text}\n    You: ").strip()
            if looks_like_edit_request(answer):
                experience_text = handle_correction(experience_text)
                interrupted = True
                break
            if answer:
                experience_text += f"\n\nFollow-up -- {q_text}\nAnswer: {answer}"
        if interrupted:
            # Don't count this round -- re-check completeness with the
            # corrected info instead of continuing down the stale question list.
            continue
        rounds += 1
    return experience_text


def edit_or_continue_loop(
    initial_text: str,
    experience_text: str,
    previous_names: set,
    updates: list,
) -> None:
    """After showing results, let the student add detail, start over, or quit."""
    while True:
        print("Would you like to:")
        print("  [1] Add or change something about this experience")
        print("  [2] Describe a new, different experience")
        print("  [3] Quit")
        choice = input("Choice: ").strip()

        if choice == "1":
            addition = input(
                "What would you like to add or change?\nYou: "
            ).strip()
            if addition:
                experience_text += f"\n\nUpdate: {addition}"
                updates.append(addition)
                print(f"\nGot it -- factoring that in: \"{addition}\"")
                print("Re-analyzing with the updated information...\n")
                result = map_competencies(experience_text)
                previous_names = display_results(result, previous_names)
                log_interaction(initial_text, experience_text, result, updates)
            else:
                print("No update entered. Keeping your current analysis.\n")

        elif choice == "2":
            initial_text = gather_initial_experience()
            experience_text = run_completeness_loop(initial_text)
            result = map_competencies(experience_text)
            previous_names = display_results(result)
            updates = []
            log_interaction(initial_text, experience_text, result, updates)

        elif choice == "3":
            print("Good luck out there!")
            break

        else:
            print("Please enter 1, 2, or 3.\n")


def main():
    initial_text = gather_initial_experience()
    experience_text = run_completeness_loop(initial_text)
    result = map_competencies(experience_text)
    previous_names = display_results(result)
    updates = []
    log_interaction(initial_text, experience_text, result, updates)
    edit_or_continue_loop(initial_text, experience_text, previous_names, updates)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nSession ended. Good luck!")
        sys.exit(0)
    except Exception as e:
        print(f"\n[Notice] An unexpected issue occurred: {e}")
        print("The agent has stopped safely without crashing. Please check your connection and try running again.\n")
        sys.exit(1)
