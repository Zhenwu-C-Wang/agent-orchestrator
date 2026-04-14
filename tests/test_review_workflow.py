from main import build_supervisor


def test_supervisor_can_run_optional_review_stage() -> None:
    supervisor = build_supervisor(runner_name="fake", enable_review=True)

    result = supervisor.run("What risks appear when a supervisor directly writes the final answer?")

    assert result.review is not None
    assert result.review.consistent is True
    assert [trace.worker_name for trace in result.traces] == ["research", "writer", "review"]
