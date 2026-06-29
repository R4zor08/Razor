"""Central reasoning and decision module."""

from __future__ import annotations

from typing import Any

from core.intent_engine import IntentEngine
from utils.logger import get_logger

logger = get_logger(__name__)


class Brain:
    """Processes natural language and produces structured intents."""

    def __init__(self, intent_engine: IntentEngine | None = None) -> None:
        self.intent_engine = intent_engine or IntentEngine()

    def reason(self, text: str) -> dict[str, Any]:
        """Convert user input into a structured intent."""
        intent = self.intent_engine.parse(text)
        logger.info("Brain resolved intent: %s", intent)
        return intent
