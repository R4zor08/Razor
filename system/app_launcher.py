"""Application launching."""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from pathlib import Path


# Friendly name -> executable or shortcut stem used for lookup
APP_ALIASES: dict[str, str] = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "outlook": "outlook.exe",
    "vscode": "code.exe",
    "visual studio code": "code.exe",
    "code": "code.exe",
    "spotify": "spotify.exe",
    "discord": "discord.exe",
    "steam": "steam.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
}

PROCESS_ALIASES: dict[str, str] = {
    **APP_ALIASES,
    "teams": "teams.exe",
    "slack": "slack.exe",
    "zoom": "zoom.exe",
}


class AppLauncher:
    """Opens and manages. Supports .exe paths and Start Menu shortcuts."""

    def __init__(self) -> None:
        self._start_menu_dirs = self._build_start_menu_dirs()

    def open_app(self, name: str) -> str:
        """Launch an application by friendly name, alias, or path."""
        query = self._normalize(name)
        if not query:
            return "Please specify an application name."

        if os.path.isfile(query) and query.lower().endswith((".exe", ".lnk", ".bat", ".cmd")):
            return self._launch_path(Path(query))

        path = self._resolve_app_path(query)
        if path:
            return self._launch_path(path)

        return f"Could not find application '{name}'."

    def close_app(self, name: str) -> str:
        """Close an application by terminating its process."""
        query = self._normalize(name)
        if not query:
            return "Please specify an application to close."

        process_name = self._resolve_process_name(query)
        if not process_name:
            return f"Could not resolve process for '{name}'."

        if platform.system() == "Windows":
            result = subprocess.run(
                ["taskkill", "/IM", process_name, "/F"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return f"Closed {process_name}."
            if "not found" in result.stderr.lower():
                return f"No running process found for '{name}' ({process_name})."
            return f"Failed to close {process_name}: {result.stderr.strip()}"

        result = subprocess.run(["pkill", "-f", process_name], capture_output=True, text=True)
        if result.returncode == 0:
            return f"Closed processes matching {process_name}."
        return f"No running process found for '{name}'."

    def _normalize(self, name: str) -> str:
        cleaned = re.sub(r"\s+", " ", name.strip().lower())
        cleaned = re.sub(r"\b(the|app|application)\b", "", cleaned).strip()
        return cleaned

    def _build_start_menu_dirs(self) -> list[Path]:
        if platform.system() != "Windows":
            return []

        dirs: list[Path] = []
        program_data = os.environ.get("ProgramData", r"C:\ProgramData")
        app_data = os.environ.get("APPDATA", "")

        candidates = [
            Path(program_data) / "Microsoft/Windows/Start Menu/Programs",
            Path(app_data) / "Microsoft/Windows/Start Menu/Programs",
        ]
        for path in candidates:
            if path.is_dir():
                dirs.append(path)
        return dirs

    def _resolve_app_path(self, query: str) -> Path | None:
        alias_target = self._match_alias(query, APP_ALIASES)
        if alias_target:
            resolved = self._find_executable(alias_target, query)
            if resolved:
                return resolved

        shortcut = self._find_shortcut(query)
        if shortcut:
            return shortcut

        direct = self._find_executable(f"{query}.exe", query)
        if direct:
            return direct

        return self._find_executable(query, query)

    def _match_alias(self, query: str, aliases: dict[str, str]) -> str | None:
        if query in aliases:
            return aliases[query]

        for alias, target in aliases.items():
            if query in alias or alias in query:
                return target

        return None

    def _find_executable(self, executable: str, query: str) -> Path | None:
        if platform.system() == "Windows":
            which = shutil.which(executable)
            if which:
                return Path(which)

            where = subprocess.run(
                ["where", executable],
                capture_output=True,
                text=True,
            )
            if where.returncode == 0:
                first = where.stdout.strip().splitlines()[0]
                return Path(first)

        shortcut = self._find_shortcut(query)
        if shortcut:
            return shortcut

        if platform.system() != "Windows":
            which = shutil.which(executable)
            return Path(which) if which else None

        program_files = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
        ]

        exe_name = executable if executable.lower().endswith(".exe") else f"{executable}.exe"
        for root in program_files:
            if not root:
                continue
            base = Path(root)
            if not base.is_dir():
                continue
            try:
                for match in base.rglob(exe_name):
                    if match.is_file():
                        return match
            except OSError:
                continue

        return None

    def _find_shortcut(self, query: str) -> Path | None:
        best: Path | None = None
        best_score = -1

        for start_dir in self._start_menu_dirs:
            try:
                for shortcut in start_dir.rglob("*.lnk"):
                    stem = shortcut.stem.lower()
                    score = self._match_score(query, stem)
                    if score > best_score:
                        best_score = score
                        best = shortcut
            except OSError:
                continue

        return best if best_score > 0 else None

    def _match_score(self, query: str, candidate: str) -> int:
        if query == candidate:
            return 100
        if candidate.startswith(query):
            return 80
        if query in candidate:
            return 60
        query_words, candidate_words = query.split(), candidate.split()
        overlap = sum(1 for word in query_words if any(word in part for part in candidate_words))
        return overlap * 20

    def _resolve_process_name(self, query: str) -> str | None:
        alias = self._match_alias(query, PROCESS_ALIASES)
        if alias:
            return alias if alias.lower().endswith(".exe") else f"{alias}.exe"

        path = self._resolve_app_path(query)
        if path:
            if path.suffix.lower() == ".lnk":
                alias = self._match_alias(query, PROCESS_ALIASES)
                if alias:
                    return alias if alias.lower().endswith(".exe") else f"{alias}.exe"
            return path.name

        guess = f"{query}.exe" if not query.endswith(".exe") else query
        return guess

    def _launch_path(self, path: Path) -> str:
        try:
            if platform.system() == "Windows":
                os.startfile(str(path))  # noqa: S606
            else:
                subprocess.Popen([str(path)], start_new_session=True)
            return f"Opened {path.name}."
        except OSError as exc:
            return f"Failed to open {path.name}: {exc}"
