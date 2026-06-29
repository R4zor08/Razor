# Razor AI

Local voice assistant for Windows — wake word, offline STT, Ollama reasoning, and OS control.

## Features

- Wake word activation (`Hey Razor`)
- Speech-to-text (Whisper or Vosk)
- Natural language commands via local Ollama
- Australian voice output (ElevenLabs with local fallback)
- OS control: apps, files, volume, windows, shortcuts
- Safe mode for shutdown/restart confirmation
- Action logging to `assets/logs/actions.log`

## Quick start

```bash
pip install -r requirements.txt
python main.py
```

Say **"Hey Razor"**, then speak your command.

## Modes

| Command | Description |
|---------|-------------|
| `python main.py` | Full assistant (default) |
| `python main.py --cli` | Text-only CLI |
| `python main.py --no-tts` | Voice without speech output |
| `python main.py --no-ai` | Deterministic commands only |
| `python main.py --stt vosk` | Use Vosk instead of Whisper |

## Run on Windows startup

```bash
python main.py --install-startup
```

Remove with:

```bash
python main.py --uninstall-startup
```

Or run manually at login via `scripts/start_razor.bat`.

## Configuration

Copy `.env.example` to `.env` and set:

```
ELEVENLABS_API_KEY=your-key
ELEVENLABS_VOICE_ID=your-voice-id
```

Edit `config.py` for wake phrase, Ollama model, safe mode, and mic device.

## Logs

- `assets/logs/razor.log` — application log
- `assets/logs/actions.log` — JSON audit log of commands and results

## Requirements

- Python 3.11+
- Ollama running locally (`ollama serve`)
- Microphone
- ElevenLabs API key (optional — local TTS fallback available)
