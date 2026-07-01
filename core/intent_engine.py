"""Intent classification and parsing."""

from __future__ import annotations

import re
from typing import Any

import config
from ai.ollama_client import OllamaError, get_ollama_client
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
        "search_web",
        "open_url",
        "create_folder",
        "create_file",
        "set_volume",
        "set_brightness",
        "minimize_window",
        "maximize_window",
        "close_window",
        "switch_app",
        "run_shortcut",
        "type_text",
        "mouse_click",
        "scroll",
        "chat",
        "shutdown",
        "restart",
        "help",
        "exit",
        "unknown",
    }
)

NULL_VALUE_ACTIONS = frozenset(
    {
        "shutdown",
        "restart",
        "help",
        "exit",
        "minimize_window",
        "maximize_window",
        "close_window",
        "switch_app",
        "mouse_click",
    }
)


class IntentEngine:
    """Detects user intent from input text via the local Ollama LLM."""

    def __init__(self, prompt_engine: PromptEngine | None = None) -> None:
        self.client = get_ollama_client()
        self.prompt_engine = prompt_engine or PromptEngine()

    def parse(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if not cleaned:
            return {"action": "unknown", "value": None}

        reflex = self.reflex_parse(cleaned)
        if reflex["action"] != "unknown":
            return reflex

        prompt = self.prompt_engine.build_intent_prompt(cleaned)
        logger.info("Parsing intent for: %s", cleaned)

        try:
            raw = self.client.generate_json(
                prompt,
                model=config.OLLAMA_INTENT_MODEL or None,
            )
        except OllamaError as exc:
            logger.warning("Ollama error (%s), using rule-based intent fallback", exc)
            return reflex

        return self._validate_intent(raw, cleaned)

    def reflex_parse(self, text: str) -> dict[str, Any]:
        """Fast rule-based parse only — no Ollama."""
        return self._fallback_parse(text.strip())

    def _validate_intent(self, raw: dict[str, Any], original_text: str) -> dict[str, Any]:
        action = str(raw.get("action", "unknown")).strip().lower()
        value = raw.get("value")

        if action not in VALID_ACTIONS:
            return self._fallback_parse(original_text)

        if action in NULL_VALUE_ACTIONS:
            return {"action": action, "value": None}

        if action == "chat":
            return {"action": "chat", "value": str(value or original_text).strip()}

        if value is None or str(value).strip() == "":
            if action in {"set_volume", "set_brightness", "scroll", "run_shortcut", "type_text"}:
                return self._fallback_parse(original_text)
            if action in NULL_VALUE_ACTIONS:
                return {"action": action, "value": None}
            return self._fallback_parse(original_text)

        return {"action": action, "value": str(value).strip()}

    def _fallback_parse(self, text: str) -> dict[str, Any]:
        lowered = text.lower()

        if lowered in {"help", "?"}:
            return {"action": "help", "value": None}
        if lowered in {"exit", "quit", "bye"}:
            return {"action": "exit", "value": None}
        if any(p in lowered for p in ("shut down", "shutdown", "power off", "poweroff")):
            return {"action": "shutdown", "value": None}
        if any(p in lowered for p in ("restart", "reboot")):
            return {"action": "restart", "value": None}

        web_patterns = [
            (r"(?:search google for|google search|search the web for|search web for|google)\s+(.+)", "search_web"),
            (r"(?:search for|find)\s+(.+)\s+online", "search_web"),
        ]
        for pattern, action in web_patterns:
            match = re.search(pattern, lowered)
            if match:
                return {"action": action, "value": match.group(1).strip()}

        folder_patterns = [
            (r"create folder(?: called)?\s+(.+?)\s+on\s+desktop", "create_folder", "desktop/"),
            (r"make folder(?: called)?\s+(.+?)\s+on\s+desktop", "create_folder", "desktop/"),
            (r"create folder(?: called)?\s+(.+)", "create_folder", "desktop/"),
            (r"make a folder(?: called)?\s+(.+)", "create_folder", "desktop/"),
        ]
        for pattern, action, prefix in folder_patterns:
            match = re.search(pattern, lowered)
            if match:
                name = match.group(1).strip()
                return {"action": action, "value": f"{prefix}{name}"}

        file_patterns = [
            (r"create file(?: called)?\s+(.+)", "create_file", "desktop/"),
            (r"make file(?: called)?\s+(.+)", "create_file", "desktop/"),
        ]
        for pattern, action, prefix in file_patterns:
            match = re.search(pattern, lowered)
            if match:
                return {"action": action, "value": f"{prefix}{match.group(1).strip()}"}

        if lowered.startswith(("open http", "open www.")):
            return {"action": "open_url", "value": text[5:].strip()}

        known_sites = ("youtube", "gmail", "google", "facebook", "github", "netflix", "spotify", "reddit")
        for site in known_sites:
            if re.search(rf"\b(open|go to|launch)\s+{site}\b", lowered):
                return {"action": "open_url", "value": site}

        if any(p in lowered for p in ("volume up", "louder", "turn up the volume", "turn up volume")):
            return {"action": "set_volume", "value": "up"}
        if any(p in lowered for p in ("volume down", "quieter", "turn down the volume", "turn down volume")):
            return {"action": "set_volume", "value": "down"}
        if "unmute" in lowered:
            return {"action": "set_volume", "value": "unmute"}
        if "mute" in lowered:
            return {"action": "set_volume", "value": "mute"}
        if any(p in lowered for p in ("brightness up", "brighter")):
            return {"action": "set_brightness", "value": "up"}
        if any(p in lowered for p in ("brightness down", "dimmer")):
            return {"action": "set_brightness", "value": "down"}

        quick_apps = (
            "notepad", "calculator", "chrome", "firefox", "edge", "settings",
            "explorer", "paint", "cmd", "terminal", "spotify", "discord",
        )
        for app in quick_apps:
            if re.search(rf"\b(open|launch|start|run)\s+{app}\b", lowered):
                return {"action": "open_app", "value": app}

        if re.search(r"\bwhat time is it\b", lowered) or re.search(
            r"\bwhat(?:'s| is) the time\b", lowered
        ):
            return {"action": "__instant__", "value": "__time__"}
        if "minimize" in lowered:
            return {"action": "minimize_window", "value": None}
        if "maximize" in lowered:
            return {"action": "maximize_window", "value": None}
        if "close window" in lowered:
            return {"action": "close_window", "value": None}
        if lowered.startswith("switch to "):
            return {"action": "switch_app", "value": text[10:].strip()}

        patterns: list[tuple[str, str]] = [
            (r"(?:open|launch|start|run|go to)\s+(?:the\s+)?(?:app\s+)?(.+)", "open_app"),
            (r"(?:close|quit|kill|stop)\s+(?:the\s+)?(?:app\s+)?(.+)", "close_app"),
            (r"(?:open|show)\s+(?:my\s+)?(.+?)\s+folder", "open_folder"),
            (r"(?:find|search)\s+(?:my\s+)?(?:file\s+)?(.+)", "search_file"),
            (r"open file\s+(.+)", "open_file"),
            (r"(?:open|show|go to)\s+(?:my\s+)?(.+)$", "open_folder"),
        ]

        for pattern, action in patterns:
            match = re.search(pattern, lowered)
            if match:
                value = re.sub(r"\b(please|for me|now)\b", "", match.group(1)).strip()
                if value and value not in known_sites:
                    return {"action": action, "value": value}

        if lowered.startswith(("what ", "who ", "why ", "how ", "when ", "where ", "tell me ", "explain ")):
            return {"action": "chat", "value": text}

        return {"action": "unknown", "value": text}
