# Razor AI v0.3

Local voice assistant for Windows — say **"Hey Razor"** and the UI appears instantly. No hotkey or extra activation needed.

## Features

- **"Hey Razor" = instant UI** — overlay pops up immediately when wake word is heard
- **Idle UI pill** — compact bar always visible: "Razor — say Hey Razor" (always listening)
- Wake word with improved matching (razer, razr, hay razor, split utterances)
- Optional: global hotkey (`Ctrl+Shift+R`) or double-clap
- Energy-themed dark overlay (cyan accent) — listening, transcript, response
- Background tray mode — built-in on login via `--install-startup`
- Fast speech-to-text (Vosk default; Whisper optional)
- Natural language commands via local Ollama
- Web search, open URLs, create files/folders
- Wide local file search across your user profile
- Australian voice output (ElevenLabs with local fallback)
- OS control: apps, files, volume, brightness, windows, shortcuts
- Safe mode for shutdown/restart confirmation
- Single-instance lock (no duplicate tray icons)
- Action logging to `assets/logs/actions.log`

## Quick start

```powershell
pip install -r requirements.txt
python main.py --tray
```

Say **"Hey Razor"** only — UI expands instantly. No button press required.

Hotkey and clap are optional fallbacks.

## Built into your laptop (auto-start)

```powershell
python main.py --install-startup
```

Then **sign out and back in** (or reboot). Razor starts silently via `pythonw` in tray mode with wake word, UI, hotkey, and clap detection.

Remove with:

```powershell
python main.py --uninstall-startup
```

## Activation UI

| State | What you see |
|-------|----------------|
| **Idle** | Compact pill at bottom: "Razor — say Hey Razor" |
| **Wake** | Expands instantly on "Hey Razor" — "Yes mate?" |
| **Listening** | Live transcript, pulse indicator |
| **Processing** | "Processing..." — stays visible |
| **Done** | Shows response, then collapses to idle pill after 8s |

Config: `UI_IDLE_VISIBLE`, `WAKE_UI_FIRST`, `UI_AUTO_HIDE_SECONDS`

## Activation methods (optional extras)

| Method | Action |
|--------|--------|
| **"Hey Razor"** | Wake word → UI pops up → "Yes mate?" → listen for command |
| **Ctrl+Shift+R** | Instant activation without wake word |
| **Double clap** | Two claps within ~0.7s (tune `CLAP_THRESHOLD` in config) |
| **Tray menu** | Right-click blue **R** → Activate (listen) |

## Activation UI

When Razor activates, a small always-on-top overlay appears (bottom-center by default):

- **Status** — Yes mate? / Listening... / Processing... / Confirm?
- **Transcript** — what you said (live partial text with Vosk)
- **Response** — Razor's reply or action result
- **Auto-hide** — hides after 5 seconds when idle (`UI_AUTO_HIDE_SECONDS`)

Disable UI: set `UI_ENABLED = False` in `config.py`.

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
| `UI_IDLE_VISIBLE` | `True` | Compact idle pill always on screen |
| `WAKE_UI_FIRST` | `True` | UI before beep/TTS on wake word |
| `WAKE_DEBUG` | `False` | Log partial STT for wake tuning |
| `UI_AUTO_HIDE_SECONDS` | `5` | Hide overlay after idle |
| `WAKE_BEEP` | `True` | Instant beep on activation |
| `WAKE_SPEAK` | `True` | TTS "Yes mate?" (runs after UI/beep) |
| `CLAP_ENABLED` | `True` | Double-clap activation |
| `CLAP_THRESHOLD` | `2500` | Raise if false triggers; lower if claps missed |
| `SINGLE_INSTANCE` | `True` | Prevent duplicate Razor processes |
| `STT_ENGINE` | `vosk` | Faster than Whisper on CPU |
| `HOTKEY` | `<ctrl>+<shift>+r` | Global activation |

## Troubleshooting

**No tray icon** — Run `python main.py --tray`; check Task Manager for `pythonw.exe`; click **^** near clock.

**UI doesn't appear** — Ensure `UI_ENABLED = True`; tkinter is included with Python on Windows.

**Clap too sensitive / not detected** — Tune `CLAP_THRESHOLD`, `CLAP_MIN_GAP_MS`, `CLAP_MAX_GAP_MS`.

**Quit cleanly** — Tray → **Quit** (don't Ctrl+C in terminal when using `--tray`).

**Mic overflow** — Run `--list-mics`, set `MIC_DEVICE` or leave `None`.

## Acceptance tests

1. Reboot/sign-in → Razor in tray, no terminal
2. "Hey Razor" → UI within ~0.5s, then listens
3. "open notepad" → Notepad opens, UI shows result, logged
4. Ctrl+Shift+R → UI without wake word
5. Double clap → UI appears
6. UI auto-hides after idle
7. Tray → Quit → clean exit
8. "shutdown" → confirmation in UI; no shutdown until "yes"

## Logs

- `assets/logs/razor.log` — application log
- `assets/logs/actions.log` — JSON audit log

## Requirements

- Python 3.11+
- Ollama running locally
- Vosk model at `assets/models/vosk-model-small-en-us-0.15`
- Microphone
- pystray + Pillow (tray icon)
