"""Intent classification and parsing."""

from __future__ import annotations

import re
from typing import Any

from ai.ollama_client import OllamaClient, OllamaError
from ai.prompt_engine import PromptEngine
from utils.logger import get_logger

logger = get_logger(__name__)

VALID_ACTIONS = frozenset(
    {
        "open_app",
        "close_app",
        "open_folder",
        "open_file",
        "search_file",
        "shutdown",
        "restart",
        "help",
        "exit",
        "unknown",
    }
)

NULL_VALUE_ACTIONS = frozenset({"shutdown", "restart", "help", "exit"})


class IntentEngine:
    """Detects user intent from input text via the local Ollama LLM."""

    def __init__(
        self,
        client: OllamaClient | None = None,
        prompt_engine: PromptEngine | None = None,
    ) -> None:
        self.client = client or OllamaClient()
        self.prompt_engine = prompt_engine or PromptEngine()

    def parse(self, text: str) -> dict[str, Any]:
        """
        Convert natural language into a structured command dict.

        Returns:
            {"action": str, "value": str | None}
        """
        cleaned = text.strip()
        if not cleaned:
            return {"action": "unknown", "value": None}

        prompt = self.prompt_engine.build_intent_prompt(cleaned)
        logger.info("Parsing intent for: %s", cleaned)

        try:
            raw = self.client.generate_json(prompt)
        except OllamaError as exc:
            logger.warning("Ollama error (%s), using rule-based intent fallback", exc)
            return self._fallback_parse(cleaned)

        return self._validate_intent(raw, cleaned)

    def _validate_intent(self, raw: dict[str, Any], original_text: str) -> dict[str, Any]:
        action = str(raw.get("action", "unknown")).strip().lower()
        value = raw.get("value")

        if action not in VALID_ACTIONS:
            logger.warning("Invalid action '%s' from model, marking unknown", action)
            return {"action": "unknown", "value": original_text}

        if action in NULL_VALUE_ACTIONS:
            return {"action": action, "value": None}

        if value is None or str(value).strip() == "":
            return {"action": "unknown", "value": original_text}

        return {"action": action, "value": str(value).strip()}

    def _fallback_parse(self, text: str) -> dict[str, Any]:
        """Simple keyword fallback when Ollama is unavailable."""
        lowered = text.lower()

        if lowered in {"help", "?"}:
            return {"action": "help", "value": None}
        if lowered in {"exit", "quit", "bye"}:
            return {"action": "exit", "value": None}
        if any(p in lowered for p in ("shut down", "shutdown", "power off", "poweroff")):
            return {"action": "shutdown", "value": None}
        if any(p in lowered for p in ("restart", "reboot")):
            return {"action": "restart", "value": None}

        patterns: list[tuple[str, str]] = [
            (r"(?:open|launch|start|run)\s+(?:the\s+)?(?:app\s+)?(.+)", "open_app"),
            (r"(?:close|quit|kill|stop)\s+(?:the\s+)?(?:app\s+)?(.+)", "close_app"),
            (r"(?:open|show|go to)\s+(?:my\s+)?(.+?)(?:\s+folder)?$", "open_folder"),
            (r"(?:find|search for|search)\s+(?:my\s+)?(.+)", "search_file"),
            (r"open file\s+(.+)", "open_file"),
        ]

        for pattern, action in patterns:
            match = re.search(pattern, lowered)
            if match:
                value = match.group(1).strip()
                value = re.sub(r"\b(please|for me|now)\b", "", value).strip()
                if value:
                    if action == "open_folder" and value.endswith(" folder"):
                        value = value[: -len(" folder")]
                    return {"action": action, "value": value}

        return {"action": "unknown", "value": text}
