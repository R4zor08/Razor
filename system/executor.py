"""Command execution coordinator."""

from __future__ import annotations

import re

from system.app_launcher import AppLauncher
from system.file_manager import FileManager
from system.system_control import SystemControl


class Executor:
    """Runs deterministic system commands from plain-text input."""

    HELP_TEXT = """
Available commands:
  open app <name>        Launch an application (e.g. open app notepad)
  launch <name>          Shorthand for open app
  close app <name>       Close an application (e.g. close app chrome)
  quit <name>            Shorthand for close app
  open folder <name>     Open Desktop, Downloads, Documents, or a path
  open <folder>          Shorthand (e.g. open desktop)
  open file <name>       Find and open a file by name
  search file <keyword>  Search for files by keyword
  find file <keyword>    Shorthand for search file
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
        if match:
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
