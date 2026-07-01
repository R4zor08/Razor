"""Transcript quality checks."""

from __future__ import annotations

import re

_GARBAGE = frozenset({"uh", "um", "ah", "oh", "the", "a", "an", "it", "is", "be"})


def is_plausible_command(text: str, *, min_length: int = 4) -> bool:
    cleaned = text.strip()
    if len(cleaned) < min_length:
        return False

    words = re.findall(r"[a-z0-9']+", cleaned.lower())
    if not words:
        return False

    substantive = [w for w in words if len(w) >= 3 and w not in _GARBAGE]
    if len(substantive) >= 1:
        return True

    if len(words) == 1 and len(words[0]) >= 4:
        return True

    return False
