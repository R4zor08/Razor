"""File and directory operations."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

import config

SPECIAL_FOLDERS: dict[str, str] = {
    "desktop": "Desktop",
    "downloads": "Downloads",
    "documents": "Documents",
    "pictures": "Pictures",
    "music": "Music",
    "videos": "Videos",
    "home": "",
}

# Windows User Shell Folders registry value names
_WINDOWS_SHELL_KEYS: dict[str, str] = {
    "desktop": "Desktop",
    "documents": "Personal",
    "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
    "pictures": "My Pictures",
    "music": "My Music",
    "videos": "My Video",
}


class FileManager:
    """Handles file system tasks."""

    def __init__(self) -> None:
        self._home = Path.home()

    def open_folder(self, target: str) -> str:
        """Open a special folder or path in the file explorer."""
        query = target.strip().lower()
        if not query:
            return "Please specify a folder name or path."

        path = self._resolve_folder_path(query)
        if not path:
            return f"Could not find folder '{target}'."

        if not path.is_dir():
            return f"'{path}' is not a folder."

        return self._open_path(path)

    def open_file(self, name: str, search_roots: list[Path] | None = None) -> str:
        """Find and open a file by name."""
        query = name.strip()
        if not query:
            return "Please specify a file name."

        if os.path.isfile(query):
            return self._open_path(Path(query))

        matches = self.search_files(query, search_roots=search_roots)
        if not matches:
            return f"No file found matching '{name}'."

        best = matches[0]
        return self._open_path(Path(best))

    def search_files(
        self,
        keyword: str,
        search_roots: list[Path] | None = None,
    ) -> list[str]:
        """Search for files whose names contain the keyword."""
        query = keyword.strip().lower()
        if not query:
            return []

        roots = search_roots or self._default_search_roots()
        results: list[str] = []
        seen: set[str] = set()

        for root in roots:
            if not root.is_dir():
                continue
            for path in self._walk_files(root, config.FILE_SEARCH_DEPTH):
                if query not in path.name.lower():
                    continue
                resolved = str(path.resolve())
                if resolved in seen:
                    continue
                seen.add(resolved)
                results.append(resolved)
                if len(results) >= config.FILE_SEARCH_MAX_RESULTS:
                    return results

        return results

    def format_search_results(self, keyword: str, results: list[str]) -> str:
        """Format file search results for CLI output."""
        if not results:
            return f"No files found matching '{keyword}'."

        lines = [f"Found {len(results)} file(s) matching '{keyword}':"]
        for index, path in enumerate(results, start=1):
            lines.append(f"  {index}. {path}")
        if len(results) >= config.FILE_SEARCH_MAX_RESULTS:
            lines.append(f"  (showing first {config.FILE_SEARCH_MAX_RESULTS} results)")
        return "\n".join(lines)

    def create_folder(self, target: str) -> str:
        """Create a folder on desktop, in documents, or at a path."""
        path = self._resolve_create_path(target, expect_file=False)
        if path is None:
            return f"Could not resolve folder location for '{target}'."
        try:
            path.mkdir(parents=True, exist_ok=True)
            return f"Created folder {path}."
        except OSError as exc:
            return f"Failed to create folder: {exc}"

    def create_file(self, target: str, content: str = "") -> str:
        """Create a file with optional text content."""
        path = self._resolve_create_path(target, expect_file=True)
        if path is None:
            return f"Could not resolve file location for '{target}'."
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return f"Created file {path}."
        except OSError as exc:
            return f"Failed to create file: {exc}"

    def _resolve_create_path(self, target: str, *, expect_file: bool) -> Path | None:
        text = target.strip()
        if not text:
            return None

        if "|" in text:
            text = text.split("|", 1)[0].strip()

        lowered = text.lower()
        for prefix in ("on desktop ", "on my desktop ", "in documents ", "in downloads "):
            if lowered.startswith(prefix):
                location = prefix.strip().split()[0].replace("on", "").replace("in", "").strip()
                if "desktop" in prefix:
                    base = self._resolve_folder_path("desktop") or self._home / "Desktop"
                elif "documents" in prefix:
                    base = self._resolve_folder_path("documents") or self._home / "Documents"
                else:
                    base = self._resolve_folder_path("downloads") or self._home / "Downloads"
                name = text[len(prefix) :].strip()
                return base / name

        if lowered.startswith("called "):
            text = text[7:].strip()

        for location in ("desktop", "documents", "downloads", "home"):
            token = f"{location}/"
            if lowered.startswith(token):
                base = self._resolve_folder_path(location) or self._home
                remainder = text[len(token) :]
                return base / remainder

        if "/" in text or "\\" in text:
            return Path(text)

        base = self._resolve_folder_path("desktop") or self._home
        path = base / text
        if expect_file and not path.suffix:
            path = path.with_suffix(".txt")
        return path

    def _resolve_folder_path(self, query: str) -> Path | None:
        if query in SPECIAL_FOLDERS:
            if query == "home":
                return self._home

            shell_path = self._windows_shell_folder(query)
            if shell_path:
                return shell_path

            sub = SPECIAL_FOLDERS[query]
            candidates = [
                self._home / sub,
                self._home / "OneDrive" / sub,
            ]
            for candidate in candidates:
                if candidate.is_dir():
                    return candidate
            return candidates[0] if candidates[0].exists() else None

        expanded = os.path.expandvars(os.path.expanduser(query))
        if os.path.isdir(expanded):
            return Path(expanded)

        candidate = self._home / query
        if candidate.is_dir():
            return candidate

        return None

    def _windows_shell_folder(self, name: str) -> Path | None:
        """Resolve a known folder via the Windows User Shell Folders registry key."""
        if platform.system() != "Windows" or name not in _WINDOWS_SHELL_KEYS:
            return None

        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            )
            value, _ = winreg.QueryValueEx(key, _WINDOWS_SHELL_KEYS[name])
            winreg.CloseKey(key)
            path = Path(os.path.expandvars(value))
            return path if path.is_dir() else None
        except OSError:
            return None

    def _default_search_roots(self) -> list[Path]:
        if config.FILE_SEARCH_WIDE:
            return [self._home]

        names = ("desktop", "downloads", "documents", "pictures", "videos", "music")
        roots: list[Path] = []
        for name in names:
            path = self._resolve_folder_path(name)
            if path and path.is_dir():
                roots.append(path)
        roots.append(self._home)
        unique: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            key = str(root.resolve()) if root.exists() else str(root)
            if key not in seen:
                seen.add(key)
                unique.append(root)
        return unique

    def _walk_files(self, root: Path, max_depth: int):
        root = root.resolve()
        stack: list[tuple[Path, int]] = [(root, 0)]

        while stack:
            current, depth = stack.pop()
            if depth > max_depth:
                continue
            try:
                entries = list(current.iterdir())
            except OSError:
                continue

            for entry in entries:
                if entry.is_file():
                    yield entry
                elif entry.is_dir() and not entry.name.startswith("."):
                    skip_dirs = {".git", "node_modules", "__pycache__", "AppData", "venv", ".venv"}
                    if entry.name in skip_dirs and config.FILE_SEARCH_WIDE:
                        continue
                    stack.append((entry, depth + 1))

    def _open_path(self, path: Path) -> str:
        try:
            if platform.system() == "Windows":
                os.startfile(str(path))  # noqa: S606
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(path)], start_new_session=True)
            else:
                subprocess.Popen(["xdg-open", str(path)], start_new_session=True)
            return f"Opened {path}."
        except OSError as exc:
            return f"Failed to open {path}: {exc}"
