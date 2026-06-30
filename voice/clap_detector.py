"""Double-clap activation detector."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

import numpy as np

import config
from utils.logger import get_logger

logger = get_logger(__name__)


class ClapDetector:
    """Detect two sharp claps within a short window via RMS energy spikes."""

    def __init__(self, on_double_clap: Callable[[], None]) -> None:
        self.on_double_clap = on_double_clap
        self._enabled = config.CLAP_ENABLED
        self._threshold = config.CLAP_THRESHOLD
        self._min_gap = config.CLAP_MIN_GAP_MS / 1000.0
        self._max_gap = config.CLAP_MAX_GAP_MS / 1000.0
        self._cooldown = config.CLAP_COOLDOWN_MS / 1000.0
        self._clap_times: list[float] = []
        self._last_trigger = 0.0
        self._armed = True

    def process_chunk(self, chunk: bytes) -> None:
        if not self._enabled or not self._armed:
            return

        now = time.monotonic()
        if now - self._last_trigger < self._cooldown:
            return

        samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
        if samples.size == 0:
            return

        rms = float(np.sqrt(np.mean(samples * samples)))
        peak = float(np.max(np.abs(samples)))

        if rms < self._threshold and peak < self._threshold * 1.5:
            return

        if self._clap_times and now - self._clap_times[-1] < self._min_gap:
            return

        self._clap_times.append(now)
        self._clap_times = [t for t in self._clap_times if now - t <= self._max_gap * 2]

        if len(self._clap_times) >= 2:
            gap = self._clap_times[-1] - self._clap_times[-2]
            if self._min_gap <= gap <= self._max_gap:
                self._clap_times.clear()
                self._last_trigger = now
                logger.info("Double clap detected")
                threading.Thread(
                    target=self._fire_callback,
                    daemon=True,
                    name="razor-clap",
                ).start()

    def _fire_callback(self) -> None:
        try:
            self.on_double_clap()
        except Exception as exc:
            logger.warning("Clap callback failed: %s", exc)

    def set_armed(self, armed: bool) -> None:
        self._armed = armed
        if not armed:
            self._clap_times.clear()
