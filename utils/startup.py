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


def _pythonw_path() -> Path:
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    return pythonw if pythonw.is_file() else exe


def _write_launcher_scripts(root: Path) -> Path:
    scripts = root / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)

    pythonw = _pythonw_path()
    main_py = root / "main.py"

    bat_path = scripts / "start_razor.bat"
    bat_path.write_text(
        f'@echo off\r\ncd /d "{root}"\r\n"{pythonw}" "{main_py}" --tray\r\n',
        encoding="utf-8",
    )

    vbs_path = scripts / "start_razor.vbs"
    vbs_path.write_text(
        "\r\n".join(
            [
                'Set shell = CreateObject("WScript.Shell")',
                f'shell.CurrentDirectory = "{root}"',
                f'shell.Run """{pythonw}"" ""{main_py}"" --tray", 0, False',
            ]
        )
        + "\r\n",
        encoding="utf-8",
    )
    return vbs_path


def install_startup() -> str:
    """Create a Startup folder entry that launches Razor silently in tray mode."""
    root = project_root()
    vbs_path = _write_launcher_scripts(root)

    startup_vbs = startup_folder() / f"{config.STARTUP_FOLDER_NAME}.vbs"
    startup_vbs.write_text(
        f'CreateObject("WScript.Shell").Run """{vbs_path}""", 0, False\r\n',
        encoding="utf-8",
    )
    return f"Installed silent startup launcher at {startup_vbs}"


def uninstall_startup() -> str:
    removed: list[str] = []
    for name in (f"{config.STARTUP_FOLDER_NAME}.vbs", f"{config.STARTUP_FOLDER_NAME}.bat"):
        path = startup_folder() / name
        if path.exists():
            path.unlink()
            removed.append(str(path))
    if removed:
        return "Removed startup launcher(s):\n  " + "\n  ".join(removed)
    return "Startup launcher was not installed."


def open_startup_folder() -> None:
    folder = startup_folder()
    if sys.platform == "win32":
        os.startfile(folder)  # noqa: S606
    else:
        subprocess.Popen(["xdg-open", str(folder)])
