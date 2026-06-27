"""Audio capture and streaming."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

import config
from utils.logger import get_logger

logger = get_logger(__name__)


class Listener:
    """Captures microphone input in continuous chunks."""

    def __init__(
        self,
        sample_rate: int | None = None,
        block_duration_ms: int | None = None,
        device: int | None = None,
    ) -> None:
        self.sample_rate = sample_rate or config.SAMPLE_RATE
        self.block_duration_ms = block_duration_ms or config.VOICE_BLOCK_MS
        self.device = device if device is not None else config.MIC_DEVICE
        self.blocksize = int(self.sample_rate * self.block_duration_ms / 1000)
        self._stream: Any = None

    def listen_continuous(self, callback: Callable[[bytes], None]) -> None:
        """Start streaming microphone audio to callback as 16-bit PCM bytes."""
        import sounddevice as sd  # pyright: ignore[reportMissingImports]

        def audio_callback(indata: np.ndarray, _frames: int, _time: Any, status: Any) -> None:
            if status:
                logger.warning("Audio stream status: %s", status)
            pcm = (indata[:, 0] * 32767).astype(np.int16).tobytes()
            callback(pcm)

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.blocksize,
            device=self.device,
            callback=audio_callback,
        )
        self._stream.start()
        logger.info(
            "Listening on microphone (sample_rate=%s, block=%sms)",
            self.sample_rate,
            self.block_duration_ms,
        )

    def stop(self) -> None:
        """Stop the active microphone stream."""
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None
        logger.info("Microphone stream stopped.")

    @staticmethod
    def list_devices() -> str:
        """Return a formatted list of available input devices."""
        import sounddevice as sd  # pyright: ignore[reportMissingImports]

        lines = ["Available audio input devices:"]
        devices = sd.query_devices()
        for index, device in enumerate(devices):
            if device["max_input_channels"] > 0:
                lines.append(f"  [{index}] {device['name']}")
        return "\n".join(lines)
