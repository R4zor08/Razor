"""Personality formatting for spoken responses."""

from __future__ import annotations

import random
import re

import config

JARVIS_SUCCESS = ("Done.", "Certainly.", "Right away.", "Complete.")
JARVIS_FAILURE = ("I'm afraid that didn't work.", "Unable to complete that, sir.")

AUSSIE_SUCCESS_LEADS = ("Righto, doing that now.", "No worries mate.", "Yeah, on it.")
AUSSIE_SUCCESS_TAIL = ("All sorted for ya.", "Done and dusted.", "Too easy.")
AUSSIE_FAILURE_LEADS = ("No worries mate,", "Ah mate,")


def format_wake_response(text: str) -> str:
    return text.strip()


def exit_phrase() -> str:
    if config.PERSONALITY == "jarvis":
        return "Goodbye."
    return "Catch ya later mate."


def processing_phrase() -> str:
    if config.PERSONALITY == "jarvis":
        return "One moment."
    return "One sec mate."


def format_spoken_response(technical_result: str) -> str:
    if config.PERSONALITY == "jarvis":
        return _format_jarvis(technical_result)
    return _format_aussie(technical_result)


def _format_jarvis(result: str) -> str:
    text = result.strip()
    if not text:
        return random.choice(JARVIS_SUCCESS)
    if _is_failure(text):
        return f"{random.choice(JARVIS_FAILURE)} {_humanize(text)}"
    if _is_search_result(text):
        return _summarize_search(text)
    if text.lower().startswith("opened") or text.lower().startswith("created"):
        return random.choice(JARVIS_SUCCESS)
    return text if len(text) < 120 else text[:117] + "..."


def _format_aussie(result: str) -> str:
    text = result.strip()
    if not text:
        return random.choice(AUSSIE_SUCCESS_LEADS)
    if _is_failure(text):
        return f"{random.choice(AUSSIE_FAILURE_LEADS)} {_humanize(text)}"
    if _is_search_result(text):
        return f"{random.choice(AUSSIE_SUCCESS_LEADS)} {_summarize_search(text)} {random.choice(AUSSIE_SUCCESS_TAIL)}"
    return f"{random.choice(AUSSIE_SUCCESS_LEADS)} {_humanize(text)} {random.choice(AUSSIE_SUCCESS_TAIL)}"


def _is_failure(result: str) -> bool:
    lowered = result.lower()
    return lowered.startswith(
        ("could not", "failed", "unknown", "no running", "no file", "i don't know", "i didn't catch")
    ) or "not found" in lowered


def _is_search_result(result: str) -> bool:
    return result.lower().startswith("found ") and "file(s) matching" in result.lower()


def _humanize(result: str) -> str:
    text = result.rstrip(".")
    replacements = (
        (r"^Opened\s+", "I've opened "),
        (r"^Closed\s+", "I've closed "),
        (r"^Could not find application '(.+)'", r"I couldn't find \1"),
    )
    for pattern, repl in replacements:
        if re.match(pattern, text, re.IGNORECASE):
            return re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text.lower() if config.PERSONALITY == "aussie" else text


def _summarize_search(result: str) -> str:
    match = re.search(r"Found\s+(\d+)\s+file\(s\)\s+matching\s+'([^']+)'", result, re.IGNORECASE)
    if match:
        count, keyword = match.groups()
        if config.PERSONALITY == "jarvis":
            return f"Found {count} files matching {keyword}."
        return f"I found {count} files matching {keyword}"
    return result
