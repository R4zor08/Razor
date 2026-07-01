"""Persistent memory for Jarvis-style context and preferences."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config
from utils.helpers import ensure_dir
from utils.logger import get_logger

logger = get_logger(__name__)

MEMORY_PATH = Path(config.ASSETS_DIR) / "data" / "memory.json"


class Memory:
    """Stores user context across sessions."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or MEMORY_PATH
        ensure_dir(str(self.path.parent))
        self._data: dict[str, Any] = self._load()

    def remember(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    def recall(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def add_command(self, text: str) -> None:
        recent: list[str] = list(self._data.get("last_commands", []))
        recent.insert(0, text.strip())
        self._data["last_commands"] = recent[:5]
        self._save()

    def set_last_opened_app(self, app_name: str) -> None:
        self._data["last_opened_app"] = app_name.strip()
        self._save()

    def get_context_for_prompt(self) -> str:
        parts: list[str] = []
        name = self._data.get("user_name")
        if name:
            parts.append(f"User name: {name}")
        last_app = self._data.get("last_opened_app")
        if last_app:
            parts.append(f"Last opened app: {last_app}")
        recent = self._data.get("last_commands", [])
        if recent:
            parts.append(f"Recent commands: {', '.join(recent[:3])}")
        prefs = self._data.get("preferences", {})
        if prefs:
            parts.append(f"Preferences: {prefs}")
        return "\n".join(parts)

    def summary(self) -> str:
        lines = ["Here's what I remember:"]
        if self._data.get("user_name"):
            lines.append(f"  Name: {self._data['user_name']}")
        if self._data.get("last_opened_app"):
            lines.append(f"  Last app: {self._data['last_opened_app']}")
        recent = self._data.get("last_commands", [])
        if recent:
            lines.append(f"  Recent: {', '.join(recent)}")
        if len(lines) == 1:
            lines.append("  Nothing stored yet.")
        return "\n".join(lines)

    def parse_remember_command(self, text: str) -> str | None:
        lowered = text.lower().strip()
        patterns = [
            (r"remember my name is (.+)", "user_name"),
            (r"my name is (.+)", "user_name"),
            (r"call me (.+)", "user_name"),
        ]
        import re

        for pattern, key in patterns:
            match = re.match(pattern, lowered)
            if match:
                value = match.group(1).strip().title()
                self.remember(key, value)
                return f"Certainly. I'll call you {value}."
        if lowered in {"what do you remember", "what do you remember?", "what do you recall"}:
            return self.summary()
        if lowered in {"what's my name", "what is my name", "whats my name"}:
            name = self.recall("user_name")
            return f"Your name is {name}." if name else "I don't have your name stored yet."
        return None

    def resolve_follow_up(self, text: str) -> dict[str, Any] | None:
        lowered = text.lower().strip()
        if lowered in {
            "open it again",
            "open that again",
            "launch it again",
            "open it",
            "launch it again",
        }:
            app = self.recall("last_opened_app")
            if app:
                return {"action": "open_app", "value": str(app)}
        return None

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"last_commands": [], "preferences": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load memory: %s", exc)
        return {"last_commands": [], "preferences": {}}

    def _save(self) -> None:
        self._data["updated_at"] = datetime.now(timezone.utc).isoformat()
        try:
            self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not save memory: %s", exc)


_memory: Memory | None = None


def get_memory() -> Memory:
    global _memory
    if _memory is None:
        _memory = Memory()
    return _memory
