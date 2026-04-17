import json
from urllib import error

import pytest

from models.ollama_client import OllamaClient
from tools.errors import ModelInvocationError


class _FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_list_models_returns_sorted_unique_names(monkeypatch) -> None:
    def _fake_urlopen(req, timeout):
        return _FakeHTTPResponse(
            {
                "models": [
                    {"name": "llama3.1"},
                    {"name": "qwen2.5:14b"},
                    {"model": "llama3.1"},
                    {"name": "  mistral  "},
                ]
            }
        )

    monkeypatch.setattr("models.ollama_client.request.urlopen", _fake_urlopen)

    client = OllamaClient(base_url="http://localhost:11434")

    assert client.list_models() == ["llama3.1", "mistral", "qwen2.5:14b"]


def test_list_models_raises_friendly_error_when_unreachable(monkeypatch) -> None:
    def _fake_urlopen(req, timeout):
        raise error.URLError("connection refused")

    monkeypatch.setattr("models.ollama_client.request.urlopen", _fake_urlopen)

    client = OllamaClient(base_url="http://localhost:11434")

    with pytest.raises(ModelInvocationError, match="Failed to reach Ollama"):
        client.list_models()


def test_list_models_raises_when_response_has_no_models_list(monkeypatch) -> None:
    monkeypatch.setattr(
        "models.ollama_client.request.urlopen",
        lambda req, timeout: _FakeHTTPResponse({"unexpected": []}),
    )

    client = OllamaClient(base_url="http://localhost:11434")

    with pytest.raises(ModelInvocationError, match="did not include a valid 'models' list"):
        client.list_models()
