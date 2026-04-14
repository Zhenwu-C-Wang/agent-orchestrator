import pytest

from models.model_runner import ModelRequest
from models.ollama_runner import OllamaModelRunner, extract_json_payload
from schemas.result_schema import ResearchResult
from tools.retry import RetryPolicy


def test_extract_json_payload_from_markdown_fence() -> None:
    raw_text = """
    Here is the result:

    ```json
    {"question":"q","summary":"s","key_points":[],"caveats":[],"sources":[]}
    ```
    """

    payload = extract_json_payload(raw_text)

    assert payload == '{"question":"q","summary":"s","key_points":[],"caveats":[],"sources":[]}'


class StubOllamaClient:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls = 0

    def generate(self, **kwargs) -> str:
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _request() -> ModelRequest:
    return ModelRequest(
        task_type="research",
        system_prompt="system",
        user_prompt="user",
    )


def _research_json(summary: str = "s") -> str:
    return (
        '{"question":"q","summary":"'
        + summary
        + '","key_points":[],"caveats":[],"sources":[]}'
    )


def test_ollama_runner_retries_after_client_error() -> None:
    client = StubOllamaClient([RuntimeError("temporary failure"), _research_json("ok")])
    runner = OllamaModelRunner(
        model="test-model",
        client=client,
        retry_policy=RetryPolicy(max_retries=1, backoff_seconds=0),
    )

    result = runner.generate_structured(_request(), ResearchResult)

    assert result.summary == "ok"
    assert client.calls == 2


def test_ollama_runner_retries_after_invalid_json() -> None:
    client = StubOllamaClient(["not valid json", _research_json("recovered")])
    runner = OllamaModelRunner(
        model="test-model",
        client=client,
        retry_policy=RetryPolicy(max_retries=1, backoff_seconds=0),
    )

    result = runner.generate_structured(_request(), ResearchResult)

    assert result.summary == "recovered"
    assert client.calls == 2


def test_ollama_runner_raises_after_retry_exhaustion() -> None:
    client = StubOllamaClient([RuntimeError("still failing"), RuntimeError("still failing again")])
    runner = OllamaModelRunner(
        model="test-model",
        client=client,
        retry_policy=RetryPolicy(max_retries=1, backoff_seconds=0),
    )

    with pytest.raises(RuntimeError, match="after 2 attempts"):
        runner.generate_structured(_request(), ResearchResult)

    assert client.calls == 2
