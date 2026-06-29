"""Main assistant orchestrator."""

from __future__ import annotations

import json
import sys
import time

import config
from core.brain import Brain
from core.command_router import CommandRouter
from system.executor import Executor
from utils.action_logger import ActionLogger
from utils.logger import get_logger
from utils.personality import format_spoken_response, format_wake_response
from utils.safety import SafetyGuard
from voice.audio_queue import BackgroundListener
from voice.listener import Listener
from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech, TTSError
from voice.wake_word import WakeWord

logger = get_logger(__name__)


class Assistant:
    """Coordinates wake word, voice, AI reasoning, TTS, and safe OS control."""

    def __init__(
        self,
        *,
        use_ai: bool = True,
        use_tts: bool = True,
        stt_engine: str | None = None,
    ) -> None:
        self.use_ai = use_ai and config.AI_ENABLED
        self.use_tts = use_tts and config.TTS_ENABLED
        self.stt_engine = stt_engine or config.STT_ENGINE

        self.router = CommandRouter()
        self.brain = Brain(self.router.intent_engine)
        self.executor = self.router.executor
        self.safety = SafetyGuard()
        self.actions = ActionLogger()
        self.wake = WakeWord()
        self._tts: TextToSpeech | None = None

    def run(self) -> None:
        """Run the full background assistant loop."""
        self._log_startup()
        self._print_banner()

        try:
            while True:
                logger.info("Idle — listening for wake phrase '%s'", config.WAKE_PHRASE)
                print(f"[idle] Listening for '{config.WAKE_PHRASE}'...")

                trailing_command = self._wait_for_wake_word()
                self._speak(config.WAKE_RESPONSE, personality=False)

                command = trailing_command or self._listen_for_command()
                if not command:
                    message = "(no command heard)"
                    print(message)
                    self._speak("I didn't catch that mate.")
                    self.actions.log(event="no_command", source="voice", result=message)
                    continue

                print(f">> {command}")
                result = self.handle_input(command, source="voice")
                if result == "__EXIT__":
                    self._speak("Catch ya later mate.", personality=False)
                    break

                if result:
                    print(result)
                    self._speak(result)
                print()
        except KeyboardInterrupt:
            print("\nGoodbye.")
            self._speak("Catch ya later mate.", personality=False)
        finally:
            self.wake.stop()
            self.actions.log(event="shutdown", source="assistant", result="stopped")

    def handle_input(self, text: str, *, source: str = "cli") -> str:
        """Process a command with safety checks, AI reasoning, and action logging."""
        cleaned = text.strip()
        if not cleaned:
            return "Enter a command."

        self.actions.log(event="input_received", source=source, input_text=cleaned)

        lowered = cleaned.lower()
        if lowered in {"cancel", "abort", "never mind", "nevermind"}:
            result = self.safety.cancel_pending()
            self.actions.log(event="cancelled", source=source, input_text=cleaned, result=result)
            return result

        if self.safety.has_pending_confirmation:
            confirmed = self.safety.try_confirm(cleaned)
            if confirmed:
                result = self._execute_intent(confirmed, source=source, input_text=cleaned)
                return result
            return self.safety.cancel_pending() if lowered == "no" else (
                "Say 'yes' to confirm or 'cancel' to abort."
            )

        if self.use_ai:
            intent = self.brain.reason(cleaned)
            print(f"Intent: {json.dumps(intent)}")
            allowed, prompt = self.safety.check_intent(intent)
            if not allowed and prompt:
                self.actions.log(
                    event="confirmation_required",
                    source=source,
                    input_text=cleaned,
                    intent=intent,
                    result=prompt,
                )
                return prompt
            return self._execute_intent(intent, source=source, input_text=cleaned)

        result = self.executor.execute(cleaned)
        self.actions.log(event="executed", source=source, input_text=cleaned, result=result)
        return result

    def _execute_intent(self, intent: dict, *, source: str, input_text: str) -> str:
        result = self.router.route(intent)
        self.actions.log(
            event="executed",
            source=source,
            input_text=input_text,
            intent=intent,
            result=result,
        )
        return result

    def _wait_for_wake_word(self) -> str | None:
        self.actions.log(event="wake_listen_start", source="wake_word")
        trailing = self.wake.wait_for_activation()
        self.actions.log(
            event="wake_word_detected",
            source="wake_word",
            result=trailing or config.WAKE_RESPONSE,
        )
        print(f"Razor: {config.WAKE_RESPONSE}")
        return trailing

    def _listen_for_command(self) -> str | None:
        import numpy as np

        stt = SpeechToText(engine=self.stt_engine)
        stt.reset()
        background = BackgroundListener()

        result: dict[str, str | None] = {"text": None}
        partial_line = ""
        listening_indicator = False

        def on_audio(chunk: bytes) -> None:
            nonlocal partial_line, listening_indicator
            if result["text"] is not None:
                return

            final_text, partial_text = stt.process_chunk(chunk)

            if stt.is_streaming and partial_text:
                partial_line = partial_text
                print(f"\r  ... {partial_text}   ", end="", flush=True)

            if not stt.is_streaming and not listening_indicator:
                samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
                rms = float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0
                if rms >= config.SPEECH_ENERGY_THRESHOLD:
                    listening_indicator = True
                    print("\r  [listening...]   ", end="", flush=True)

            if stt.consume_utterance_complete() and listening_indicator and not final_text:
                print("\r" + " " * 24 + "\r", end="", flush=True)
                listening_indicator = False

            if final_text:
                if partial_line:
                    print("\r" + " " * (len(partial_line) + 8) + "\r", end="")
                elif listening_indicator:
                    print("\r" + " " * 24 + "\r", end="")
                result["text"] = final_text
                stt.reset()

        background.start(on_audio)
        try:
            while result["text"] is None:
                time.sleep(0.05)
        finally:
            remaining = stt.flush()
            background.stop()
            if result["text"] is None and remaining:
                result["text"] = remaining

        return result["text"]

    def _speak(self, text: str, *, personality: bool = True) -> None:
        if not self.use_tts:
            return

        tts = self._get_tts()
        if not tts:
            return

        spoken = format_spoken_response(text) if personality else format_wake_response(text)
        try:
            tts.speak(spoken)
        except TTSError as exc:
            logger.warning("TTS failed: %s", exc)

    def _get_tts(self) -> TextToSpeech | None:
        if self._tts is None:
            tts = TextToSpeech()
            if not tts.is_configured() and config.TTS_PROVIDER != "local":
                logger.warning("TTS not fully configured; local fallback may be used.")
            self._tts = tts
        return self._tts

    def _log_startup(self) -> None:
        logger.info("Starting %s v%s", config.APP_NAME, config.APP_VERSION)
        self.actions.log(
            event="startup",
            source="assistant",
            meta={
                "ai": self.use_ai,
                "tts": self.use_tts,
                "stt": self.stt_engine,
                "safe_mode": config.SAFE_MODE,
            },
        )

    def _print_banner(self) -> None:
        print(f"{config.APP_NAME} v{config.APP_VERSION} — Assistant mode")
        print(f"Say '{config.WAKE_PHRASE.title()}' to activate.")
        if self.use_ai:
            print("AI reasoning enabled via Ollama.")
        if self.use_tts:
            print("Voice output enabled (ElevenLabs with local fallback).")
        if config.SAFE_MODE:
            print("Safe mode enabled for destructive actions.")
        print("Press Ctrl+C to stop.\n")
