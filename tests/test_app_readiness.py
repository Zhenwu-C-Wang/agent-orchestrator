import app
from tools.errors import ModelInvocationError


class _StubOllamaClient:
    def __init__(self, *, models=None, error=None, **kwargs) -> None:
        self.models = list(models or [])
        self.error = error

    def list_models(self) -> list[str]:
        if self.error is not None:
            raise self.error
        return list(self.models)


def test_inspect_ollama_readiness_reports_unreachable_server() -> None:
    readiness = app.inspect_ollama_readiness(
        base_url="http://localhost:11434",
        model="llama3.1",
        client_factory=lambda **kwargs: _StubOllamaClient(
            error=ModelInvocationError("connection refused")
        ),
    )

    assert readiness.ok is False
    assert readiness.reachable is False
    assert "not reachable" in readiness.headline.lower()
    assert "fake" in readiness.error_message.lower()


def test_inspect_ollama_readiness_reports_missing_model() -> None:
    readiness = app.inspect_ollama_readiness(
        base_url="http://localhost:11434",
        model="llama3.1",
        client_factory=lambda **kwargs: _StubOllamaClient(models=["qwen2.5:14b", "mistral"]),
    )

    assert readiness.ok is False
    assert readiness.reachable is True
    assert readiness.available_models == ["qwen2.5:14b", "mistral"]
    assert "not installed" in readiness.summary.lower()
    assert "ollama pull llama3.1" in readiness.error_message


def test_inspect_ollama_readiness_reports_ready_model() -> None:
    readiness = app.inspect_ollama_readiness(
        base_url="http://localhost:11434",
        model="llama3.1",
        client_factory=lambda **kwargs: _StubOllamaClient(models=["llama3.1", "qwen2.5:14b"]),
    )

    assert readiness.ok is True
    assert readiness.reachable is True
    assert readiness.configured_model == "llama3.1"
    assert "looks ready" in readiness.headline.lower()
