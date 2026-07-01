"""Main assistant orchestrator."""

from __future__ import annotations

import json
import sys
import threading
import time

import config
from core.brain import Brain
from core.command_router import CommandRouter
from system.executor import Executor
from ui.overlay import ActivationOverlay
from utils.action_logger import ActionLogger
from utils.hotkey import GlobalHotkey
from utils.logger import get_logger
from utils.personality import format_spoken_response, format_wake_response
from utils.safety import SafetyGuard
from utils.tray import TrayIcon
from utils.wake_feedback import play_wake_beep
from voice.audio_hub import AudioHub
from voice.audio_queue import BackgroundListener
from voice.clap_detector import ClapDetector
from ai.memory import get_memory
from utils.scheduler import maybe_startup_greeting
from utils.transcript import is_plausible_command
from utils.warmup import warm_models
from voice.speech_to_text import SpeechToText, get_speech_to_text
from voice.text_to_speech import TextToSpeech, TTSError
from voice.wake_word import WakeWord

logger = get_logger(__name__)


class Assistant:
    """Coordinates wake word, voice, AI reasoning, TTS, UI overlay, and safe OS control."""

    def __init__(
        self,
        *,
        use_ai: bool = True,
        use_tts: bool = True,
        stt_engine: str | None = None,
        tray_mode: bool = False,
    ) -> None:
        self.use_ai = use_ai and config.AI_ENABLED
        self.use_tts = use_tts and config.TTS_ENABLED
        self.stt_engine = stt_engine or config.STT_ENGINE
        self.tray_mode = tray_mode

        self.router = CommandRouter()
        self.brain = Brain(self.router.intent_engine)
        self.executor = self.router.executor
        self.safety = SafetyGuard()
        self.actions = ActionLogger()
        self.wake = WakeWord(on_trigger=self._wake_instant_ui)
        self._tts: TextToSpeech | None = None
        self._running = True
        self._activation_lock = threading.Lock()
        self._hotkey: GlobalHotkey | None = None
        self._wake_thread: threading.Thread | None = None
        self._tray: TrayIcon | None = None
        self._ui: ActivationOverlay | None = None
        self._hub: AudioHub | None = None
        self._clap: ClapDetector | None = None
        self._shutting_down = False
        self._ui_wake_shown = False
        self._stt: SpeechToText | None = None
        self._memory = get_memory()

    def _wake_instant_ui(self) -> None:
        """Called from wake-word audio thread the moment 'Hey Razor' is detected."""
        if not config.WAKE_UI_FIRST:
            return
        self._ui_wake_shown = True
        self._ui_show_activated()

    def run(self) -> None:
        """Run the full assistant loop (console or tray background mode)."""
        self._log_startup()
        warm_models()
        self._stt = get_speech_to_text(self.stt_engine)
        self._start_ui()
        self._start_idle_listening()

        greeting = maybe_startup_greeting()
        if greeting and self.use_tts:
            self._speak_async(greeting, personality=True)

        if self.tray_mode and config.TRAY_ENABLED:
            self._run_tray_mode()
            return

        self._print_banner()
        if config.HOTKEY_ENABLED:
            self._start_hotkey()
        try:
            while self._running:
                logger.info("Idle — listening for wake phrase '%s'", config.WAKE_PHRASE)
                print(f"[idle] Listening for '{config.WAKE_PHRASE}'...")
                self.wake.reset_for_next()

                trailing_command = self._wait_for_wake_word()
                if not self._running:
                    break
                self._handle_activation(trailing_command, source="voice")
        except KeyboardInterrupt:
            print("\nGoodbye.")
            self._speak("Catch ya later mate.", personality=False)
        finally:
            self.shutdown()

    def activate_once(self, *, source: str = "hotkey") -> None:
        """Skip wake word and listen for a single command (hotkey / clap / tray)."""
        if self._shutting_down:
            return
        if not self._activation_lock.acquire(blocking=False):
            logger.info("Activation already in progress.")
            return

        try:
            self._on_activate(source=source)
            command = self._listen_for_command()
            self._handle_command(command, source=source)
        finally:
            self._disarm_triggers()
            self.wake.reset_for_next()
            self._ui_wake_shown = False
            self._activation_lock.release()
            if self._ui and config.UI_IDLE_VISIBLE:
                self._ui.show_idle()

    def shutdown(self) -> None:
        """Stop background services cleanly."""
        if self._shutting_down:
            return
        self._shutting_down = True
        self._running = False

        self.wake.stop()
        if self._hub:
            self._hub.stop()
        if self._hotkey:
            self._hotkey.stop()
        if self._clap:
            self._clap.set_armed(False)
        if self._ui:
            self._ui.stop()
        if self._tray:
            self._tray.stop()

        self.actions.log(event="shutdown", source="assistant", result="stopped")
        logger.info("Razor shutdown complete.")

    def handle_input(self, text: str, *, source: str = "cli") -> str:
        """Process a command with safety checks, AI reasoning, and action logging."""
        cleaned = text.strip()
        if not cleaned:
            return "Enter a command."

        self.actions.log(event="input_received", source=source, input_text=cleaned)

        lowered = cleaned.lower()
        if lowered in {"cancel", "abort", "never mind", "nevermind"}:
            result = self.safety.cancel_pending()
            self._ui_set_response(result)
            self.actions.log(event="cancelled", source=source, input_text=cleaned, result=result)
            return result

        if self.safety.has_pending_confirmation:
            confirmed = self.safety.try_confirm(cleaned)
            if confirmed:
                return self._execute_intent(confirmed, source=source, input_text=cleaned)
            result = self.safety.cancel_pending() if lowered == "no" else (
                "Say 'yes' to confirm or 'cancel' to abort."
            )
            self._ui_set_status("confirm")
            self._ui_set_response(result)
            return result

        if self.use_ai:
            if source in {"voice", "hotkey", "clap"} and config.PROCESSING_FEEDBACK:
                print("[processing...]")
                self._ui_set_status("processing")
                if config.PROCESSING_SPEAK:
                    self._speak_async("One sec mate.", personality=False)

            intent = self.brain.reason(cleaned)
            print(f"Intent: {json.dumps(intent, default=str)}")

            if intent.get("action") == "__instant__":
                result = str(intent.get("value", ""))
                self._ui_set_response(result)
                self._memory.add_command(cleaned)
                return result

            if intent.get("action") == "__remember__":
                result = str(intent.get("value", ""))
                self._ui_set_response(result)
                return result

            if intent.get("action") == "__multi__":
                steps = intent.get("value") or []
                results: list[str] = []
                for step in steps:
                    if isinstance(step, dict):
                        results.append(
                            self._execute_intent(step, source=source, input_text=cleaned)
                        )
                result = "\n".join(r for r in results if r)
                return result or "Done."

            if intent.get("action") == "chat":
                result = self.brain.chat(intent.get("value") or cleaned)
                self.actions.log(
                    event="chat",
                    source=source,
                    input_text=cleaned,
                    intent=intent,
                    result=result,
                )
                self._ui_set_response(result)
                return result

            if intent.get("action") == "unknown":
                if config.CHAT_FALLBACK:
                    result = self.brain.chat(cleaned)
                    self.actions.log(
                        event="chat_fallback",
                        source=source,
                        input_text=cleaned,
                        intent=intent,
                        result=result,
                    )
                else:
                    result = "I didn't quite catch that. Try a simpler command?"
                    self.actions.log(
                        event="unknown_intent",
                        source=source,
                        input_text=cleaned,
                        intent=intent,
                        result=result,
                    )
                self._ui_set_response(result)
                return result

            allowed, prompt = self.safety.check_intent(intent)
            if not allowed and prompt:
                self.actions.log(
                    event="confirmation_required",
                    source=source,
                    input_text=cleaned,
                    intent=intent,
                    result=prompt,
                )
                self._ui_set_status("confirm")
                self._ui_set_response(prompt)
                return prompt
            return self._execute_intent(intent, source=source, input_text=cleaned)

        result = self.executor.execute(cleaned)
        self.actions.log(event="executed", source=source, input_text=cleaned, result=result)
        self._ui_set_response(result)
        return result

    def _execute_intent(self, intent: dict, *, source: str, input_text: str) -> str:
        action = intent.get("action")
        if action == "open_app" and intent.get("value"):
            self._memory.set_last_opened_app(str(intent["value"]))
        self._memory.add_command(input_text)

        result = self.router.route(intent)
        self.actions.log(
            event="executed",
            source=source,
            input_text=input_text,
            intent=intent,
            result=result,
        )
        self._ui_set_response(result)
        if config.EXECUTE_BEFORE_SPEAK and action not in {"chat", "help"}:
            self._ui_show_done()
        return result

    def _start_ui(self) -> None:
        if not config.UI_ENABLED:
            return
        self._ui = ActivationOverlay()
        self._ui.start()

    def _start_idle_listening(self) -> None:
        """Shared mic for wake word + clap detection."""
        self._hub = AudioHub()
        self.wake.attach_hub(self._hub)

        if config.CLAP_ENABLED:
            self._clap = ClapDetector(on_double_clap=lambda: self.activate_once(source="clap"))
            self._hub.subscribe(self._clap.process_chunk)

        self._hub.start()
        self.wake.reset_for_next()
        if self._ui and config.UI_IDLE_VISIBLE:
            self._ui.show_idle()
        logger.info(
            "Idle listening started (wake=%s, clap=%s, hub=%s)",
            config.WAKE_PHRASE,
            config.CLAP_ENABLED,
            True,
        )

    def _arm_triggers(self) -> None:
        if self._clap:
            self._clap.set_armed(False)

    def _disarm_triggers(self) -> None:
        if self._clap:
            self._clap.set_armed(True)

    def _on_activate(self, *, source: str) -> None:
        """Instant feedback: UI + beep, then optional wake TTS."""
        self._arm_triggers()
        if not self._ui_wake_shown:
            self._ui_show_activated()
        self._ui_wake_shown = False
        play_wake_beep()

        if config.WAKE_SPEAK and self.use_tts:
            self._speak_async(config.WAKE_RESPONSE, personality=False)

        self._ui_set_status("listening")
        print(f"Razor: {config.WAKE_RESPONSE} ({source})")

    def _run_tray_mode(self) -> None:
        logger.info("Starting tray background mode.")
        self._start_hotkey()
        self._start_wake_thread()

        def on_quit() -> None:
            self.shutdown()
            sys.exit(0)

        self._tray = TrayIcon(on_activate=lambda: self.activate_once(source="tray"), on_quit=on_quit)
        logger.info("Razor ready — tray mode active (wake word + hotkey + UI).")
        self._tray.run()

    def _start_wake_thread(self) -> None:
        def wake_loop() -> None:
            while self._running:
                self.wake.reset_for_next()
                trailing = self.wake.wait_for_activation()
                if not self._running:
                    break
                if not self._activation_lock.acquire(blocking=False):
                    self.wake.reset_for_next()
                    continue
                try:
                    self._on_activate(source="voice")
                    command = trailing or self._listen_for_command()
                    self._handle_command(command, source="voice")
                finally:
                    self._disarm_triggers()
                    self.wake.reset_for_next()
                    self._ui_wake_shown = False
                    self._activation_lock.release()
                    if self._ui and config.UI_IDLE_VISIBLE:
                        self._ui.show_idle()

        self._wake_thread = threading.Thread(target=wake_loop, daemon=True, name="razor-wake")
        self._wake_thread.start()

    def _start_hotkey(self) -> None:
        if not config.HOTKEY_ENABLED:
            return
        self._hotkey = GlobalHotkey(config.HOTKEY, lambda: self.activate_once(source="hotkey"))
        self._hotkey.start()

    def _handle_activation(
        self,
        trailing_command: str | None,
        *,
        source: str,
    ) -> None:
        if not self._activation_lock.acquire(blocking=False):
            return
        try:
            self._on_activate(source=source)
            command = trailing_command or self._listen_for_command()
            self._handle_command(command, source=source)
        finally:
            self._disarm_triggers()
            self.wake.reset_for_next()
            self._ui_wake_shown = False
            self._activation_lock.release()
            if self._ui and config.UI_IDLE_VISIBLE:
                self._ui.show_idle()

    def _handle_command(self, command: str | None, *, source: str) -> None:
        if not command:
            message = "(no command heard)"
            print(message)
            self._speak_async("I didn't catch that.")
            self._ui_set_response("I didn't catch that — try again?")
            self.actions.log(event="no_command", source=source, result=message)
            self._ui_schedule_hide()
            return

        command = self._clean_command(command)
        if not is_plausible_command(command):
            message = "I didn't catch that — try again?"
            print(message)
            self._ui_set_response(message)
            self.actions.log(event="bad_transcript", source=source, result=command)
            self._speak_async(message)
            self._ui_schedule_hide()
            return

        print(f">> {command}")
        self._ui_set_transcript(command, partial=False)
        result = self.handle_input(command, source=source)
        if result == "__EXIT__":
            self._speak_async("Catch ya later mate.", personality=False)
            self.shutdown()
            sys.exit(0)

        if result:
            print(result)
            if config.EXECUTE_BEFORE_SPEAK or source in {"voice", "hotkey", "clap"}:
                self._speak_async(result)
        print()
        self._ui_schedule_hide()

    def _wait_for_wake_word(self) -> str | None:
        self.actions.log(event="wake_listen_start", source="wake_word")
        trailing = self.wake.wait_for_activation()
        self.actions.log(
            event="wake_word_detected",
            source="wake_word",
            result=trailing or config.WAKE_RESPONSE,
        )
        return trailing

    def _pause_hub(self) -> None:
        if self._hub and self._hub.is_running:
            self._hub.stop()

    def _resume_hub(self) -> None:
        if self._hub and self._running and not self._hub.is_running:
            self._hub.start()

    def _listen_for_command(self) -> str | None:
        import numpy as np

        self._ui_set_status("listening")
        self._pause_hub()
        if self._stt is None:
            self._stt = get_speech_to_text(self.stt_engine)
        stt = self._stt
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
                self._ui_set_transcript(partial_text, partial=True)
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
            while result["text"] is None and self._running:
                time.sleep(0.05)
        finally:
            remaining = stt.flush()
            background.stop()
            if result["text"] is None and remaining:
                result["text"] = remaining
            self._resume_hub()

            if result["text"] is None and remaining:
                result["text"] = remaining
            self._resume_hub()

        text = result["text"]
        return self._clean_command(text) if text else None

    @staticmethod
    def _clean_command(text: str) -> str:
        """Remove wake phrase bleed-through from command transcripts."""
        cleaned = text.strip()
        if not cleaned:
            return cleaned
        lowered = cleaned.lower()
        for prefix in (
            "hey razor",
            "hey razer",
            "hey razr",
            "hay razor",
            "a razor",
            "hi razor",
            "high razor",
        ):
            if lowered.startswith(prefix):
                return cleaned[len(prefix) :].strip(" ,.!")
        return cleaned

    def _ui_show_idle(self) -> None:
        if self._ui:
            self._ui.show_idle()

    def _ui_show_activated(self) -> None:
        if self._ui:
            self._ui.show_activated()

    def _ui_set_status(self, status: str) -> None:
        if self._ui:
            self._ui.set_status(status)

    def _ui_set_transcript(self, text: str, *, partial: bool = False) -> None:
        if self._ui:
            self._ui.set_transcript(text, partial=partial)

    def _ui_set_response(self, text: str) -> None:
        if self._ui:
            self._ui.set_response(text)

    def _ui_schedule_hide(self) -> None:
        if self._ui:
            self._ui.schedule_hide()

    def _ui_show_done(self) -> None:
        if self._ui:
            self._ui.show_done()

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

    def _speak_async(self, text: str, *, personality: bool = True) -> None:
        threading.Thread(
            target=self._speak,
            args=(text,),
            kwargs={"personality": personality},
            daemon=True,
            name="razor-tts",
        ).start()

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
                "tray": self.tray_mode,
                "ui": config.UI_ENABLED,
                "clap": config.CLAP_ENABLED,
            },
        )

    def _print_banner(self) -> None:
        print(f"{config.APP_NAME} v{config.APP_VERSION} — Jarvis mode")
        print(f"Say '{config.WAKE_PHRASE.title()}' — reflex commands run instantly.")
        if config.UI_IDLE_VISIBLE:
            print("Idle UI visible — Razor is always listening.")
        if config.HOTKEY_ENABLED:
            print(f"Or press {config.HOTKEY} for instant activation.")
        if config.CLAP_ENABLED:
            print("Or clap twice to activate.")
        if config.UI_ENABLED:
            print("Activation UI enabled — overlay appears when listening.")
        if self.use_ai:
            print("AI reasoning enabled via Ollama.")
        if self.use_tts:
            print("Voice output enabled (ElevenLabs with local fallback).")
        if config.SAFE_MODE:
            print("Safe mode enabled for destructive actions.")
        print("Press Ctrl+C to stop.\n")
