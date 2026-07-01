"""Agent tool loop for non-reflex commands."""

from __future__ import annotations

import json
from typing import Any

import config
from ai.ollama_client import OllamaClient, OllamaError
from ai.prompt_engine import PromptEngine
from utils.logger import get_logger

logger = get_logger(__name__)

AGENT_TIMEOUT = 8


class Agent:
    """Uses Ollama to pick tools / multi-step plans when reflex rules miss."""

    def __init__(self, prompt_engine: PromptEngine | None = None) -> None:
        self.client = OllamaClient(timeout=AGENT_TIMEOUT)
        self.prompt_engine = prompt_engine or PromptEngine()

    def plan(self, text: str, *, memory_context: str = "") -> dict[str, Any] | list[dict[str, Any]]:
        prompt = self.prompt_engine.build_agent_prompt(text, memory_context=memory_context)
        try:
            raw = self.client.generate_json(
                prompt,
                model=config.OLLAMA_INTENT_MODEL or None,
            )
        except OllamaError as exc:
            logger.warning("Agent plan failed: %s", exc)
            return {
                "action": "__instant__",
                "value": "I'm having trouble thinking — try a simpler command.",
            }

        if isinstance(raw.get("steps"), list):
            steps = raw["steps"][:3]
            valid = [s for s in steps if isinstance(s, dict) and s.get("action")]
            if valid:
                return valid
        if raw.get("action"):
            return raw
        return {"action": "unknown", "value": text}

    @staticmethod
    def normalize_plan(plan: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
        if isinstance(plan, list):
            return plan
        return [plan]
