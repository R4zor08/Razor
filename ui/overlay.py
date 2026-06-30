"""Floating activation overlay — idle pill + expanded listening UI."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import font as tkfont

import config
from utils.logger import get_logger

logger = get_logger(__name__)

# Energy-inspired palette (dark + cyan accent)
_COLOR_BG = "#0a0e17"
_COLOR_PANEL = "#111827"
_COLOR_HEADER = "#0f172a"
_COLOR_ACCENT = "#00d4ff"
_COLOR_ACCENT_DIM = "#0099bb"
_COLOR_TEXT = "#e8f4fc"
_COLOR_MUTED = "#7dd3fc"
_COLOR_GLOW = "#00d4ff"

_STATUS_LABELS = {
    "activated": "Yes mate?",
    "listening": "Listening...",
    "processing": "Processing...",
    "responding": "Razor",
    "confirm": "Confirm?",
    "idle": f"Razor — say \"{config.WAKE_PHRASE.title()}\"",
}

_IDLE_W, _IDLE_H = 340, 52
_EXPANDED_W, _EXPANDED_H = 480, 168


class ActivationOverlay:
    """Thread-safe always-on-top overlay with compact idle + expanded active modes."""

    def __init__(self) -> None:
        self._queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._root: tk.Tk | None = None
        self._hide_timer: str | None = None
        self._visible = False
        self._expanded = False
        self._busy = False
        self._started = threading.Event()
        self._status_var: tk.StringVar | None = None
        self._transcript_var: tk.StringVar | None = None
        self._response_var: tk.StringVar | None = None
        self._pulse_var: tk.StringVar | None = None
        self._detail_frame: tk.Frame | None = None

    def start(self) -> None:
        if not config.UI_ENABLED:
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_ui, daemon=True, name="razor-ui")
        self._thread.start()
        self._started.wait(timeout=5.0)

    def stop(self) -> None:
        if self._root is not None:
            self._queue.put(("quit", None))

    def show_idle(self) -> None:
        self._post("idle", None)

    def show_activated(self, message: str | None = None) -> None:
        text = message or config.WAKE_RESPONSE
        self._post("show", text)

    def set_status(self, status: str) -> None:
        self._post("status", status)

    def set_transcript(self, text: str, *, partial: bool = False) -> None:
        self._post("transcript", (text, partial))

    def set_response(self, text: str) -> None:
        self._post("response", text)

    def schedule_hide(self, delay: float | None = None) -> None:
        self._post("hide_later", delay if delay is not None else config.UI_AUTO_HIDE_SECONDS)

    def hide(self) -> None:
        self._post("hide", None)

    def _post(self, action: str, payload: object) -> None:
        if not config.UI_ENABLED:
            return
        if self._thread is None or not self._thread.is_alive():
            self.start()
        self._queue.put((action, payload))

    def _run_ui(self) -> None:
        root = tk.Tk()
        self._root = root
        root.withdraw()
        root.title("Razor AI")
        root.configure(bg=_COLOR_BG)
        root.overrideredirect(True)
        root.attributes("-topmost", True)

        try:
            root.attributes("-alpha", 0.96)
        except tk.TclError:
            pass

        container = tk.Frame(
            root,
            bg=_COLOR_BG,
            highlightthickness=2,
            highlightbackground=_COLOR_GLOW,
        )
        container.pack(fill=tk.BOTH, expand=True)

        title_font = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        body_font = tkfont.Font(family="Segoe UI", size=10)
        small_font = tkfont.Font(family="Segoe UI", size=9)

        header = tk.Frame(container, bg=_COLOR_HEADER)
        header.pack(fill=tk.X)

        brand = tk.Label(
            header,
            text="⚡",
            font=title_font,
            fg=_COLOR_ACCENT,
            bg=_COLOR_HEADER,
            padx=8,
        )
        brand.pack(side=tk.LEFT)

        self._status_var = tk.StringVar(value=_STATUS_LABELS["idle"])
        status_lbl = tk.Label(
            header,
            textvariable=self._status_var,
            font=title_font,
            fg=_COLOR_ACCENT,
            bg=_COLOR_HEADER,
            anchor="w",
            pady=10,
        )
        status_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._detail_frame = tk.Frame(container, bg=_COLOR_BG)
        self._detail_frame.pack(fill=tk.BOTH, expand=True)

        self._transcript_var = tk.StringVar(value="")
        transcript_lbl = tk.Label(
            self._detail_frame,
            textvariable=self._transcript_var,
            font=body_font,
            fg=_COLOR_TEXT,
            bg=_COLOR_BG,
            anchor="w",
            padx=14,
            pady=6,
            wraplength=_EXPANDED_W - 28,
            justify=tk.LEFT,
        )
        transcript_lbl.pack(fill=tk.X)

        self._response_var = tk.StringVar(value="")
        response_lbl = tk.Label(
            self._detail_frame,
            textvariable=self._response_var,
            font=small_font,
            fg=_COLOR_MUTED,
            bg=_COLOR_BG,
            anchor="w",
            padx=14,
            pady=4,
            wraplength=_EXPANDED_W - 28,
            justify=tk.LEFT,
        )
        response_lbl.pack(fill=tk.X)

        self._pulse_var = tk.StringVar(value="")
        pulse_lbl = tk.Label(
            self._detail_frame,
            textvariable=self._pulse_var,
            font=small_font,
            fg=_COLOR_ACCENT_DIM,
            bg=_COLOR_BG,
            anchor="w",
            padx=14,
            pady=2,
        )
        pulse_lbl.pack(fill=tk.X)

        self._pulse_on = False
        self._detail_frame.pack_forget()

        root.after(50, self._poll_queue)
        root.after(400, self._animate_pulse)
        self._started.set()
        logger.info("Activation UI overlay started.")

        if config.UI_IDLE_VISIBLE:
            root.after(100, lambda: self._handle_action("idle", None))

        root.mainloop()

    def _apply_geometry(self, width: int, height: int) -> None:
        root = self._root
        if root is None:
            return
        root.update_idletasks()
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        position = (config.UI_POSITION or "bottom").lower()
        x = (screen_w - width) // 2
        y = 48 if position == "top" else screen_h - height - 72
        root.geometry(f"{width}x{height}+{x}+{y}")

    def _poll_queue(self) -> None:
        if self._root is None:
            return
        try:
            while True:
                action, payload = self._queue.get_nowait()
                self._handle_action(action, payload)
        except queue.Empty:
            pass
        if self._root.winfo_exists():
            self._root.after(30, self._poll_queue)

    def _handle_action(self, action: str, payload: object) -> None:
        root = self._root
        if root is None or self._status_var is None:
            return

        if action == "quit":
            root.quit()
            return

        if action == "idle":
            self._busy = False
            self._expanded = False
            self._status_var.set(_STATUS_LABELS["idle"])
            if self._transcript_var:
                self._transcript_var.set("")
            if self._response_var:
                self._response_var.set("")
            if self._pulse_var:
                self._pulse_var.set("")
            if self._detail_frame:
                self._detail_frame.pack_forget()
            if config.UI_IDLE_VISIBLE:
                self._apply_geometry(_IDLE_W, _IDLE_H)
                root.deiconify()
                root.lift()
                self._visible = True
            else:
                root.withdraw()
                self._visible = False
            self._cancel_hide_timer()
            return

        if action == "show":
            self._busy = True
            self._expanded = True
            if self._response_var:
                self._response_var.set("")
            if self._transcript_var:
                self._transcript_var.set("")
            msg = str(payload) if payload else config.WAKE_RESPONSE
            self._status_var.set(msg)
            if self._pulse_var:
                self._pulse_var.set("●")
            if self._detail_frame:
                self._detail_frame.pack(fill=tk.BOTH, expand=True)
            self._apply_geometry(_EXPANDED_W, _EXPANDED_H)
            root.deiconify()
            root.lift()
            root.attributes("-topmost", True)
            self._visible = True
            self._cancel_hide_timer()
            return

        if action == "status":
            key = str(payload)
            self._status_var.set(_STATUS_LABELS.get(key, key))
            if key in {"listening", "processing", "confirm"}:
                self._busy = True
                self._cancel_hide_timer()
            if key == "listening" and self._pulse_var:
                self._pulse_var.set("● listening")
            elif key == "processing" and self._pulse_var:
                self._pulse_var.set("● thinking")
            if not self._expanded:
                self._handle_action("show", config.WAKE_RESPONSE)
            elif not self._visible:
                root.deiconify()
                root.lift()
                self._visible = True
            return

        if action == "transcript":
            text, partial = payload  # type: ignore[misc]
            if self._transcript_var:
                prefix = "… " if partial else "You: "
                self._transcript_var.set(f"{prefix}{text}")
            return

        if action == "response":
            self._busy = False
            self._status_var.set(_STATUS_LABELS["responding"])
            if self._response_var:
                self._response_var.set(f"Razor: {payload}")
            if self._pulse_var:
                self._pulse_var.set("")
            return

        if action == "hide":
            if config.UI_IDLE_VISIBLE and config.UI_IDLE_COMPACT:
                self._handle_action("idle", None)
            else:
                root.withdraw()
                self._visible = False
                self._expanded = False
            self._busy = False
            self._cancel_hide_timer()
            return

        if action == "hide_later":
            if self._busy:
                return
            delay_ms = int(float(payload) * 1000)
            self._cancel_hide_timer()
            self._hide_timer = root.after(delay_ms, lambda: self._handle_action("hide", None))

    def _cancel_hide_timer(self) -> None:
        if self._root and self._hide_timer:
            try:
                self._root.after_cancel(self._hide_timer)
            except tk.TclError:
                pass
            self._hide_timer = None

    def _animate_pulse(self) -> None:
        if self._root is None or not self._root.winfo_exists():
            return
        if self._visible and self._expanded and self._pulse_var and self._pulse_var.get().startswith("●"):
            self._pulse_on = not self._pulse_on
            base = self._pulse_var.get().lstrip("●○ ").strip()
            self._pulse_var.set(f"{'●' if self._pulse_on else '○'} {base}".strip())
        self._root.after(400, self._animate_pulse)
