# Razor AI v0.4 — Jarvis Mode

Local voice assistant for Windows — say **"Hey Razor"** and the UI appears instantly. Reflex commands run in under a second; complex questions use local Ollama.

## Jarvis Mind

| Layer | Behavior |
|-------|----------|
| **Presence** | Always listening in tray; idle pill shows Razor is ready |
| **Reflexes** | "open notepad", "volume down" → action in &lt;2s, no LLM |
| **Mind** | Complex requests → Ollama plans tools, brief Jarvis reply |
| **Memory** | Remembers name, last app, recent commands across restarts |

### Speed tips

- `TTS_PROVIDER = "local"` — skip ElevenLabs API delays (default in v0.4)
- `WAKE_SPEAK = False` — UI + beep only; listen immediately after wake
- `CHAT_FALLBACK = False` — misheard garbage won't trigger 20s chat
- `WARM_MODELS_ON_STARTUP = True` — preloads Vosk + Ollama on launch
- Reflex rules in `core/intent_engine.py` run first (&lt;50ms)

### Memory commands

| Say this | Result |
|----------|--------|
| "Remember my name is Alex" | Stored in `assets/data/memory.json` |
| "What's my name?" | Recalls stored name |
| "What do you remember?" | Summary of stored context |
| "Open calculator" then "Open it again" | Reopens last app from memory |

Memory file is gitignored at `assets/data/memory.json`.

## Features

- **"Hey Razor" = instant UI** — overlay expands immediately on wake word
- **Idle UI pill** — compact bar: "Razor — say Hey Razor"
- **Execute before speak** — OS action runs first, TTS after
- **Cached Vosk STT** — model loads once, shared for wake + commands
- Wake word with improved matching (razer, razr, hay razor)
- Optional: global hotkey (`Ctrl+Shift+R`) or double-clap
- Energy-themed dark overlay (cyan accent)
- Background tray mode — auto-start on login via `--install-startup`
- Two-tier brain: reflex rules → memory → agent (1b) → chat (3b)
- Web search, open URLs, create files/folders, volume, brightness, windows
- Jarvis personality — calm, brief ("Certainly.", "Done.", "Right away.")
- Safe mode for shutdown/restart confirmation
- Single-instance lock, action logging

## Quick start

```powershell
pip install -r requirements.txt
python main.py --tray
```

Say **"Hey Razor"** only — UI expands instantly. No button press required.

## Built into your laptop (auto-start)

```powershell
python main.py --install-startup
```

Sign out and back in (or reboot). Razor starts silently via `pythonw` in tray mode.

Remove with:

```powershell
python main.py --uninstall-startup
```

## Activation UI

| State | What you see |
|-------|----------------|
| **Idle** | Compact pill: "Razor — say Hey Razor" |
| **Wake** | Expands instantly — "Ready." |
| **Listening** | Live transcript, pulse indicator |
| **Processing** | "Processing..." — stays visible |
| **Done** | Flash "Done." then response; collapses to idle after 8s |

## Activation methods

| Method | Action |
|--------|--------|
| **"Hey Razor"** | Wake word → UI → listen for command |
| **Ctrl+Shift+R** | Instant activation without wake word |
| **Double clap** | Two claps within ~0.7s |
| **Tray menu** | Right-click **R** → Activate |

## Modes

| Command | Description |
|---------|-------------|
| `python main.py --tray` | Background + tray + UI (recommended) |
| `python main.py` | Console or tray if `TRAY_ON_START` |
| `python main.py --cli` | Text-only CLI (no UI/voice) |
| `python main.py --no-tts` | Voice without speech output |
| `python main.py --list-mics` | List microphone devices |

## Configuration (`config.py`)

| Setting | Default | Notes |
|---------|---------|-------|
| `PERSONALITY` | `jarvis` | `jarvis` or `aussie` |
| `TTS_PROVIDER` | `local` | Fastest; set `auto` for ElevenLabs |
| `WAKE_SPEAK` | `False` | Skip wake TTS for faster listen |
| `WAKE_BEEP` | `True` | Instant beep on activation |
| `CHAT_FALLBACK` | `False` | No chat on unknown/misheard input |
| `EXECUTE_BEFORE_SPEAK` | `True` | Action before voice reply |
| `WARM_MODELS_ON_STARTUP` | `True` | Preload Vosk + Ollama |
| `PROACTIVE_GREETING` | `True` | Once-per-day "Good morning" on startup |
| `UI_IDLE_VISIBLE` | `True` | Compact idle pill always on screen |
| `STT_ENGINE` | `vosk` | Faster than Whisper on CPU |
| `OLLAMA_INTENT_MODEL` | `llama3.2:1b` | Agent / tool picking |
| `OLLAMA_MODEL` | `llama3.2:3b` | Chat / reasoning |

## Troubleshooting

**Slow first command** — Check `razor.log` for "Models warmed". Ensure Ollama is running.

**ElevenLabs 402** — Set `TTS_PROVIDER = "local"` (default). Session auto-disables ElevenLabs after first 402.

**Misheard commands** — Short/garbage transcripts are rejected without calling Ollama.

**No tray icon** — Run `python main.py --tray`; check Task Manager for `pythonw.exe`.

**Quit cleanly** — Tray → **Quit** (don't Ctrl+C when using `--tray`).

## Acceptance tests

1. Startup → idle pill visible, "Models warmed" in log, no Vosk reload on 2nd command
2. "Hey Razor" → "open notepad" → Notepad in &lt;3s, TTS after
3. "Hey Razor" → "volume down" → volume changes in &lt;2s (no Ollama in log)
4. "Hey Razor" → "what is Python" → Jarvis-style chat via Ollama 3b
5. "Open calculator" then "open it again" → opens calculator from memory
6. Misheard/empty transcript → "didn't catch that", no Ollama chat
7. ElevenLabs 402 → local TTS only for rest of session
8. `actions.log` records executions; `memory.json` persists across restart
9. `python main.py --cli` still works
10. Tray → Quit → clean shutdown

## Logs

- `assets/logs/razor.log` — application log
- `assets/logs/actions.log` — JSON audit log
- `assets/data/memory.json` — user memory (local only)

## Requirements

- Python 3.11+
- Ollama running locally (`llama3.2:1b`, `llama3.2:3b`)
- Vosk model at `assets/models/vosk-model-small-en-us-0.15`
- Microphone
- pystray + Pillow (tray icon)
