from __future__ import annotations

import json

import pytest

from main import build_supervisor
from tools.errors import ToolExecutionError


def test_successful_run_writes_audit_record(tmp_path) -> None:
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("quarter,revenue\nQ1,10\nQ2,20\n", encoding="utf-8")
    supervisor = build_supervisor(
        runner_name="fake",
        enable_review=True,
        audit_dir=str(tmp_path),
        cache_dir=str(tmp_path / "cache"),
    )

    result = supervisor.run_with_context(
        "Analyze this dataset and summarize the changes.",
        context_files=[str(csv_path)],
    )

    records = list(tmp_path.glob("*.json"))
    assert len(records) == 1

    payload = json.loads(records[0].read_text(encoding="utf-8"))
    assert payload["status"] == "completed"
    assert payload["question"] == result.question
    assert payload["metadata"]["runner"] == "fake"
    assert payload["metadata"]["review_enabled"] is True
    assert payload["metadata"]["cache_enabled"] is True
    assert payload["result"]["review"]["consistent"] is True
    assert payload["result"]["tool_invocations"][0]["tool_name"] == "local_file_context"
    assert payload["result"]["tool_invocations"][1]["tool_name"] == "csv_analysis"
    assert [trace["worker_name"] for trace in payload["traces"]] == ["analysis", "writer", "review"]
    assert all(trace["metadata"]["cache_hit"] is False for trace in payload["traces"])
    assert all(trace["metadata"]["cache_status"] == "miss" for trace in payload["traces"])
    assert payload["traces"][0]["metadata"]["tool_invocation_count"] == 2


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


def test_tool_failure_writes_failure_audit_record(tmp_path) -> None:
    supervisor = build_supervisor(
        runner_name="fake",
        audit_dir=str(tmp_path),
    )

    with pytest.raises(ToolExecutionError, match="http_fetch failed"):
        supervisor.run_with_context(
            "Summarize the most important findings from this webpage.",
            context_urls=["http://127.0.0.1:1/context"],
        )

    records = list(tmp_path.glob("*.json"))
    assert len(records) == 1

    payload = json.loads(records[0].read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert "http_fetch failed" in payload["error"]
    assert payload["result"] is None
    assert [trace["worker_name"] for trace in payload["traces"]] == ["analysis"]
    assert payload["traces"][0]["status"] == "failed"
    assert payload["traces"][0]["metadata"]["tool_invocation_count"] == 1
    assert payload["traces"][0]["metadata"]["tool_invocations"][0]["status"] == "failed"
