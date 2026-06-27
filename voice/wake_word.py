"""Wake word detection."""

from __future__ import annotations

import re
import threading
import time
from typing import Any

import config
from utils.logger import get_logger
from voice.listener import Listener
from voice.speech_to_text import VoskSpeechToText

logger = get_logger(__name__)


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

    def wait_for_activation(self) -> str | None:
        """
        Block until the wake phrase is spoken.

        Returns:
            Trailing command text if the user continued speaking after the wake phrase
            in the same utterance, otherwise None.
        """
        self._triggered = False
        self._follow_up_command = None
        self._running = True
        self._stt.reset()

        self._listener.listen_continuous(self._on_audio)
        logger.info("Waiting for wake phrase: '%s'", self.phrase)

        try:
            while self._running and not self._triggered:
                time.sleep(0.05)
        finally:
            self._listener.stop()
            self._stt.reset()

        return self._follow_up_command

    def stop(self) -> None:
        """Stop the background wake word loop."""
        self._running = False
        self._listener.stop()

    def _on_audio(self, chunk: bytes) -> None:
        if not self._running or self._triggered:
            return

        final_text, partial_text = self._stt.process_chunk(chunk)

        for text in (partial_text, final_text):
            if not text:
                continue
            if self._contains_wake_phrase(text):
                command = self._extract_trailing_command(text)
                with self._lock:
                    if not self._triggered:
                        self._triggered = True
                        self._follow_up_command = command
                        self._running = False
                        logger.info("Wake phrase detected")
                        if self.on_trigger:
                            self.on_trigger()
                return

        if final_text:
            self._stt.reset()

    def _contains_wake_phrase(self, text: str) -> bool:
        normalized = self._normalize(text)
        if not normalized:
            return False

        if self.phrase in normalized:
            return True

        words = normalized.split()
        if len(words) < 2:
            return False

        wake_words = self.phrase.split()
        wake_len = len(wake_words)

        for index in range(len(words) - wake_len + 1):
            window = words[index : index + wake_len]
            if self._words_match(window, wake_words):
                return True

        return False

    def _extract_trailing_command(self, text: str) -> str | None:
        normalized = self._normalize(text)
        wake_words = self.phrase.split()
        words = normalized.split()

        for index in range(len(words) - len(wake_words) + 1):
            window = words[index : index + len(wake_words)]
            if self._words_match(window, wake_words):
                remainder = " ".join(words[index + len(wake_words) :]).strip()
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
            "hey": {"hey", "hay", "a"},
            "razor": {"razor", "razer", "razr", "razor's"},
        }

        for heard_word, expected_word in zip(heard, expected):
            allowed = aliases.get(expected_word, {expected_word})
            allowed.add(expected_word)
            if heard_word not in allowed:
                return False

        return True
