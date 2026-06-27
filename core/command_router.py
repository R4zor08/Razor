"""Routes parsed intents to system handlers."""

from __future__ import annotations

from typing import Any

from core.intent_engine import IntentEngine
from system.executor import Executor
from utils.logger import get_logger

logger = get_logger(__name__)


class CommandRouter:
    """Dispatches natural language or structured intents to system handlers."""

    def __init__(
        self,
        executor: Executor | None = None,
        intent_engine: IntentEngine | None = None,
    ) -> None:
        self.executor = executor or Executor()
        self.intent_engine = intent_engine or IntentEngine()

    def handle(self, text: str) -> str:
        """Parse natural language and execute the resulting command."""
        intent = self.intent_engine.parse(text)
        logger.info("Resolved intent: %s", intent)
        return self.executor.execute_intent(intent)

    def route(self, intent: dict[str, Any]) -> str:
        """Execute a pre-built intent dict."""
        return self.executor.execute_intent(intent)
