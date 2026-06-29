"""Window management."""

from __future__ import annotations

import platform
import time

import pyautogui
import pygetwindow as gw

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


class WindowController:
    """Controls application windows."""

    def minimize(self, target: str | None = None) -> str:
        """Minimize the active window or a window matching target."""
        window = self._resolve_window(target)
        if window:
            try:
                window.minimize()
                return f"Minimized {window.title}."
            except Exception as exc:
                return f"Failed to minimize window: {exc}"

        pyautogui.hotkey("win", "down")
        return "Minimized active window."

    def maximize(self, target: str | None = None) -> str:
        """Maximize the active window or a window matching target."""
        window = self._resolve_window(target)
        if window:
            try:
                if hasattr(window, "maximize"):
                    window.maximize()
                else:
                    self._focus_window(window)
                    pyautogui.hotkey("win", "up")
                return f"Maximized {window.title}."
            except Exception as exc:
                return f"Failed to maximize window: {exc}"

        pyautogui.hotkey("win", "up")
        return "Maximized active window."

    def close(self, target: str | None = None) -> str:
        """Close the active window or a window matching target."""
        window = self._resolve_window(target)
        if window:
            try:
                window.close()
                return f"Closed {window.title}."
            except Exception as exc:
                return f"Failed to close window: {exc}"

        pyautogui.hotkey("alt", "F4")
        return "Closed active window."

    def switch_app(self, target: str | None = None) -> str:
        """Switch focus to another application."""
        if target and target.lower() not in {"next", "previous", "back"}:
            window = self._resolve_window(target, partial=True)
            if window:
                try:
                    self._focus_window(window)
                    return f"Switched to {window.title}."
                except Exception as exc:
                    return f"Failed to switch to window: {exc}"
            return f"Could not find a window matching '{target}'."

        pyautogui.hotkey("alt", "tab")
        time.sleep(0.2)
        return "Switched to the next application."

    def _resolve_window(self, target: str | None, *, partial: bool = False):
        active = gw.getActiveWindow()
        if not target:
            return active

        query = target.strip().lower()
        if query in {"active", "current", "this"}:
            return active

        windows = gw.getAllWindows()
        visible = [w for w in windows if w.title and w.visible]
        for window in visible:
            if window.title.lower() == query:
                return window

        if partial:
            for window in visible:
                if query in window.title.lower():
                    return window

        return None

    @staticmethod
    def _focus_window(window) -> None:
        if platform.system() == "Windows":
            try:
                window.activate()
                return
            except Exception:
                pass
        window.restore()
        window.activate()
