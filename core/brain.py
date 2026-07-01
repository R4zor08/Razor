"""Central reasoning and decision module."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import config
from ai.agent import Agent
from ai.memory import get_memory
from ai.ollama_client import OllamaError, get_ollama_client
from ai.prompt_engine import PromptEngine
from core.intent_engine import IntentEngine
from utils.logger import get_logger

logger = get_logger(__name__)


class Brain:
    """Two-tier mind: reflexes first, then agent/LLM for complex requests."""

    def __init__(self, intent_engine: IntentEngine | None = None) -> None:
        self.intent_engine = intent_engine or IntentEngine()
        self.prompt_engine = PromptEngine()
        self.client = get_ollama_client()
        self.agent = Agent(self.prompt_engine)
        self.memory = get_memory()

    def reason(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if not cleaned:
            return {"action": "unknown", "value": None}

        remember = self.memory.parse_remember_command(cleaned)
        if remember:
            return {"action": "__remember__", "value": remember}

        follow = self.memory.resolve_follow_up(cleaned)
        if follow:
            logger.info("Memory follow-up: %s", follow)
            return follow

        reflex = self.intent_engine.reflex_parse(cleaned)
        if reflex["action"] == "__instant__":
            if reflex.get("value") == "__time__":
                return {"action": "__instant__", "value": self._time_string()}
            return reflex
        if reflex["action"] not in {"unknown", "chat"}:
            logger.info("Reflex intent: %s", reflex)
            return reflex

        if reflex["action"] == "chat" or self._looks_like_chat(cleaned):
            return {"action": "chat", "value": cleaned}

        logger.info("Agent planning for: %s", cleaned)
        plan = self.agent.plan(cleaned, memory_context=self.memory.get_context_for_prompt())
        steps = Agent.normalize_plan(plan)
        if len(steps) > 1:
            return {"action": "__multi__", "value": steps}
        if steps and steps[0].get("action") not in {None, "unknown"}:
            logger.info("Agent intent: %s", steps[0])
            return steps[0]

        return {"action": "unknown", "value": cleaned}

    def chat(self, text: str) -> str:
        context = self.memory.get_context_for_prompt()
        prompt = self.prompt_engine.build_chat_prompt(text, memory_context=context)
        try:
            return self.client.chat(prompt, model=config.OLLAMA_MODEL)
        except OllamaError as exc:
            logger.warning("Chat failed: %s", exc)
            return "I'm having difficulty reaching my core systems. Is Ollama running?"

    @staticmethod
    def _looks_like_chat(text: str) -> bool:
        lowered = text.lower()
        return bool(
            re.match(
                r"^(what|who|why|how|when|where|tell me|explain|describe|can you)\b",
                lowered,
            )
        )

    @staticmethod
    def _time_string() -> str:
        return datetime.now().strftime("It's %I:%M %p.")
