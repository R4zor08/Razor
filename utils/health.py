"""Startup health checks for mic, Vosk, and Ollama."""

from __future__ import annotations

from pathlib import Path

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def check_startup_health() -> dict[str, str]:
    """Return status dict: ok | offline | missing | error."""
    return {
        "mic": _check_mic(),
        "vosk": _check_vosk(),
        "ollama": _check_ollama(),
    }


def log_health_summary() -> dict[str, str]:
    health = check_startup_health()
    logger.info(
        "Health: mic=%s ollama=%s vosk=%s",
        health["mic"],
        health["ollama"],
        health["vosk"],
    )
    return health


def health_tooltip(health: dict[str, str] | None = None) -> str:
    h = health or check_startup_health()
    if h.get("ollama") != "ok":
        return "Razor AI — Ollama offline (reflex commands still work)"
    if h.get("mic") != "ok":
        return "Razor AI — microphone issue"
    if h.get("vosk") != "ok":
        return "Razor AI — Vosk model missing"
    return "Razor AI — online"


def _check_mic() -> str:
    try:
        import sounddevice as sd

        sd.query_devices()
        return "ok"
    except Exception as exc:
        logger.warning("Mic health check failed: %s", exc)
        return "error"


def _check_vosk() -> str:
    path = Path(config.VOSK_MODEL_PATH)
    return "ok" if path.is_dir() else "missing"


def _check_ollama() -> str:
    try:
        from ai.ollama_client import get_ollama_client

        if get_ollama_client().is_available():
            return "ok"
        return "offline"
    except Exception as exc:
        logger.warning("Ollama health check failed: %s", exc)
        return "offline"
