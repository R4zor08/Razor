"""Central reasoning and decision module."""

from __future__ import annotations

from typing import Any

from ai.ollama_client import OllamaError, get_ollama_client
from ai.prompt_engine import PromptEngine
from core.intent_engine import IntentEngine
from utils.logger import get_logger

logger = get_logger(__name__)


class Brain:
    """Processes natural language and produces structured intents or chat replies."""

    def __init__(self, intent_engine: IntentEngine | None = None) -> None:
        self.intent_engine = intent_engine or IntentEngine()
        self.prompt_engine = PromptEngine()
        self.client = get_ollama_client()

    def reason(self, text: str) -> dict[str, Any]:
        intent = self.intent_engine.parse(text)
        logger.info("Brain resolved intent: %s", intent)
        return intent

    def chat(self, text: str) -> str:
        prompt = self.prompt_engine.build_chat_prompt(text)
        try:
            return self.client.chat(prompt)
        except OllamaError as exc:
            logger.warning("Chat failed: %s", exc)
            return "Sorry mate, I can't reach my brain right now. Is Ollama running?"
