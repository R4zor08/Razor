"""Australian personality phrases for spoken responses."""

from __future__ import annotations

import random
import re

SUCCESS_LEADS = (
    "Righto, doing that now.",
    "No worries mate.",
    "Yeah, on it.",
)

SUCCESS_TAIL = (
    "All sorted for ya.",
    "Done and dusted.",
    "Too easy.",
)

FAILURE_LEADS = (
    "No worries mate,",
    "Ah mate,",
)


def format_wake_response(text: str) -> str:
    """Format the wake-word acknowledgement."""
    return text.strip()


def format_spoken_response(technical_result: str) -> str:
    """Turn a technical executor result into natural Australian speech."""
    result = technical_result.strip()
    if not result:
        return random.choice(SUCCESS_LEADS)

    if _is_failure(result):
        lead = random.choice(FAILURE_LEADS)
        return f"{lead} {_humanize(result)}"

    if _is_search_result(result):
        return f"{random.choice(SUCCESS_LEADS)} {_summarize_search(result)} {random.choice(SUCCESS_TAIL)}"

    lead = random.choice(SUCCESS_LEADS)
    tail = random.choice(SUCCESS_TAIL)
    return f"{lead} {_humanize(result)} {tail}"


def _is_failure(result: str) -> bool:
    lowered = result.lower()
    return lowered.startswith(
        ("could not", "failed", "unknown", "no running", "no file", "i don't know")
    ) or "not found" in lowered


def _is_search_result(result: str) -> bool:
    return result.lower().startswith("found ") and "file(s) matching" in result.lower()


def _humanize(result: str) -> str:
    text = result.rstrip(".")
    replacements = (
        (r"^Opened\s+", "I've opened "),
        (r"^Closed\s+", "I've closed "),
        (r"^Shutting down.*", "shutting down the PC now"),
        (r"^Restarting.*", "restarting the PC now"),
        (r"^Could not find application '(.+)'", r"I couldn't find \1"),
        (r"^No file found matching '(.+)'", r"I couldn't find a file called \1"),
        (r"^No running process found for '(.+)'", r"\1 doesn't look like it's running"),
    )
    for pattern, repl in replacements:
        if re.match(pattern, text, re.IGNORECASE):
            return re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text.lower()


def _summarize_search(result: str) -> str:
    match = re.search(r"Found\s+(\d+)\s+file\(s\)\s+matching\s+'([^']+)'", result, re.IGNORECASE)
    if match:
        count, keyword = match.groups()
        return f"I found {count} files matching {keyword}"
    return "I've found some files for ya"
