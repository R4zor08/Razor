"""Razor AI — entry point."""

import argparse
import sys
import time

import config
from system.executor import Executor
from utils.logger import get_logger

logger = get_logger(__name__)


def run_cli() -> None:
    """Interactive CLI for deterministic command execution."""
    executor = Executor()
    print(f"{config.APP_NAME} v{config.APP_VERSION} — CLI mode")
    print("Type a command or 'help' for available commands. Type 'exit' to quit.\n")

    while True:
        try:
            command = input("razor> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not command:
            continue

        result = executor.execute(command)
        if result == "__EXIT__":
            print("Goodbye.")
            break

        print(result)
        print()


def run_voice(stt_engine: str | None = None) -> None:
    """Continuous voice input — transcribes speech and prints text commands."""
    from voice.listener import Listener
    from voice.speech_to_text import SpeechToText

    import numpy as np

    try:
        stt = SpeechToText(engine=stt_engine)
        stt.reset()
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    print(f"{config.APP_NAME} v{config.APP_VERSION} — Voice mode ({stt.engine})")
    if stt.is_streaming:
        print("Speak into your microphone. Partial results appear while you talk.")
    else:
        print("Speak a command, then pause. Whisper transcribes after a short silence.")
    print("Press Ctrl+C to stop.\n")

    listener = Listener()
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

        if stt.consume_utterance_complete() and listening_indicator and not final_text:
            print("\r" + " " * 24 + "\r", end="", flush=True)
            listening_indicator = False

        if final_text:
            if partial_line:
                print("\r" + " " * (len(partial_line) + 8) + "\r", end="")
                partial_line = ""
            elif listening_indicator:
                print("\r" + " " * 24 + "\r", end="")
                listening_indicator = False
            print(f">> {final_text}")
            stt.reset()

    try:
        listener.listen_continuous(on_audio)
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        remaining = stt.flush()
        if remaining:
            print(f">> {remaining}")
        listener.stop()
        print("Goodbye.")


def main() -> None:
    """Bootstrap and run the assistant."""
    parser = argparse.ArgumentParser(description=f"{config.APP_NAME} assistant")
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Run in voice input mode (speech to text output)",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in CLI text input mode (default)",
    )
    parser.add_argument(
        "--stt",
        choices=["whisper", "vosk"],
        default=None,
        help=f"Speech-to-text engine (default: {config.STT_ENGINE})",
    )
    args = parser.parse_args()

    logger.info("Starting %s v%s", config.APP_NAME, config.APP_VERSION)

    if args.voice:
        run_voice(stt_engine=args.stt)
    else:
        run_cli()


if __name__ == "__main__":
    main()
