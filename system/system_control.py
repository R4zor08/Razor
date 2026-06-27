"""OS-level system controls."""

import platform
import subprocess


class SystemControl:
    """Manages volume, power, and system settings."""

    def shutdown(self) -> str:
        """Shut down the computer."""
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["shutdown", "/s", "/t", "5"])
            return "Shutting down in 5 seconds."
        if system == "Darwin":
            subprocess.Popen(["osascript", "-e", 'tell app "System Events" to shut down'])
            return "Shutting down."
        subprocess.Popen(["shutdown", "-h", "now"])
        return "Shutting down."

    def restart(self) -> str:
        """Restart the computer."""
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["shutdown", "/r", "/t", "5"])
            return "Restarting in 5 seconds."
        if system == "Darwin":
            subprocess.Popen(["osascript", "-e", 'tell app "System Events" to restart'])
            return "Restarting."
        subprocess.Popen(["shutdown", "-r", "now"])
        return "Restarting."
