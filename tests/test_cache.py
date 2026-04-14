from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

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


def _age_cache_entry(cache: StructuredResultCache, cache_key: str, *, age_seconds: int) -> None:
    path = cache.path_for(cache_key)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["created_at"] = (datetime.now(timezone.utc) - timedelta(seconds=age_seconds)).isoformat()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_cached_runner_hits_cache_for_repeated_request(tmp_path) -> None:
    cache = StructuredResultCache(tmp_path)
    inner = CountingRunner(summary="first")
    runner = CachedModelRunner(
        runner=inner,
        cache=cache,
        namespace={"runner": "ollama", "model": "qwen2.5:14b"},
    )

    first = runner.generate_structured(_request(), ResearchResult)
    first_metadata = runner.get_last_invocation_metadata()
    second = runner.generate_structured(_request(), ResearchResult)
    second_metadata = runner.get_last_invocation_metadata()

    assert first.summary == "first"
    assert second.summary == "first"
    assert inner.calls == 1
    assert len(list(tmp_path.glob("*.json"))) == 1
    assert first_metadata["cache_hit"] is False
    assert first_metadata["cache_status"] == "miss"
    assert second_metadata["cache_hit"] is True
    assert second_metadata["cache_status"] == "hit"
    assert first_metadata["cache_key"] == second_metadata["cache_key"]
    assert second_metadata["attempt_count"] == 0


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


def test_structured_result_cache_expires_old_entries_on_lookup(tmp_path) -> None:
    cache = StructuredResultCache(tmp_path, max_age_seconds=60)
    request = _request()
    cache_key = cache.build_key(
        namespace={"runner": "ollama", "model": "qwen2.5:14b"},
        request=request,
        response_model=ResearchResult,
    )
    cache.set(
        cache_key=cache_key,
        metadata={"runner": "ollama"},
        response=ResearchResult.model_validate(
            {
                "question": request.payload["question"],
                "summary": "stale",
                "key_points": [],
                "caveats": [],
                "sources": [],
            }
        ),
    )
    _age_cache_entry(cache, cache_key, age_seconds=120)

    lookup = cache.lookup(cache_key=cache_key, response_model=ResearchResult)

    assert lookup.status == "expired"
    assert lookup.response is None
    assert not cache.path_for(cache_key).exists()


def test_cached_runner_refreshes_expired_entry(tmp_path) -> None:
    cache = StructuredResultCache(tmp_path, max_age_seconds=60)
    inner = CountingRunner(summary="fresh")
    runner = CachedModelRunner(
        runner=inner,
        cache=cache,
        namespace={"runner": "ollama", "model": "qwen2.5:14b"},
    )
    runner.generate_structured(_request(), ResearchResult)
    first_cache_key = runner.get_last_invocation_metadata()["cache_key"]
    _age_cache_entry(cache, first_cache_key, age_seconds=120)
    inner.summary = "refreshed"

    result = runner.generate_structured(_request(), ResearchResult)
    metadata = runner.get_last_invocation_metadata()

    assert result.summary == "refreshed"
    assert inner.calls == 2
    assert metadata["cache_hit"] is False
    assert metadata["cache_status"] == "expired"


def test_supervisor_traces_expose_cache_hit_metadata(tmp_path) -> None:
    from main import build_supervisor

    supervisor = build_supervisor(
        runner_name="fake",
        enable_review=True,
        cache_dir=str(tmp_path),
    )

    first_result = supervisor.run("How should I bootstrap a supervisor-worker system?")
    second_result = supervisor.run("How should I bootstrap a supervisor-worker system?")

    assert all(trace.metadata["cache_enabled"] is True for trace in first_result.traces)
    assert all(trace.metadata["cache_hit"] is False for trace in first_result.traces)
    assert all(trace.metadata["cache_status"] == "miss" for trace in first_result.traces)
    assert all("cache_key" in trace.metadata for trace in first_result.traces)
    assert all(trace.metadata["cache_hit"] is True for trace in second_result.traces)
    assert all(trace.metadata["cache_status"] == "hit" for trace in second_result.traces)
