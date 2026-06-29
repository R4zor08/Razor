"""Windows startup installation helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import config


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def startup_folder() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA environment variable is not set.")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def install_startup() -> str:
    """Create a Startup folder shortcut that launches Razor on login."""
    root = project_root()
    launcher = root / "scripts" / "start_razor.bat"
    if not launcher.is_file():
        raise FileNotFoundError(f"Launcher not found: {launcher}")

    shortcut_path = startup_folder() / f"{config.STARTUP_FOLDER_NAME}.bat"
    target_cmd = f'"{launcher}"'
    shortcut_path.write_text(
        f'@echo off\r\nstart "" {target_cmd}\r\n',
        encoding="utf-8",
    )
    return f"Installed startup launcher at {shortcut_path}"


def uninstall_startup() -> str:
    shortcut_path = startup_folder() / f"{config.STARTUP_FOLDER_NAME}.bat"
    if shortcut_path.exists():
        shortcut_path.unlink()
        return f"Removed startup launcher from {shortcut_path}"
    return "Startup launcher was not installed."


def open_startup_folder() -> None:
    folder = startup_folder()
    if sys.platform == "win32":
        os.startfile(folder)  # noqa: S606
    else:
        subprocess.Popen(["xdg-open", str(folder)])
