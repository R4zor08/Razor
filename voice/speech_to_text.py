"""Speech-to-text conversion."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np

import config
from utils.logger import get_logger

logger = get_logger(__name__)

VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"


class STTBackend(ABC):
    """Base class for speech-to-text backends."""

    @property
    @abstractmethod
    def is_streaming(self) -> bool:
        """Whether the backend emits partial results while speaking."""

    @abstractmethod
    def reset(self) -> None:
        """Reset state for a new utterance."""

    @abstractmethod
    def process_chunk(self, audio_bytes: bytes) -> tuple[str | None, str | None]:
        """
        Process an audio chunk.

        Returns:
            (final_text, partial_text)
        """

    @abstractmethod
    def flush(self) -> str | None:
        """Return any remaining recognized text."""


class VoskSpeechToText(STTBackend):
    """Streaming offline recognition via Vosk."""

    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path or config.VOSK_MODEL_PATH)
        self._model: Any = None
        self._recognizer: Any = None
        self._last_confidence: float | None = None

    @property
    def is_streaming(self) -> bool:
        return True

    @property
    def model(self) -> Any:
        if self._model is None:
            self._load_model()
        return self._model

    def reset(self) -> None:
        import vosk

        self._recognizer = vosk.KaldiRecognizer(self.model, config.SAMPLE_RATE)
        self._recognizer.SetWords(True)
        self._last_confidence = None

    @property
    def last_confidence(self) -> float | None:
        return self._last_confidence

    def process_chunk(self, audio_bytes: bytes) -> tuple[str | None, str | None]:
        if self._recognizer is None:
            self.reset()

        if self._recognizer.AcceptWaveform(audio_bytes):
            result = json.loads(self._recognizer.Result())
            text = result.get("text", "").strip()
            self._last_confidence = self._confidence_from_result(result)
            return (text or None, None)

        partial = json.loads(self._recognizer.PartialResult())
        partial_text = partial.get("partial", "").strip()
        return (None, partial_text or None)

    def flush(self) -> str | None:
        if self._recognizer is None:
            return None
        result = json.loads(self._recognizer.FinalResult())
        text = result.get("text", "").strip()
        self._last_confidence = self._confidence_from_result(result)
        return text or None

    @staticmethod
    def _confidence_from_result(result: dict[str, Any]) -> float | None:
        words = result.get("result")
        if not isinstance(words, list) or not words:
            return None
        confs = [float(w["conf"]) for w in words if isinstance(w, dict) and "conf" in w]
        if not confs:
            return None
        return sum(confs) / len(confs)

    def _load_model(self) -> None:
        if not self.model_path.is_dir():
            raise FileNotFoundError(
                f"Vosk model not found at '{self.model_path}'.\n"
                "Download the small English model and extract it:\n"
                f"  {VOSK_MODEL_URL}\n"
                f"Extract to: {self.model_path}"
            )

        import vosk

        vosk.SetLogLevel(-1)
        logger.info("Loading Vosk model from %s", self.model_path)
        self._model = vosk.Model(str(self.model_path))


class WhisperSpeechToText(STTBackend):
    """Batch recognition via faster-whisper with silence-based utterance detection."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
    ) -> None:
        self.model_name = model_name or config.WHISPER_MODEL
        self.device = device or config.WHISPER_DEVICE
        self.compute_type = compute_type or config.WHISPER_COMPUTE_TYPE
        self._model: Any = None
        self._buffer = bytearray()
        self._speech_started = False
        self._silence_chunks = 0
        self._speech_chunks = 0
        self._utterance_complete = False

    @property
    def is_streaming(self) -> bool:
        return False

    @property
    def model(self) -> Any:
        if self._model is None:
            self._load_model()
        return self._model

    def reset(self) -> None:
        self._clear_buffer()
        self._utterance_complete = False

    def consume_utterance_complete(self) -> bool:
        """Return True once when an utterance boundary was detected."""
        if self._utterance_complete:
            self._utterance_complete = False
            return True
        return False

    def process_chunk(self, audio_bytes: bytes) -> tuple[str | None, str | None]:
        energy = self._rms_energy(audio_bytes)

        if energy >= config.SPEECH_ENERGY_THRESHOLD:
            self._speech_started = True
            self._silence_chunks = 0
            self._speech_chunks += 1
            self._buffer.extend(audio_bytes)
            return (None, None)

        if self._speech_started:
            self._silence_chunks += 1
            self._buffer.extend(audio_bytes)
            silence_ms = self._silence_chunks * config.VOICE_BLOCK_MS
            if silence_ms >= config.SILENCE_DURATION_MS:
                self._utterance_complete = True
                text = self._transcribe_buffer()
                return (text, None)

        return (None, None)

    def flush(self) -> str | None:
        if not self._speech_started or not self._buffer:
            return None
        return self._transcribe_buffer()

    def _transcribe_buffer(self) -> str | None:
        speech_ms = self._speech_chunks * config.VOICE_BLOCK_MS
        audio_bytes = bytes(self._buffer)
        self._clear_buffer()

        if speech_ms < config.MIN_SPEECH_MS:
            return None

        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if audio.size == 0:
            return None

        logger.debug("Transcribing %.1fs of audio with Whisper", speech_ms / 1000)
        segments, _ = self.model.transcribe(
            audio,
            language="en",
            vad_filter=True,
            beam_size=1,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text or None

    def _clear_buffer(self) -> None:
        self._buffer.clear()
        self._speech_started = False
        self._silence_chunks = 0
        self._speech_chunks = 0

    @staticmethod
    def _rms_energy(audio_bytes: bytes) -> float:
        if not audio_bytes:
            return 0.0
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        if samples.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(samples * samples)))

    def _load_model(self) -> None:
        from faster_whisper import WhisperModel

        logger.info(
            "Loading Whisper model '%s' (device=%s, compute=%s)",
            self.model_name,
            self.device,
            self.compute_type,
        )
        self._model = WhisperModel(
            self.model_name,
            device=self.device,
            compute_type=self.compute_type,
        )


