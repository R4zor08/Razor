"""Application configuration."""

APP_NAME = "Razor AI"
APP_VERSION = "0.1.0"

# Voice
WAKE_PHRASE = "hey razor"
WAKE_RESPONSE = "Yes mate?"
WAKE_WORD = "razor"
SAMPLE_RATE = 16000
VOICE_BLOCK_MS = 250
MIC_DEVICE = None  # None = system default microphone

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

# Paths
ASSETS_DIR = "assets"
AUDIO_DIR = "assets/audio"
LOGS_DIR = "assets/logs"

# File search
FILE_SEARCH_MAX_RESULTS = 25
FILE_SEARCH_DEPTH = 6
