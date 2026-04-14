from main import build_supervisor


def test_supervisor_runs_the_closed_loop_workflow() -> None:
    supervisor = build_supervisor(runner_name="fake")

    result = supervisor.run("How should I bootstrap a supervisor-worker agent system?")

    assert result.research.summary.startswith("Research summary for:")
    assert "synchronous" in result.final_answer.answer.lower()
    assert [trace.worker_name for trace in result.traces] == ["research", "writer"]
    assert all(trace.status == "completed" for trace in result.traces)
