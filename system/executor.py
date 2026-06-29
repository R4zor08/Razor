"""Command execution coordinator."""

from __future__ import annotations

import re

from system.app_launcher import AppLauncher
from system.automation import Automation
from system.file_manager import FileManager
from system.system_control import SystemControl
from system.window_controller import WindowController


class Executor:
    """Runs deterministic system commands from plain-text input."""

    HELP_TEXT = """
Available commands:
  open app <name>        Launch an application
  close app <name>       Close an application
  open folder <name>     Open Desktop, Downloads, Documents, or a path
  open file <name>       Find and open a file by name
  search file <keyword>  Search for files by keyword
  volume <up|down|mute|50>   Control system volume
  brightness <up|down|50>    Control display brightness
  minimize [window]      Minimize active or named window
  maximize [window]      Maximize active or named window
  close window [name]    Close active or named window
  switch app [name]      Switch to next app or named window
  shortcut <keys>        Run shortcut (e.g. copy, ctrl+c, win+d)
  type <text>            Type text at cursor
  click [left|right|x,y] Mouse click
  scroll <up|down>       Scroll the mouse wheel
  shutdown               Shut down the computer
  restart                Restart the computer
  help                   Show this help
  exit / quit            Exit Razor CLI
""".strip()

    _FOLDER_NAMES = frozenset(
        {"desktop", "downloads", "documents", "pictures", "music", "videos", "home"}
    )

    def __init__(self) -> None:
        self.app_launcher = AppLauncher()
        self.file_manager = FileManager()
        self.system_control = SystemControl()
        self.window_controller = WindowController()
        self.automation = Automation()

    def execute(self, command: str) -> str:
        """Parse and run a user command."""
        text = command.strip()
        if not text:
            return "Enter a command. Type 'help' for available commands."

        lowered = text.lower()

        if lowered in {"help", "?"}:
            return self.HELP_TEXT

        if lowered in {"exit", "quit", "bye"}:
            return "__EXIT__"

        if lowered in {"shutdown", "shut down", "power off", "poweroff"}:
            return self.system_control.shutdown()

        if lowered in {"restart", "reboot"}:
            return self.system_control.restart()

        match = re.match(r"^volume\s+(.+)$", text, re.IGNORECASE)
        if match:
            return self.system_control.set_volume(match.group(1))

        match = re.match(r"^brightness\s+(.+)$", text, re.IGNORECASE)
        if match:
            return self.system_control.set_brightness(match.group(1))

        match = re.match(r"^minimize(?:\s+(.+))?$", text, re.IGNORECASE)
        if match:
            return self.window_controller.minimize(match.group(1))

        match = re.match(r"^maximize(?:\s+(.+))?$", text, re.IGNORECASE)
        if match:
            return self.window_controller.maximize(match.group(1))

        match = re.match(r"^close window(?:\s+(.+))?$", text, re.IGNORECASE)
        if match:
            return self.window_controller.close(match.group(1))

        match = re.match(r"^switch app(?:\s+(.+))?$", text, re.IGNORECASE)
        if match:
            return self.window_controller.switch_app(match.group(1))

        match = re.match(r"^(?:shortcut|hotkey)\s+(.+)$", text, re.IGNORECASE)
        if match:
            return self.automation.run_shortcut(match.group(1))

        match = re.match(r"^type\s+(.+)$", text, re.IGNORECASE)
        if match:
            return self.automation.type_text(match.group(1))

        match = re.match(r"^click(?:\s+(.+))?$", text, re.IGNORECASE)
        if match:
            return self.automation.mouse_click(match.group(1))

        match = re.match(r"^scroll\s+(.+)$", text, re.IGNORECASE)
        if match:
            return self.automation.scroll(match.group(1))

        match = re.match(
            r"^(?:open app|launch app|launch|start app|start)\s+(.+)$",
            text,
            re.IGNORECASE,
        )
        if match:
            return self.app_launcher.open_app(match.group(1))

        match = re.match(
            r"^(?:close app|close|quit app|kill app|kill|stop app|stop)\s+(.+)$",
            text,
            re.IGNORECASE,
        )
        if match and not lowered.startswith("close window"):
            return self.app_launcher.close_app(match.group(1))

        match = re.match(
            r"^(?:search file|search files|find file|find files|search for file|find)\s+(.+)$",
            text,
            re.IGNORECASE,
        )
        if match:
            keyword = match.group(1)
            results = self.file_manager.search_files(keyword)
            return self.file_manager.format_search_results(keyword, results)

        match = re.match(r"^open file\s+(.+)$", text, re.IGNORECASE)
        if match:
            return self.file_manager.open_file(match.group(1))

        match = re.match(r"^open folder\s+(.+)$", text, re.IGNORECASE)
        if match:
            return self.file_manager.open_folder(match.group(1))

        match = re.match(r"^open\s+(.+)$", text, re.IGNORECASE)
        if match:
            return self._open_generic(match.group(1))

        return (
            f"Unknown command: '{text}'\n"
            "Type 'help' for available commands."
        )

    def execute_intent(self, intent: dict[str, str | None]) -> str:
        """Run a structured intent produced by the intent engine."""
        action = intent.get("action", "unknown")
        value = intent.get("value")

        if action == "help":
            return self.HELP_TEXT

        if action == "exit":
            return "__EXIT__"

        if action == "shutdown":
            return self.system_control.shutdown()

        if action == "restart":
            return self.system_control.restart()

        if action == "set_volume" and value:
            return self.system_control.set_volume(value)

        if action == "set_brightness" and value:
            return self.system_control.set_brightness(value)

        if action == "minimize_window":
            return self.window_controller.minimize(value)

        if action == "maximize_window":
            return self.window_controller.maximize(value)

        if action == "close_window":
            return self.window_controller.close(value)

        if action == "switch_app":
            return self.window_controller.switch_app(value)

        if action == "run_shortcut" and value:
            return self.automation.run_shortcut(value)

        if action == "type_text" and value:
            return self.automation.type_text(value)

        if action == "mouse_click":
            return self.automation.mouse_click(value)

        if action == "scroll" and value:
            return self.automation.scroll(value)

        if action == "open_app" and value:
            return self.app_launcher.open_app(value)

        if action == "close_app" and value:
            return self.app_launcher.close_app(value)

        if action == "open_folder" and value:
            return self.file_manager.open_folder(value)

        if action == "open_file" and value:
            return self.file_manager.open_file(value)

        if action == "search_file" and value:
            results = self.file_manager.search_files(value)
            return self.file_manager.format_search_results(value, results)

        if action == "unknown":
            original = value or "that request"
            return (
                f"I don't know how to handle '{original}'.\n"
                "Type 'help' for available commands."
            )

        return (
            f"Unknown action: '{action}'\n"
            "Type 'help' for available commands."
        )

    def _open_generic(self, target: str) -> str:
        """Resolve ambiguous 'open <target>' commands."""
        stripped = target.strip()
        lowered = stripped.lower()

        if lowered in self._FOLDER_NAMES or self._looks_like_path(stripped):
            return self.file_manager.open_folder(stripped)

        app_result = self.app_launcher.open_app(stripped)
        if not app_result.startswith("Could not find"):
            return app_result

        file_result = self.file_manager.open_file(stripped)
        if not file_result.startswith("No file found"):
            return file_result

        folder_result = self.file_manager.open_folder(stripped)
        if not folder_result.startswith("Could not find"):
            return folder_result

        return app_result

    def _looks_like_path(self, target: str) -> bool:
        if "\\" in target or "/" in target:
            return True
        return bool(re.match(r"^[a-z]:\\", target, re.IGNORECASE))
