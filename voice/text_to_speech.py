"""Text-to-speech synthesis via ElevenLabs with local fallback."""

from __future__ import annotations

import json
import platform
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import config
from utils.helpers import ensure_dir
from utils.logger import get_logger

logger = get_logger(__name__)


class TTSError(Exception):
    """Raised when text-to-speech synthesis or playback fails."""


class TextToSpeech:
    """Converts text to speech using ElevenLabs, with optional local fallback."""

    API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    def __init__(
        self,
        api_key: str | None = None,
        voice_id: str | None = None,
        model_id: str | None = None,
        output_dir: str | Path | None = None,
        provider: str | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else config.ELEVENLABS_API_KEY
        self.voice_id = voice_id or config.ELEVENLABS_VOICE_ID
        self.model_id = model_id or config.ELEVENLABS_MODEL
        self.output_dir = Path(output_dir or config.AUDIO_DIR)
        self.provider = (provider or config.TTS_PROVIDER).lower()
        ensure_dir(str(self.output_dir))

    def speak(self, text: str) -> Path | None:
        """Synthesize speech and play it."""
        cleaned = text.strip()
        if not cleaned:
            raise TTSError("Cannot speak empty text.")

        if self.provider == "local":
            self._speak_local(cleaned)
            return None

        try:
            audio_path = self._synthesize_elevenlabs(cleaned)
            self.play(audio_path)
            return audio_path
        except TTSError as exc:
            if self.provider == "auto" and self._should_fallback(exc):
                logger.warning("ElevenLabs failed (%s). Falling back to local TTS.", exc)
                self._speak_local(cleaned)
                return None
            raise

    def synthesize(self, text: str) -> Path:
        """Download synthesized speech from ElevenLabs."""
        return self._synthesize_elevenlabs(text)

    def _synthesize_elevenlabs(self, text: str) -> Path:
        if not self.api_key:
            raise TTSError(
                "ElevenLabs API key not set. Set ELEVENLABS_API_KEY in .env or use TTS_PROVIDER=local."
            )
        if not self.voice_id:
            raise TTSError(
                "ElevenLabs voice ID not set. Set ELEVENLABS_VOICE_ID in .env or use TTS_PROVIDER=local."
            )

        url = (
            f"{self.API_URL.format(voice_id=self.voice_id)}"
            f"?output_format={config.ELEVENLABS_OUTPUT_FORMAT}"
        )
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": config.ELEVENLABS_STABILITY,
                "similarity_boost": config.ELEVENLABS_SIMILARITY,
                "style": config.ELEVENLABS_STYLE,
                "use_speaker_boost": True,
            },
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "xi-api-key": self.api_key,
                "Accept": "audio/mpeg",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=config.ELEVENLABS_TIMEOUT) as response:
                audio_bytes = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            message = self._friendly_http_error(exc.code, detail)
            raise TTSError(message) from exc
        except urllib.error.URLError as exc:
            raise TTSError(f"Cannot reach ElevenLabs API: {exc}") from exc

        if not audio_bytes:
            raise TTSError("ElevenLabs returned empty audio.")

        filename = f"razor_{int(time.time() * 1000)}.mp3"
        output_path = self.output_dir / filename
        output_path.write_bytes(audio_bytes)
        logger.info("Saved TTS audio to %s", output_path)
        return output_path

    def _speak_local(self, text: str) -> None:
        """Speak using the OS built-in voice (free, works offline)."""
        try:
            import pyttsx3
        except ImportError as exc:
            raise TTSError(
                "Local TTS requires pyttsx3. Install with: pip install pyttsx3"
            ) from exc

        engine = pyttsx3.init()
        engine.setProperty("rate", config.TTS_LOCAL_RATE)

        for voice in engine.getProperty("voices"):
            name = voice.name.lower()
            voice_id = voice.id.lower()
            if "australia" in name or "en-au" in voice_id or "en-au" in name:
                engine.setProperty("voice", voice.id)
                break

        engine.say(text)
        engine.runAndWait()
        logger.info("Spoke via local TTS")

    @staticmethod
    def _should_fallback(exc: TTSError) -> bool:
        message = str(exc).lower()
        return any(
            token in message
            for token in (
                "402",
                "401",
                "payment_required",
                "free plan",
                "library voices",
                "cannot reach elevenlabs",
            )
        )

    @staticmethod
    def _friendly_http_error(code: int, detail: str) -> str:
        if code == 402 and "library voices" in detail.lower():
            return (
                "ElevenLabs free plan cannot use library voices via the API. "
                "Upgrade your plan, use a voice you created/cloned, or set TTS_PROVIDER=local in config."
            )
        return f"ElevenLabs HTTP {code}: {detail}"

    def play(self, audio_path: str | Path) -> None:
        """Auto-play a saved audio file."""
        path = Path(audio_path)
        if not path.is_file():
            raise TTSError(f"Audio file not found: {path}")

        system = platform.system()
        if system == "Windows":
            self._play_windows(path)
            return
        if system == "Darwin":
            subprocess.run(["afplay", str(path)], check=True)
            return

        for player in (["ffplay", "-nodisp", "-autoexit", str(path)], ["mpg123", str(path)]):
            try:
                subprocess.run(player, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue

        raise TTSError("No supported audio player found for this platform.")

    @staticmethod
    def _play_windows(path: Path) -> None:
        """Play MP3 on Windows using the MCI interface."""
        from ctypes import windll

        alias = "razor_tts"
        path_str = str(path.resolve())
        mci = windll.winmm.mciSendStringW
        mci(f"close {alias}", None, 0, None)
        error_code = mci(f'open "{path_str}" type mpegvideo alias {alias}', None, 0, None)
        if error_code != 0:
            raise TTSError(f"Failed to open audio for playback (MCI error {error_code}).")
        error_code = mci(f"play {alias} wait", None, 0, None)
        mci(f"close {alias}", None, 0, None)
        if error_code != 0:
            raise TTSError(f"Failed to play audio (MCI error {error_code}).")

    def is_configured(self) -> bool:
        """Return True when TTS can run with the current provider settings."""
        if self.provider == "local":
            return True
        if self.provider == "auto":
            return True
        return bool(self.api_key and self.voice_id)
