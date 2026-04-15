from main import build_supervisor


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

    result = supervisor.run(f"Analyze `{csv_path}` and summarize the most important changes.")

    assert result.analysis is not None
    assert len(result.tool_invocations) == 2
    assert [invocation.tool_name for invocation in result.tool_invocations] == [
        "local_file_context",
        "csv_analysis",
    ]
    assert result.workflow_plan.metadata["has_local_files"] is True
    assert result.traces[0].metadata["tool_invocation_count"] == 2
    assert "sales.csv" in result.analysis.summary
