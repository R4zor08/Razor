"""Preload models on startup for faster first response."""

from __future__ import annotations

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def warm_models() -> None:
    if not config.WARM_MODELS_ON_STARTUP:
        return

    if config.STT_ENGINE == "vosk":
        try:
            from voice.speech_to_text import preload_vosk

            preload_vosk()
        except Exception as exc:
            logger.warning("Vosk preload failed: %s", exc)

    try:
        from ai.ollama_client import get_ollama_client, OllamaError

        client = get_ollama_client()
        if not client.is_available():
            logger.warning("Ollama not available for warmup.")
            return
        model = config.OLLAMA_INTENT_MODEL or config.OLLAMA_MODEL
        client.generate("Respond with exactly: ok", json_mode=False, model=model)
        logger.info("Models warmed (Ollama %s + STT).", model)
    except OllamaError as exc:
        logger.warning("Ollama warmup failed: %s", exc)
    except Exception as exc:
        logger.warning("Warmup error: %s", exc)
