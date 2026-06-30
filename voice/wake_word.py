"""Wake word detection."""

from __future__ import annotations

import re
import time
import threading
from typing import Any

import config
from utils.logger import get_logger
from voice.audio_queue import BackgroundListener
from voice.listener import Listener
from voice.speech_to_text import VoskSpeechToText

logger = get_logger(__name__)

_HEY_ALIASES = frozenset({"hey", "hay", "a", "he", "hi", "high", "aye"})
_RAZOR_ALIASES = frozenset(
    {"razor", "razer", "razr", "razors", "razor's", "razers", "racer", "razor.", "razor,"}
)


class WakeWord:
    """Listens continuously for the activation phrase using lightweight Vosk streaming."""

    def __init__(
        self,
        phrase: str | None = None,
        on_trigger: Any | None = None,
    ) -> None:
        self.phrase = (phrase or config.WAKE_PHRASE).lower()
        self.on_trigger = on_trigger
        self._listener = Listener()
        self._stt = VoskSpeechToText()
        self._running = False
        self._triggered = False
        self._lock = threading.Lock()
        self._follow_up_command: str | None = None
        self._background: BackgroundListener | None = None
        self._hub_mode = False
        self._trigger_event = threading.Event()
        self._text_buffer = ""
        self._last_hey_at = 0.0

    def attach_hub(self, hub: Any) -> None:
        """Use a shared AudioHub instead of owning the microphone."""
        hub.subscribe(self.process_chunk)
        self._hub_mode = True

    def wait_for_activation(self) -> str | None:
        """Block until the wake phrase is spoken."""
        self._reset_state()
        self._running = True
        logger.info("Waiting for wake phrase: '%s'", self.phrase)

        if self._hub_mode:
            try:
                while self._running and not self._triggered:
                    self._trigger_event.wait(0.05)
            finally:
                self._stt.reset()
            return self._follow_up_command

        self._background = BackgroundListener(self._listener)
        self._background.start(self.process_chunk)
        try:
            while self._running and not self._triggered:
                time.sleep(0.05)
        finally:
            if self._background:
                self._background.stop()
                self._background = None
            self._stt.reset()

        return self._follow_up_command

    def stop(self) -> None:
        """Stop the background wake word loop."""
        self._running = False
        self._trigger_event.set()
        if self._background:
            self._background.stop()
            self._background = None

    def reset_for_next(self) -> None:
        """Prepare to listen for the wake phrase again."""
        self._reset_state()
        self._running = True

    def process_chunk(self, chunk: bytes) -> None:
        if not self._running or self._triggered:
            return

        final_text, partial_text = self._stt.process_chunk(chunk)

        if config.WAKE_DEBUG and partial_text:
            norm = self._normalize(partial_text)
            if any(alias in norm.split() for alias in _RAZOR_ALIASES) or "raz" in norm:
                logger.debug("Wake partial heard: %s", partial_text)

        candidates: list[str] = []
        if partial_text:
            candidates.append(partial_text)
        if final_text:
            self._text_buffer = f"{self._text_buffer} {final_text}".strip()
            if len(self._text_buffer) > 240:
                self._text_buffer = self._text_buffer[-240:]
            candidates.extend([final_text, self._text_buffer])

        combined = " ".join(filter(None, [partial_text, final_text])).strip()
        if combined:
            candidates.append(combined)

        for text in candidates:
            if text and self._try_trigger(text):
                return

        if final_text:
            norm = self._normalize(final_text)
            if any(w in _HEY_ALIASES for w in norm.split()):
                self._last_hey_at = time.monotonic()
            if not self._triggered and len(self._text_buffer) > 120:
                self._stt.reset()
                self._text_buffer = final_text

    def _try_trigger(self, text: str) -> bool:
        if not self._contains_wake_phrase(text):
            return False

        command = self._extract_trailing_command(text)
        with self._lock:
            if self._triggered:
                return True
            self._triggered = True
            self._follow_up_command = command
            self._running = False
            self._trigger_event.set()
            logger.info("Wake phrase detected in: %s", text[:80])

            if self.on_trigger:
                try:
                    self.on_trigger()
                except Exception as exc:
                    logger.warning("Wake on_trigger callback failed: %s", exc)
        return True

    def _reset_state(self) -> None:
        self._triggered = False
        self._follow_up_command = None
        self._text_buffer = ""
        self._last_hey_at = 0.0
        self._trigger_event.clear()
        self._stt.reset()

    def _contains_wake_phrase(self, text: str) -> bool:
        normalized = self._normalize(text)
        if not normalized:
            return False

        compact = normalized.replace(" ", "")
        if self.phrase.replace(" ", "") in compact:
            return True

        if self.phrase in normalized:
            return True

        words = normalized.split()
        if not words:
            return False

        hey_indices = [i for i, w in enumerate(words) if w in _HEY_ALIASES]
        razor_indices = [i for i, w in enumerate(words) if self._is_razor_word(w)]

        for hi in hey_indices:
            for ri in razor_indices:
                if 0 <= ri - hi <= 4:
                    return True

        if razor_indices and self._last_hey_at and time.monotonic() - self._last_hey_at < 2.0:
            return True

        if len(words) >= 2:
            wake_words = self.phrase.split()
            wake_len = len(wake_words)
            for index in range(len(words) - wake_len + 1):
                window = words[index : index + wake_len]
                if self._words_match(window, wake_words):
                    return True

        return False

    def _is_razor_word(self, word: str) -> bool:
        if word in _RAZOR_ALIASES:
            return True
        return word.startswith("raz") and len(word) <= 8

    def _extract_trailing_command(self, text: str) -> str | None:
        normalized = self._normalize(text)
        words = normalized.split()
        wake_words = self.phrase.split()

        for index in range(len(words) - len(wake_words) + 1):
            window = words[index : index + len(wake_words)]
            if self._words_match(window, wake_words):
                remainder = " ".join(words[index + len(wake_words) :]).strip()
                return remainder or None

        hey_indices = [i for i, w in enumerate(words) if w in _HEY_ALIASES]
        razor_indices = [i for i, w in enumerate(words) if self._is_razor_word(w)]
        for hi in hey_indices:
            for ri in razor_indices:
                if 0 < ri - hi <= 4:
                    remainder = " ".join(words[ri + 1 :]).strip()
                    return remainder or None

        return None

    @staticmethod
    def _normalize(text: str) -> str:
        cleaned = re.sub(r"[^a-z0-9\s']", " ", text.lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    def _words_match(self, heard: list[str], expected: list[str]) -> bool:
        if len(heard) != len(expected):
            return False

        aliases = {
            "hey": _HEY_ALIASES,
            "razor": _RAZOR_ALIASES,
        }

        for heard_word, expected_word in zip(heard, expected):
            allowed = set(aliases.get(expected_word, {expected_word}))
            allowed.add(expected_word)
            if heard_word not in allowed and not (
                expected_word == "razor" and heard_word.startswith("raz")
            ):
                return False

        return True