_vosk_singleton: VoskSpeechToText | None = None
_stt_singleton: SpeechToText | None = None


def get_vosk_backend() -> VoskSpeechToText:
    """Shared Vosk instance — model loads once."""
    global _vosk_singleton
    if _vosk_singleton is None:
        _vosk_singleton = VoskSpeechToText()
        _ = _vosk_singleton.model
        logger.info("Vosk model preloaded (shared instance).")
    return _vosk_singleton


def preload_vosk() -> None:
    get_vosk_backend()


def get_speech_to_text(engine: str | None = None) -> SpeechToText:
    """Shared SpeechToText facade for wake + command listening."""
    global _stt_singleton
    engine_name = (engine or config.STT_ENGINE).lower()
    if _stt_singleton is None or _stt_singleton.engine != engine_name:
        _stt_singleton = SpeechToText(engine=engine_name)
        if engine_name == "vosk":
            preload_vosk()
    return _stt_singleton


class SpeechToText:
    """Facade that delegates to the configured STT backend."""

    def __init__(self, engine: str | None = None) -> None:
        engine_name = (engine or config.STT_ENGINE).lower()
        if engine_name == "vosk":
            self._backend: STTBackend = get_vosk_backend()
        elif engine_name == "whisper":
            self._backend = WhisperSpeechToText()
        else:
            raise ValueError(f"Unknown STT engine '{engine_name}'. Use 'whisper' or 'vosk'.")

        self.engine = engine_name

    @property
    def is_streaming(self) -> bool:
        return self._backend.is_streaming

    def reset(self) -> None:
        self._backend.reset()

    def process_chunk(self, audio_bytes: bytes) -> tuple[str | None, str | None]:
        return self._backend.process_chunk(audio_bytes)

    def flush(self) -> str | None:
        return self._backend.flush()

    @property
    def last_confidence(self) -> float | None:
        if hasattr(self._backend, "last_confidence"):
            return self._backend.last_confidence
        return None

    def consume_utterance_complete(self) -> bool:
        """Return True when a non-streaming backend finished an utterance."""
        if hasattr(self._backend, "consume_utterance_complete"):
            return self._backend.consume_utterance_complete()
        return False
