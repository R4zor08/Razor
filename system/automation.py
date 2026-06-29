"""Task automation workflows."""

from __future__ import annotations

import re

import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

KNOWN_SHORTCUTS: dict[str, list[str]] = {
    "copy": ["ctrl", "c"],
    "paste": ["ctrl", "v"],
    "cut": ["ctrl", "x"],
    "undo": ["ctrl", "z"],
    "redo": ["ctrl", "y"],
    "save": ["ctrl", "s"],
    "select all": ["ctrl", "a"],
    "find": ["ctrl", "f"],
    "new tab": ["ctrl", "t"],
    "close tab": ["ctrl", "w"],
    "screenshot": ["win", "shift", "s"],
    "task manager": ["ctrl", "shift", "esc"],
    "lock": ["win", "l"],
    "desktop": ["win", "d"],
    "run": ["win", "r"],
}


class Automation:
    """Keyboard, mouse, and shortcut automation."""

    def run_shortcut(self, value: str) -> str:
        """Execute a keyboard shortcut such as ctrl+c or 'copy'."""
        keys = self._parse_shortcut(value)
        if not keys:
            return f"Unknown shortcut '{value}'."

        pyautogui.hotkey(*keys)
        return f"Ran shortcut {'+'.join(keys)}."

    def type_text(self, value: str) -> str:
        """Type text at the current cursor position."""
        text = value.strip()
        if not text:
            return "Nothing to type."
        pyautogui.write(text, interval=0.02)
        return f"Typed: {text}"

    def press_key(self, value: str) -> str:
        """Press a single key such as enter or escape."""
        key = value.strip().lower()
        if not key:
            return "No key specified."
        pyautogui.press(key)
        return f"Pressed {key}."

    def mouse_click(self, value: str | None = None) -> str:
        """
        Click the mouse.

        value: left, right, double, or 'x,y' coordinates
        """
        if not value:
            pyautogui.click()
            return "Left clicked."

        normalized = value.strip().lower()
        if normalized in {"left", "click"}:
            pyautogui.click()
            return "Left clicked."
        if normalized == "right":
            pyautogui.rightClick()
            return "Right clicked."
        if normalized in {"double", "double click"}:
            pyautogui.doubleClick()
            return "Double clicked."

        match = re.match(r"(-?\d+)\s*,\s*(-?\d+)", normalized)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            pyautogui.click(x=x, y=y)
            return f"Clicked at ({x}, {y})."

        return "Mouse value must be left, right, double, or x,y coordinates."

    def move_mouse(self, value: str) -> str:
        """Move mouse to x,y coordinates."""
        match = re.match(r"(-?\d+)\s*,\s*(-?\d+)", value.strip())
        if not match:
            return "Move mouse value must be x,y coordinates."
        x, y = int(match.group(1)), int(match.group(2))
        pyautogui.moveTo(x, y, duration=0.2)
        return f"Moved mouse to ({x}, {y})."

    def scroll(self, value: str) -> str:
        """Scroll up or down."""
        normalized = value.strip().lower()
        amount = 500
        match = re.search(r"(-?\d+)", normalized)
        if match:
            amount = int(match.group(1))

        if "up" in normalized:
            pyautogui.scroll(abs(amount))
            return "Scrolled up."
        if "down" in normalized:
            pyautogui.scroll(-abs(amount))
            return "Scrolled down."

        pyautogui.scroll(-abs(amount))
        return f"Scrolled {amount} units."

    def _parse_shortcut(self, value: str) -> list[str] | None:
        normalized = value.strip().lower()
        if normalized in KNOWN_SHORTCUTS:
            return KNOWN_SHORTCUTS[normalized]

        if "+" in normalized:
            return [part.strip() for part in normalized.split("+") if part.strip()]

        if normalized in pyautogui.KEYBOARD_KEYS:
            return [normalized]

        return None
