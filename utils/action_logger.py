"""Action audit logging."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import config
from utils.helpers import ensure_dir


class ActionLogger:
    """Append-only logger for user commands and system actions."""

    def __init__(self, log_path: str | Path | None = None) -> None:
        self.log_path = Path(log_path or config.ACTION_LOG_FILE)
        ensure_dir(str(self.log_path.parent))

    def log(
        self,
        *,
        event: str,
        source: str,
        input_text: str | None = None,
        intent: dict | None = None,
        result: str | None = None,
        meta: dict | None = None,
    ) -> None:
        if not config.ACTION_LOG_ENABLED:
            return

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "source": source,
            "input": input_text,
            "intent": intent,
            "result": result,
            "meta": meta or {},
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
