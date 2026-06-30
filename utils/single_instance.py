"""Ensure only one Razor instance runs at a time."""

from __future__ import annotations

import sys

from utils.logger import get_logger

logger = get_logger(__name__)

_MUTEX_NAME = "Global\\RazorAI_SingleInstance"
_mutex_handle = None


def acquire_single_instance() -> bool:
    """
    Return True if this is the only instance.

    On Windows uses a named mutex; elsewhere always allows start.
    """
    global _mutex_handle

    if sys.platform != "win32":
        return True

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183
        handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
        _mutex_handle = handle
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            logger.info("Another Razor instance is already running; exiting.")
            return False
        return True
    except Exception as exc:
        logger.warning("Single-instance lock unavailable: %s", exc)
        return True


def release_single_instance() -> None:
    global _mutex_handle
    if _mutex_handle is not None and sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        except Exception:
            pass
        _mutex_handle = None
