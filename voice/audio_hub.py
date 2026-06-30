"""Fan-out microphone stream to multiple processors."""

from __future__ import annotations

import threading
from collections.abc import Callable

from voice.audio_queue import BackgroundListener


class AudioHub:
    """Single microphone capture shared by wake word, clap detection, etc."""

    def __init__(self) -> None:
        self._subscribers: list[Callable[[bytes], None]] = []
        self._lock = threading.Lock()
        self._background: BackgroundListener | None = None

    def subscribe(self, processor: Callable[[bytes], None]) -> None:
        with self._lock:
            if processor not in self._subscribers:
                self._subscribers.append(processor)

    def unsubscribe(self, processor: Callable[[bytes], None]) -> None:
        with self._lock:
            if processor in self._subscribers:
                self._subscribers.remove(processor)

    def start(self) -> None:
        if self._background is not None:
            return

        def dispatch(chunk: bytes) -> None:
            with self._lock:
                targets = list(self._subscribers)
            for processor in targets:
                try:
                    processor(chunk)
                except Exception:
                    pass

        self._background = BackgroundListener()
        self._background.start(dispatch)

    def stop(self) -> None:
        if self._background is not None:
            self._background.stop()
            self._background = None

    @property
    def is_running(self) -> bool:
        return self._background is not None
