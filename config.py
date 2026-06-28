"""Application configuration."""

import os
from pathlib import Path


def _load_dotenv() -> None:
    """Load variables from .env into os.environ (does not override existing env vars)."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()

APP_NAME = "Razor AI"
APP_VERSION = "0.1.0"

# Voice
WAKE_PHRASE = "hey razor"
WAKE_RESPONSE = "Yes mate?"
WAKE_WORD = "razor"
SAMPLE_RATE = 16000
VOICE_BLOCK_MS = 750
MIC_DEVICE = 1  # None = system default microphone

# Speech-to-text engine: "whisper" or "vosk"
STT_ENGINE = "whisper"

# Vosk (streaming, lightweight)
VOSK_MODEL_PATH = "assets/models/vosk-model-small-en-us-0.15"

# Whisper (batch per utterance, higher accuracy)
WHISPER_MODEL = "base.en"
WHISPER_DEVICE = "cpu"  # "cpu" or "cuda"
WHISPER_COMPUTE_TYPE = "int8"  # use "float16" with cuda

# Silence detection (Whisper utterance boundaries)
SPEECH_ENERGY_THRESHOLD = 400  # RMS threshold for int16 PCM (tune for your mic)
SILENCE_DURATION_MS = 1000  # silence after speech triggers transcription
MIN_SPEECH_MS = 300  # ignore utterances shorter than this

# AI
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_TIMEOUT = 60
AI_ENABLED = True

# Text-to-speech
TTS_ENABLED = True
TTS_PROVIDER = "auto"  # auto | elevenlabs | local
TTS_LOCAL_RATE = 175
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL = "eleven_multilingual_v2"
ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"
ELEVENLABS_TIMEOUT = 30
ELEVENLABS_STABILITY = 0.45
ELEVENLABS_SIMILARITY = 0.85
ELEVENLABS_STYLE = 0.35

# Paths
ASSETS_DIR = "assets"
AUDIO_DIR = "assets/audio"
LOGS_DIR = "assets/logs"

# File search
FILE_SEARCH_MAX_RESULTS = 25
FILE_SEARCH_DEPTH = 6
