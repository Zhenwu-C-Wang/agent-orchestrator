from __future__ import annotations

import json
from typing import Any
from urllib import error, request


class OllamaClient:
    """Thin HTTP client for Ollama's generate endpoint."""

    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(
        self,
        *,
        model: str,
        prompt: str,
        system: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        req = request.Request(
            url=f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise RuntimeError(f"Failed to reach Ollama at {self.base_url}: {exc}") from exc

        try:
            return body["response"]
        except KeyError as exc:
            raise RuntimeError(f"Ollama response did not include a 'response' field: {body}") from exc
