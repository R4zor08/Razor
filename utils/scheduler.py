"""Proactive greeting and future scheduling hooks."""

from __future__ import annotations

from datetime import date

import config
from ai.memory import get_memory
from utils.logger import get_logger

logger = get_logger(__name__)


def maybe_startup_greeting() -> str | None:
    if not config.PROACTIVE_GREETING:
        return None

    memory = get_memory()
    today = date.today().isoformat()
    if memory.recall("last_greeting_date") == today:
        return None

    memory.remember("last_greeting_date", today)
    name = memory.recall("user_name")
    if name:
        message = f"Good morning, {name}. Razor is online."
    else:
        message = "Good morning. Razor is online."
    logger.info("Proactive greeting: %s", message)
    return message
