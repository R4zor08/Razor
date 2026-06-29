"""OS-level system controls."""

from __future__ import annotations

import platform
import re
import subprocess


class SystemControl:
    """Manages volume, power, brightness, and system settings."""

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

    def set_volume(self, value: str) -> str:
        """
        Adjust system volume.

        value: up, down, mute, unmute, or a percentage 0-100
        """
        normalized = value.strip().lower()
        if normalized in {"up", "louder", "increase", "raise"}:
            return self._change_volume(10)
        if normalized in {"down", "quieter", "decrease", "lower"}:
            return self._change_volume(-10)
        if normalized in {"mute", "silence"}:
            return self._set_mute(True)
        if normalized in {"unmute", "sound on"}:
            return self._set_mute(False)

        match = re.search(r"(\d+)", normalized)
        if match:
            level = max(0, min(100, int(match.group(1))))
            return self._set_volume_percent(level)

        return "Volume value must be up, down, mute, unmute, or a percentage 0-100."

    def set_brightness(self, value: str) -> str:
        """
        Adjust display brightness when supported.

        value: up, down, or a percentage 0-100
        """
        normalized = value.strip().lower()
        if normalized in {"up", "brighter", "increase"}:
            return self._change_brightness(10)
        if normalized in {"down", "dimmer", "decrease"}:
            return self._change_brightness(-10)

        match = re.search(r"(\d+)", normalized)
        if match:
            level = max(0, min(100, int(match.group(1))))
            return self._set_brightness_percent(level)

        return "Brightness value must be up, down, or a percentage 0-100."

    def _change_volume(self, delta: int) -> str:
        if platform.system() == "Windows":
            return self._windows_volume_delta(delta)
        if platform.system() == "Darwin":
            direction = 1 if delta > 0 else 0
            subprocess.run(["osascript", "-e", f"set volume output volume (output volume of (get volume settings) + {delta})"])
            return f"Volume adjusted {'up' if delta > 0 else 'down'}."
        subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{delta}%+"])
        return f"Volume adjusted {'up' if delta > 0 else 'down'}."

    def _set_volume_percent(self, level: int) -> str:
        if platform.system() == "Windows":
            return self._windows_volume_percent(level)
        if platform.system() == "Darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {level}"])
            return f"Volume set to {level}%."
        subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level}%"])
        return f"Volume set to {level}%."

    def _set_mute(self, muted: bool) -> str:
        if platform.system() == "Windows":
            volume = self._get_windows_volume_interface()
            if volume is not None:
                volume.SetMute(1 if muted else 0, None)
                return "Volume muted." if muted else "Volume unmuted."
            key = 0xAD
            script = f"$wshell = New-Object -ComObject WScript.Shell; $wshell.SendKeys([char]{key})"
            subprocess.run(["powershell", "-NoProfile", "-Command", script], check=False)
            return "Volume mute toggled."
        if platform.system() == "Darwin":
            subprocess.run(["osascript", "-e", f"set volume output muted {str(muted).lower()}"])
            return "Volume muted." if muted else "Volume unmuted."
        flag = "mute" if muted else "unmute"
        subprocess.run(["amixer", "-D", "pulse", "sset", "Master", flag])
        return "Volume muted." if muted else "Volume unmuted."

    def _windows_volume_delta(self, delta: int) -> str:
        volume = self._get_windows_volume_interface()
        if volume is not None:
            current = round(volume.GetMasterVolumeLevelScalar() * 100)
            new_level = max(0, min(100, current + delta))
            volume.SetMasterVolumeLevelScalar(new_level / 100, None)
            return f"Volume set to {new_level}%."
        return self._windows_volume_powershell_delta(delta)

    def _windows_volume_percent(self, level: int) -> str:
        volume = self._get_windows_volume_interface()
        if volume is not None:
            volume.SetMasterVolumeLevelScalar(level / 100, None)
            return f"Volume set to {level}%."
        return self._windows_volume_powershell_percent(level)

    def _windows_volume_powershell_delta(self, delta: int) -> str:
        key = 0xAF if delta > 0 else 0xAE
        repeats = abs(delta) // 2 or 1
        script = (
            "$wshell = New-Object -ComObject WScript.Shell; "
            f"1..{repeats} | ForEach-Object {{ $wshell.SendKeys([char]{key}) }}"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", script], check=False)
        direction = "up" if delta > 0 else "down"
        return f"Volume turned {direction}."

    def _windows_volume_powershell_percent(self, level: int) -> str:
        return (
            f"Precise volume levels need pycaw on this system. "
            f"Use volume up/down or install audio drivers. Requested: {level}%."
        )

    @staticmethod
    def _get_windows_volume_interface():
        if platform.system() != "Windows":
            return None
        try:
            from comtypes import CLSCTX_ALL
            from ctypes import cast, POINTER
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return cast(interface, POINTER(IAudioEndpointVolume))
        except Exception:
            return None

    def _change_brightness(self, delta: int) -> str:
        current = self._get_brightness_percent()
        if current is None:
            return "Brightness control is not available on this display."
        return self._set_brightness_percent(max(0, min(100, current + delta)))

    def _set_brightness_percent(self, level: int) -> str:
        if platform.system() == "Windows":
            script = (
                "$methods = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods; "
                f"foreach ($m in $methods) {{ $m.WmiSetBrightness(1, {level}) }}"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0 or "Exception" in (result.stderr or ""):
                return "Brightness control is not available on this display."
            return f"Brightness set to {level}%."
        if platform.system() == "Darwin":
            return "Brightness control is not supported on macOS via Razor yet."
        subprocess.run(["brightnessctl", "set", f"{level}%"])
        return f"Brightness set to {level}%."

    def _get_brightness_percent(self) -> int | None:
        if platform.system() == "Windows":
            script = (
                "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness | "
                "Select-Object -First 1 -ExpandProperty CurrentBrightness)"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0 or not result.stdout.strip().isdigit():
                return None
            return int(result.stdout.strip())
        if platform.system() == "Darwin":
            return None
        result = subprocess.run(["brightnessctl", "get"], capture_output=True, text=True)
        if result.returncode != 0 or not result.stdout.strip().isdigit():
            return None
        return int(result.stdout.strip())
