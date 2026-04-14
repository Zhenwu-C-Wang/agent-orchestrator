from __future__ import annotations

import json
import re

from models.model_runner import ModelRequest, StructuredModelRunner, StructuredModelT
from models.ollama_client import OllamaClient

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
    ) -> None:
        self.model = model
        self.client = client or OllamaClient()
        self.temperature = temperature

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
        raw_text = self.client.generate(
            model=self.model,
            prompt=prompt,
            system=request.system_prompt,
            options={"temperature": self.temperature},
        )
        payload = extract_json_payload(raw_text)
        return response_model.model_validate_json(payload)
