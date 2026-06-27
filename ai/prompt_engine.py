"""Prompt construction and management."""

from __future__ import annotations

INTENT_SYSTEM_PROMPT = """You are Razor, a Windows voice assistant command parser.
Convert the user's natural language request into a JSON object with exactly these fields:
- "action": one of the allowed action strings
- "value": a string parameter for the action, or null if not needed

Allowed actions:
- "open_app"       — launch an application (value = app name)
- "close_app"      — close an application (value = app name)
- "open_folder"    — open a folder (value = desktop, downloads, documents, pictures, music, videos, home, or a path)
- "open_file"      — open a file by name (value = file name)
- "search_file"    — search for files (value = search keyword)
- "shutdown"       — shut down the computer (value = null)
- "restart"        — restart the computer (value = null)
- "help"           — show help (value = null)
- "exit"           — exit the assistant (value = null)
- "unknown"        — request cannot be mapped (value = original request)

Rules:
- Respond with JSON only. No markdown, no explanation.
- Extract only the target name/keyword into "value".
- Map synonyms: "launch", "start", "run" -> open_app; "quit", "kill", "close" -> close_app.
- Examples:
  "can you open chrome for me" -> {"action":"open_app","value":"chrome"}
  "open my downloads folder" -> {"action":"open_folder","value":"downloads"}
  "find my budget spreadsheet" -> {"action":"search_file","value":"budget spreadsheet"}
  "shut down the pc" -> {"action":"shutdown","value":null}
"""


class PromptEngine:
    """Builds prompts for the LLM."""

    def build_intent_prompt(self, user_text: str) -> str:
        """Build a prompt that asks the model to return structured intent JSON."""
        return (
            f"{INTENT_SYSTEM_PROMPT}\n"
            f'User request: "{user_text.strip()}"\n'
            "JSON:"
        )
