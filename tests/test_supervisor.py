import pytest

from main import build_supervisor
from tools.errors import ToolExecutionError

from .http_fixtures import install_http_fetch_stub


def test_supervisor_runs_the_closed_loop_workflow() -> None:
    supervisor = build_supervisor(runner_name="fake")

    result = supervisor.run("How should I bootstrap a supervisor-worker agent system?")

    assert result.research.summary.startswith("Research summary for:")
    assert result.analysis is None
    assert "synchronous" in result.final_answer.answer.lower()
    assert result.workflow_plan.workflow_name == "research_then_write"
    assert [trace.worker_name for trace in result.traces] == ["research", "writer"]
    assert all(trace.status == "completed" for trace in result.traces)


def test_supervisor_routes_analysis_requests_to_analysis_worker() -> None:
    supervisor = build_supervisor(runner_name="fake")

    result = supervisor.run("Analyze this CSV dataset and summarize the most important changes.")

    assert result.research is None
    assert result.analysis is not None
    assert result.analysis.summary.startswith("Analysis summary for:")
    assert result.workflow_plan.workflow_name == "analysis_then_write"
    assert [trace.worker_name for trace in result.traces] == ["analysis", "writer"]


def test_supervisor_records_tool_invocations_for_local_csv_analysis(tmp_path) -> None:
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("month,revenue\nJan,10\nFeb,12\nMar,15\n", encoding="utf-8")

    supervisor = build_supervisor(runner_name="fake")

    result = supervisor.run_with_context(
        "Analyze this dataset and summarize the most important changes.",
        context_files=[str(csv_path)],
    )

    assert result.analysis is not None
    assert len(result.tool_invocations) == 2
    assert [invocation.tool_name for invocation in result.tool_invocations] == [
        "local_file_context",
        "csv_analysis",
    ]
    assert result.workflow_plan.metadata["has_local_files"] is True
    assert result.traces[0].metadata["tool_invocation_count"] == 2
    assert "sales.csv" in result.analysis.summary


def test_supervisor_can_use_inline_context_files_when_enabled(tmp_path) -> None:
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("month,revenue\nJan,10\nFeb,12\nMar,15\n", encoding="utf-8")

    supervisor = build_supervisor(
        runner_name="fake",
        allow_inline_context_files=True,
    )

    result = supervisor.run(f"Analyze `{csv_path}` and summarize the most important changes.")

    assert result.analysis is not None
    assert [invocation.tool_name for invocation in result.tool_invocations] == [
        "local_file_context",
        "csv_analysis",
    ]


def test_supervisor_uses_explicit_context_files_without_question_path(tmp_path) -> None:
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("month,revenue\nJan,10\nFeb,12\nMar,15\n", encoding="utf-8")

    supervisor = build_supervisor(runner_name="fake")

    result = supervisor.run_with_context(
        "Summarize the most important changes in this data.",
        context_files=[str(csv_path)],
    )

    assert result.workflow_plan.workflow_name == "analysis_then_write"
    assert result.workflow_plan.metadata["context_file_count"] == 1
    assert [invocation.tool_name for invocation in result.tool_invocations] == [
        "local_file_context",
        "csv_analysis",
    ]


def test_supervisor_records_tool_invocations_for_local_json_analysis(tmp_path) -> None:
    json_path = tmp_path / "metrics.json"
    json_path.write_text(
        (
            '[{"quarter":"2024-Q1","revenue":120,"active_users":400,"churn_rate":0.08},'
            '{"quarter":"2024-Q2","revenue":135,"active_users":430,"churn_rate":0.07}]'
        ),
        encoding="utf-8",
    )

    supervisor = build_supervisor(runner_name="fake")

    result = supervisor.run_with_context(
        "Analyze this JSON snapshot and summarize the most important changes.",
        context_files=[str(json_path)],
    )

    assert result.analysis is not None
    assert [invocation.tool_name for invocation in result.tool_invocations] == [
        "local_file_context",
        "json_analysis",
    ]
    assert result.traces[0].metadata["tool_invocation_count"] == 2
    assert "metrics.json" in result.analysis.summary


def test_supervisor_records_http_tool_invocations_for_context_urls(monkeypatch) -> None:
    supervisor = build_supervisor(runner_name="fake")
    url = install_http_fetch_stub(monkeypatch, body="service status is healthy")

    result = supervisor.run_with_context(
        "Summarize the most important findings from this webpage.",
        context_urls=[url],
    )

    assert result.analysis is not None
    assert result.workflow_plan.workflow_name == "analysis_then_write"
    assert result.workflow_plan.metadata["context_url_count"] == 1
    assert [invocation.tool_name for invocation in result.tool_invocations] == ["http_fetch"]
    assert url in result.analysis.summary


def test_supervisor_fails_when_context_url_fetch_fails() -> None:
    supervisor = build_supervisor(runner_name="fake")

    with pytest.raises(ToolExecutionError, match="http_fetch failed"):
        supervisor.run_with_context(
            "Summarize the most important findings from this webpage.",
            context_urls=["http://127.0.0.1:1/context"],
        )
