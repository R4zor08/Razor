"""Safety checks for destructive or sensitive system actions."""

from __future__ import annotations

from typing import Any

import config

CONFIRMATION_PHRASES = frozenset(
    {
        "yes",
        "yeah",
        "yep",
        "confirm",
        "confirmed",
        "do it",
        "go ahead",
        "sure",
        "affirmative",
    }
)

DESTRUCTIVE_ACTIONS = frozenset({"shutdown", "restart"})

SENSITIVE_ACTIONS = frozenset(
    {
        "close_app",
        "close_window",
        "run_shortcut",
        "type_text",
        "mouse_click",
    }
)


class SafetyGuard:
    """Blocks or confirms risky operations before execution."""

    def __init__(self) -> None:
        self._pending_action: dict[str, Any] | None = None
        self._pending_label: str | None = None

    @property
    def has_pending_confirmation(self) -> bool:
        return self._pending_action is not None

    def check_intent(self, intent: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate an intent before execution.

        Returns:
            (allowed, message_if_blocked)
        """
        action = intent.get("action", "unknown")

        if action in DESTRUCTIVE_ACTIONS and config.SAFE_MODE:
            self._pending_action = intent
            self._pending_label = action
            return False, self._confirmation_prompt(action)

        if action in SENSITIVE_ACTIONS and config.SAFE_MODE_STRICT:
            self._pending_action = intent
            self._pending_label = action
            return False, self._confirmation_prompt(action)

        return True, None

    def try_confirm(self, text: str) -> dict[str, Any] | None:
        """Confirm a pending action from user speech or text."""
        if not self._pending_action:
            return None

        normalized = text.strip().lower()
        if normalized not in CONFIRMATION_PHRASES:
            return None

        intent = self._pending_action
        self.clear_pending()
        return intent

    def clear_pending(self) -> None:
        self._pending_action = None
        self._pending_label = None

    def cancel_pending(self) -> str:
        if not self._pending_action:
            return "Nothing to cancel."
        label = self._pending_label or "that action"
        self.clear_pending()
        return f"Cancelled {label.replace('_', ' ')}."

    @staticmethod
    def _confirmation_prompt(action: str) -> str:
        readable = action.replace("_", " ")
        return f"That will {readable} the system. Say 'yes' to confirm or 'cancel' to abort."
