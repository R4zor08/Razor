"""Transcript quality checks."""

from __future__ import annotations

import re

import config

_GARBAGE = frozenset({"uh", "um", "ah", "oh", "the", "a", "an", "it", "is", "be"})
_GARBAGE_PHRASES = (
    "the new gun",
    "your job",
    "new gun",
    "you're job",
    "hay razor",
)


def is_plausible_command(
    text: str,
    *,
    min_length: int = 4,
    confidence: float | None = None,
) -> bool:
    ok, _ = check_transcript(text, confidence=confidence, min_length=min_length)
    return ok


def check_transcript(
    text: str,
    *,
    min_length: int = 4,
    confidence: float | None = None,
) -> tuple[bool, str]:
    cleaned = text.strip()
    if len(cleaned) < min_length:
        return False, "too_short"

    lowered = cleaned.lower()
    for phrase in _GARBAGE_PHRASES:
        if phrase in lowered:
            return False, "garbage_phrase"

    words = re.findall(r"[a-z0-9']+", lowered)
    if not words:
        return False, "no_words"

    substantive = [w for w in words if len(w) >= 3 and w not in _GARBAGE]
    if not substantive and not (len(words) == 1 and len(words[0]) >= 4):
        return False, "no_substance"

    if confidence is not None and confidence < config.STT_MIN_CONFIDENCE:
        return False, "low_confidence"

    return True, "ok"
