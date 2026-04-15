from main import build_supervisor


def test_supervisor_can_run_optional_review_stage() -> None:
    supervisor = build_supervisor(runner_name="fake", enable_review=True)

    result = supervisor.run("What risks appear when a supervisor directly writes the final answer?")

    assert result.review is not None
    assert result.review.consistent is True
    assert [trace.worker_name for trace in result.traces] == ["research", "writer", "review"]


def test_supervisor_can_review_hybrid_workflow(tmp_path) -> None:
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("quarter,revenue\nQ1,10\nQ2,20\n", encoding="utf-8")

    supervisor = build_supervisor(runner_name="fake", enable_review=True)

    result = supervisor.run_with_context(
        "Analyze this dataset and recommend what we should prioritize next.",
        context_files=[str(csv_path)],
    )

    assert result.review is not None
    assert result.review.consistent is True
    assert [trace.worker_name for trace in result.traces] == ["research", "analysis", "writer", "review"]
