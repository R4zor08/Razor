"""Global hotkey registration for instant Razor activation."""

from __future__ import annotations

import threading
from collections.abc import Callable

from utils.logger import get_logger

logger = get_logger(__name__)


class GlobalHotkey:
    """Register a system-wide hotkey that runs a callback in a background thread."""

    def __init__(self, hotkey: str, callback: Callable[[], None]) -> None:
        self.hotkey_str = hotkey
        self.callback = callback
        self._listener = None
        self._hotkey = None

    def start(self) -> None:
        try:
            from pynput import keyboard
        except ImportError:
            logger.warning("pynput not installed; global hotkey disabled.")
            return

        try:
            self._hotkey = keyboard.HotKey(
                keyboard.HotKey.parse(self.hotkey_str),
                self._on_activate,
            )
        except ValueError as exc:
            logger.warning("Invalid hotkey '%s': %s", self.hotkey_str, exc)
            return

        def on_press(key: keyboard.Key | keyboard.KeyCode) -> None:
            if self._hotkey is not None:
                self._hotkey.press(key)

        def on_release(key: keyboard.Key | keyboard.KeyCode) -> None:
            if self._hotkey is not None:
                self._hotkey.release(key)

        self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self._listener.start()
        logger.info("Global hotkey registered: %s", self.hotkey_str)

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def _on_activate(self) -> None:
        threading.Thread(target=self._safe_callback, daemon=True, name="razor-hotkey").start()

    def _safe_callback(self) -> None:
        try:
            self.callback()
        except Exception as exc:
            logger.exception("Hotkey callback failed: %s", exc)
