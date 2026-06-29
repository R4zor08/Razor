"""Razor AI — entry point."""

import argparse
import sys

import config
from core.assistant import Assistant
from system.executor import Executor
from utils.logger import get_logger
from utils.startup import install_startup, uninstall_startup

logger = get_logger(__name__)


def run_cli(*, use_ai: bool = True) -> None:
    """Interactive CLI for text commands."""
    assistant = Assistant(use_ai=use_ai, use_tts=False)
    mode = "AI" if use_ai and config.AI_ENABLED else "CLI"
    print(f"{config.APP_NAME} v{config.APP_VERSION} — {mode} mode")
    print("Type a command or 'help' for available commands. Type 'exit' to quit.\n")

    while True:
        try:
            command = input("razor> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not command:
            continue

        result = assistant.handle_input(command, source="cli")
        if result == "__EXIT__":
            print("Goodbye.")
            break

        print(result)
        print()


def main() -> None:
    """Bootstrap and run Razor."""
    parser = argparse.ArgumentParser(description=f"{config.APP_NAME} assistant")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run text CLI instead of full voice assistant",
    )
    parser.add_argument(
        "--voice-direct",
        action="store_true",
        help="Always-listening voice mode without wake word (legacy)",
    )
    parser.add_argument(
        "--stt",
        choices=["whisper", "vosk"],
        default=None,
        help=f"Speech-to-text engine (default: {config.STT_ENGINE})",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Disable Ollama reasoning",
    )
    parser.add_argument(
        "--no-tts",
        action="store_true",
        help="Disable voice output",
    )
    parser.add_argument(
        "--install-startup",
        action="store_true",
        help="Install Razor to run automatically on Windows login",
    )
    parser.add_argument(
        "--uninstall-startup",
        action="store_true",
        help="Remove Razor from Windows startup",
    )
    args = parser.parse_args()

    if args.install_startup:
        print(install_startup())
        return

    if args.uninstall_startup:
        print(uninstall_startup())
        return

    use_ai = not args.no_ai
    use_tts = not args.no_tts

    if args.cli:
        run_cli(use_ai=use_ai)
        return

    if args.voice_direct:
        _run_voice_direct(stt_engine=args.stt, use_ai=use_ai, use_tts=use_tts)
        return

    assistant = Assistant(use_ai=use_ai, use_tts=use_tts, stt_engine=args.stt)
    assistant.run()


def _run_voice_direct(*, stt_engine: str | None, use_ai: bool, use_tts: bool) -> None:
    """Legacy direct-listening mode without wake word."""
    from voice.listener import Listener
    from voice.speech_to_text import SpeechToText
    from voice.audio_queue import BackgroundListener
    import time
    import numpy as np

    assistant = Assistant(use_ai=use_ai, use_tts=use_tts, stt_engine=stt_engine)
    stt = SpeechToText(engine=stt_engine)
    stt.reset()
    background = BackgroundListener()

    print(f"{config.APP_NAME} v{config.APP_VERSION} — Direct voice mode")
    print("Press Ctrl+C to stop.\n")

    partial_line = ""
    listening_indicator = False

    def on_audio(chunk: bytes) -> None:
        nonlocal partial_line, listening_indicator
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
        if final_text:
            print(f"\n>> {final_text}")
            result = assistant.handle_input(final_text, source="voice")
            if result and result != "__EXIT__":
                print(result)
                assistant._speak(result)
            stt.reset()

    try:
        background.start(on_audio)
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nGoodbye.")
    finally:
        background.stop()


if __name__ == "__main__":
    main()
