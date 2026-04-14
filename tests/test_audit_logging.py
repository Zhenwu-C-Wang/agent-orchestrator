from __future__ import annotations

import json

import pytest

from main import build_supervisor


def test_successful_run_writes_audit_record(tmp_path) -> None:
    supervisor = build_supervisor(
        runner_name="fake",
        enable_review=True,
        audit_dir=str(tmp_path),
        cache_dir=str(tmp_path / "cache"),
    )

    result = supervisor.run("How should I define worker schemas before adding more workers?")

    records = list(tmp_path.glob("*.json"))
    assert len(records) == 1

    payload = json.loads(records[0].read_text(encoding="utf-8"))
    assert payload["status"] == "completed"
    assert payload["question"] == result.question
    assert payload["metadata"]["runner"] == "fake"
    assert payload["metadata"]["review_enabled"] is True
    assert payload["metadata"]["cache_enabled"] is True
    assert payload["result"]["review"]["consistent"] is True
    assert [trace["worker_name"] for trace in payload["traces"]] == ["research", "writer", "review"]
    assert all(trace["metadata"]["cache_hit"] is False for trace in payload["traces"])
    assert all(trace["metadata"]["cache_status"] == "miss" for trace in payload["traces"])


def test_failed_run_writes_failure_audit_record(tmp_path) -> None:
    supervisor = build_supervisor(
        runner_name="fake",
        audit_dir=str(tmp_path),
    )

    class BrokenWorker:
        def run(self, task) -> None:
            raise RuntimeError("writer exploded")

    supervisor.workers["writer"] = BrokenWorker()

    with pytest.raises(RuntimeError, match="writer exploded"):
        supervisor.run("How should I bootstrap a supervisor-worker agent system?")

    records = list(tmp_path.glob("*.json"))
    assert len(records) == 1

    payload = json.loads(records[0].read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["error"] == "writer exploded"
    assert payload["result"] is None
    assert [trace["worker_name"] for trace in payload["traces"]] == ["research", "writer"]
