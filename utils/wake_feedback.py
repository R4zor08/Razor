"""Optional wake beep for instant audio feedback."""

from __future__ import annotations

import sys
import threading

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def play_wake_beep() -> None:
    """Play a short beep without blocking the activation path."""
    if not config.WAKE_BEEP:
        return

    def _beep() -> None:
        try:
            if sys.platform == "win32":
                import winsound

                winsound.Beep(880, 80)
            else:
                print("\a", end="", flush=True)
        except Exception as exc:
            logger.debug("Wake beep failed: %s", exc)

    threading.Thread(target=_beep, daemon=True, name="razor-beep").start()
