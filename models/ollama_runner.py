from __future__ import annotations

import json
import re

from pydantic import ValidationError

from models.model_runner import ModelRequest, StructuredModelRunner, StructuredModelT
from models.ollama_client import OllamaClient
from tools.retry import RetryPolicy

JSON_FENCE_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
JSON_OBJECT_RE = re.compile(r"(\{.*\})", re.DOTALL)


def extract_json_payload(raw_text: str) -> str:
    stripped = raw_text.strip()

    for pattern in (JSON_FENCE_RE, JSON_OBJECT_RE):
        match = pattern.search(stripped)
        if not match:
            continue
        candidate = match.group(1).strip()
        json.loads(candidate)
        return candidate

    json.loads(stripped)
    return stripped


class OllamaModelRunner(StructuredModelRunner):
    """Structured runner that parses JSON-like text from Ollama responses."""

    def __init__(
        self,
        model: str,
        client: OllamaClient | None = None,
        temperature: float = 0.1,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.model = model
        self.client = client or OllamaClient()
        self.temperature = temperature
        self.retry_policy = retry_policy or RetryPolicy()
        self._last_invocation_metadata: dict[str, object] = {}

    def generate_structured(
        self,
        request: ModelRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredModelT:
        schema_json = json.dumps(response_model.model_json_schema(), ensure_ascii=True)
        prompt = (
            f"{request.user_prompt}\n\n"
            "Return only one JSON object and do not wrap it in markdown.\n"
            f"JSON schema: {schema_json}"
        )
        last_error: Exception | None = None

        for attempt_number in range(1, self.retry_policy.max_attempts + 1):
            try:
                raw_text = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    system=request.system_prompt,
                    options={"temperature": self.temperature},
                )
                payload = extract_json_payload(raw_text)
                result = response_model.model_validate_json(payload)
                self._last_invocation_metadata = {
                    "runner": "ollama",
                    "model": self.model,
                    "cache_enabled": False,
                    "cache_hit": False,
                    "attempt_count": attempt_number,
                    "retry_count": attempt_number - 1,
                }
                return result
            except (RuntimeError, json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                self._last_invocation_metadata = {
                    "runner": "ollama",
                    "model": self.model,
                    "cache_enabled": False,
                    "cache_hit": False,
                    "attempt_count": attempt_number,
                    "retry_count": attempt_number - 1,
                }
                if attempt_number >= self.retry_policy.max_attempts:
                    break
                self.retry_policy.sleep_before_retry(attempt_number)

        raise RuntimeError(
            f"Ollama structured generation failed after {self.retry_policy.max_attempts} attempts: "
            f"{last_error}"
        ) from last_error

    def get_last_invocation_metadata(self) -> dict[str, object]:
        return dict(self._last_invocation_metadata)
