from __future__ import annotations

from models.cached_runner import CachedModelRunner
from models.model_runner import ModelRequest
from schemas.result_schema import ResearchResult
from tools.cache import StructuredResultCache


class CountingRunner:
    def __init__(self, summary: str = "cached-summary") -> None:
        self.summary = summary
        self.calls = 0

    def generate_structured(self, request: ModelRequest, response_model):
        self.calls += 1
        return response_model.model_validate(
            {
                "question": request.payload["question"],
                "summary": self.summary,
                "key_points": [],
                "caveats": [],
                "sources": [],
            }
        )


def _request(question: str = "How should I define worker schemas?") -> ModelRequest:
    return ModelRequest(
        task_type="research",
        system_prompt="system",
        user_prompt="user",
        payload={"question": question},
    )


def test_cached_runner_hits_cache_for_repeated_request(tmp_path) -> None:
    cache = StructuredResultCache(tmp_path)
    inner = CountingRunner(summary="first")
    runner = CachedModelRunner(
        runner=inner,
        cache=cache,
        namespace={"runner": "ollama", "model": "qwen2.5:14b"},
    )

    first = runner.generate_structured(_request(), ResearchResult)
    second = runner.generate_structured(_request(), ResearchResult)

    assert first.summary == "first"
    assert second.summary == "first"
    assert inner.calls == 1
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_cached_runner_reuses_disk_cache_across_instances(tmp_path) -> None:
    cache = StructuredResultCache(tmp_path)
    first_inner = CountingRunner(summary="persisted")
    first_runner = CachedModelRunner(
        runner=first_inner,
        cache=cache,
        namespace={"runner": "ollama", "model": "qwen2.5:14b"},
    )
    first_runner.generate_structured(_request(), ResearchResult)

    second_inner = CountingRunner(summary="should-not-run")
    second_runner = CachedModelRunner(
        runner=second_inner,
        cache=StructuredResultCache(tmp_path),
        namespace={"runner": "ollama", "model": "qwen2.5:14b"},
    )
    result = second_runner.generate_structured(_request(), ResearchResult)

    assert result.summary == "persisted"
    assert first_inner.calls == 1
    assert second_inner.calls == 0


def test_cached_runner_misses_when_namespace_changes(tmp_path) -> None:
    cache = StructuredResultCache(tmp_path)
    first_inner = CountingRunner(summary="model-a")
    first_runner = CachedModelRunner(
        runner=first_inner,
        cache=cache,
        namespace={"runner": "ollama", "model": "model-a"},
    )
    first_runner.generate_structured(_request(), ResearchResult)

    second_inner = CountingRunner(summary="model-b")
    second_runner = CachedModelRunner(
        runner=second_inner,
        cache=cache,
        namespace={"runner": "ollama", "model": "model-b"},
    )
    result = second_runner.generate_structured(_request(), ResearchResult)

    assert result.summary == "model-b"
    assert first_inner.calls == 1
    assert second_inner.calls == 1
    assert len(list(tmp_path.glob("*.json"))) == 2
