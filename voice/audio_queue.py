"""Queued microphone processing to avoid audio callback overflow."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable

from voice.listener import Listener


class BackgroundListener:
    """Capture audio on a callback thread and process chunks on a worker thread."""

    def __init__(self, listener: Listener | None = None) -> None:
        self.listener = listener or Listener()
        self._queue: queue.Queue[bytes] = queue.Queue(maxsize=50)
        self._worker: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self, processor: Callable[[bytes], None]) -> None:
        """Start background capture and processing."""
        self._stop.clear()

        def worker() -> None:
            while not self._stop.is_set():
                try:
                    chunk = self._queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                processor(chunk)
                self._queue.task_done()

        self._worker = threading.Thread(target=worker, daemon=True, name="razor-audio")
        self._worker.start()

        def enqueue(chunk: bytes) -> None:
            try:
                self._queue.put_nowait(chunk)
            except queue.Full:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
                self._queue.put_nowait(chunk)

        self.listener.listen_continuous(enqueue)

    def stop(self) -> None:
        """Stop worker and microphone stream."""
        self._stop.set()
        self.listener.stop()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=1.0)
