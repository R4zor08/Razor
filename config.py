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
APP_VERSION = "0.4.0"

# Jarvis mind — speed + personality
PERSONALITY = "jarvis"  # jarvis | aussie
EXECUTE_BEFORE_SPEAK = True
WARM_MODELS_ON_STARTUP = True
PROACTIVE_GREETING = True
JARVIS_BRIEFING = False

# Voice
WAKE_PHRASE = "hey razor"
WAKE_RESPONSE = "Ready." if PERSONALITY == "jarvis" else "Yes mate?"
WAKE_WORD = "razor"
SAMPLE_RATE = 16000
VOICE_BLOCK_MS = 500
MIC_DEVICE = None  # None = system default; run `python main.py --list-mics` to list devices

# Speech-to-text engine: "whisper" or "vosk"
STT_ENGINE = "vosk"

# Vosk (streaming, lightweight)
VOSK_MODEL_PATH = "assets/models/vosk-model-small-en-us-0.15"

# Whisper (batch per utterance, higher accuracy)
WHISPER_MODEL = "base.en"
WHISPER_DEVICE = "cpu"  # "cpu" or "cuda"
WHISPER_COMPUTE_TYPE = "int8"  # use "float16" with cuda

# Silence detection (Whisper utterance boundaries)
SPEECH_ENERGY_THRESHOLD = 400  # RMS threshold for int16 PCM (tune for your mic)
SILENCE_DURATION_MS = 700  # silence after speech triggers transcription
MIN_SPEECH_MS = 300  # ignore utterances shorter than this

# AI
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_INTENT_MODEL = "llama3.2:1b"  # faster model for intent parsing; empty = use OLLAMA_MODEL
OLLAMA_TIMEOUT = 60
AI_ENABLED = True
CHAT_FALLBACK = False  # don't run chat on misheard garbage

# Text-to-speech
TTS_ENABLED = True
TTS_PROVIDER = "local"  # local | auto | elevenlabs — local is fastest
TTS_LOCAL_RATE = 195
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
APP_LOG_FILE = "assets/logs/razor.log"
ACTION_LOG_FILE = "assets/logs/actions.log"

# Logging & safety
FILE_LOG_ENABLED = True
ACTION_LOG_ENABLED = True
SAFE_MODE = True
SAFE_MODE_STRICT = False

# Startup & always-on
STARTUP_FOLDER_NAME = "Razor AI"
TRAY_ENABLED = True
TRAY_ON_START = True  # minimize to tray when launched with --tray
HOTKEY_ENABLED = True
HOTKEY = "<ctrl>+<shift>+r"
PROCESSING_FEEDBACK = True
PROCESSING_SPEAK = False  # speak "One sec mate" while Ollama thinks

# Activation UI
UI_ENABLED = True
UI_AUTO_HIDE_SECONDS = 8
UI_POSITION = "bottom"  # bottom | top
UI_IDLE_VISIBLE = True  # show compact "Say Hey Razor" bar while idle
UI_IDLE_COMPACT = True  # collapse to idle pill instead of hiding completely

# Wake — UI appears instantly on detection (before beep/TTS)
WAKE_UI_FIRST = True
WAKE_DEBUG = False  # log partial STT when razor-like words heard
WAKE_BEEP = True
WAKE_SPEAK = False  # UI + beep only — listen faster

# Double-clap activation
CLAP_ENABLED = True
CLAP_THRESHOLD = 2500  # RMS energy for a clap (tune for your mic)
CLAP_MIN_GAP_MS = 120
CLAP_MAX_GAP_MS = 700
CLAP_COOLDOWN_MS = 2500

# Single instance (prevent duplicate tray icons)
SINGLE_INSTANCE = True

# File search
FILE_SEARCH_MAX_RESULTS = 25
FILE_SEARCH_DEPTH = 8
FILE_SEARCH_WIDE = True  # search entire user profile instead of Desktop/Downloads only
