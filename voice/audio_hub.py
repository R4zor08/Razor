"""Fan-out microphone stream to multiple processors."""

from __future__ import annotations

import threading
from collections.abc import Callable

from utils.logger import get_logger
from voice.audio_queue import BackgroundListener

logger = get_logger(__name__)


class AudioHub:
    """Single microphone capture — route to idle (wake/clap) or command STT without restart."""

    def __init__(self) -> None:
        self._idle_subscribers: list[Callable[[bytes], None]] = []
        self._command_processor: Callable[[bytes], None] | None = None
        self._lock = threading.Lock()
        self._background: BackgroundListener | None = None

    def subscribe(self, processor: Callable[[bytes], None]) -> None:
        with self._lock:
            if processor not in self._idle_subscribers:
                self._idle_subscribers.append(processor)

    def unsubscribe(self, processor: Callable[[bytes], None]) -> None:
        with self._lock:
            if processor in self._idle_subscribers:
                self._idle_subscribers.remove(processor)

    def enter_command_mode(self, processor: Callable[[bytes], None]) -> None:
        """Route mic audio to command STT only; wake/clap paused."""
        with self._lock:
            self._command_processor = processor
        logger.info("AudioHub: command mode (mic stream stays open)")

    def enter_idle_mode(self) -> None:
        """Route mic audio to wake word + clap subscribers."""
        with self._lock:
            self._command_processor = None
        logger.info("AudioHub: idle mode (wake + clap)")

    @property
    def mode(self) -> str:
        with self._lock:
            return "command" if self._command_processor else "idle"

    def start(self) -> None:
        if self._background is not None:
            return

        def dispatch(chunk: bytes) -> None:
            with self._lock:
                command = self._command_processor
                idle = list(self._idle_subscribers) if command is None else []

            if command is not None:
                try:
                    command(chunk)
                except Exception:
                    pass
                return

            for processor in idle:
                try:
                    processor(chunk)
                except Exception:
                    pass

        self._background = BackgroundListener()
        self._background.start(dispatch)
        logger.info("AudioHub: microphone stream started")

    def stop(self) -> None:
        if self._background is not None:
            self._background.stop()
            self._background = None
            logger.info("AudioHub: microphone stream stopped")

    @property
    def is_running(self) -> bool:
        return self._background is not None
