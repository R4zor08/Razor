"""Ollama API client."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

import config
from utils.logger import get_logger

logger = get_logger(__name__)


class OllamaError(Exception):
    """Raised when Ollama communication fails."""


class OllamaClient:
    """Communicates with a local Ollama instance."""

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.host = (host or config.OLLAMA_HOST).rstrip("/")
        self.model = model or config.OLLAMA_MODEL
        self.timeout = timeout or config.OLLAMA_TIMEOUT

    def generate(self, prompt: str, *, json_mode: bool = True, model: str | None = None) -> str:
        """Send a prompt and return the model response text."""
        payload: dict[str, Any] = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"

        response = self._post("/api/generate", payload)
        text = response.get("response", "").strip()
        if not text:
            raise OllamaError("Ollama returned an empty response.")
        return text

    def generate_json(self, prompt: str, *, model: str | None = None) -> dict[str, Any]:
        """Send a prompt and return a parsed JSON object."""
        raw = self.generate(prompt, json_mode=True, model=model)
        return self.parse_json_response(raw)

    def is_available(self) -> bool:
        """Check whether the Ollama server is reachable."""
        try:
            self._get("/api/tags")
            return True
        except OllamaError:
            return False

    @staticmethod
    def parse_json_response(text: str) -> dict[str, Any]:
        """Extract and parse JSON from a model response."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise OllamaError(f"Failed to parse JSON from model response: {exc}") from exc

        if not isinstance(data, dict):
            raise OllamaError("Model response JSON must be an object.")
        return data

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.host}{path}"
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OllamaError(f"Ollama HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise OllamaError(
                f"Cannot connect to Ollama at {self.host}. Is Ollama running?"
            ) from exc

    def chat(self, prompt: str, *, model: str | None = None) -> str:
        """Return a conversational response (non-JSON)."""
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": False,
        }
        response = self._post("/api/generate", payload)
        text = response.get("response", "").strip()
        if not text:
            raise OllamaError("Ollama returned an empty response.")
        return text

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{self.host}{path}"
        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise OllamaError(
                f"Cannot connect to Ollama at {self.host}. Is Ollama running?"
            ) from exc


# Shared client instance for lower latency
_client_instance: OllamaClient | None = None


def get_ollama_client() -> OllamaClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = OllamaClient()
    return _client_instance
