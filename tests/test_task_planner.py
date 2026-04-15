from orchestrator.planner import TaskPlanner


def test_task_planner_uses_research_workflow_for_general_questions() -> None:
    plan = TaskPlanner().build_plan("How should I bootstrap a supervisor-worker agent system?")

    assert plan.workflow_name == "research_then_write"
    assert [step.worker_name for step in plan.steps] == ["research", "writer"]
    assert plan.metadata["question_type"] == "research"


def test_task_planner_uses_analysis_workflow_for_data_requests() -> None:
    plan = TaskPlanner(enable_review=True).build_plan(
        "Analyze this dataset and summarize the biggest changes."
    )

    assert plan.workflow_name == "analysis_then_write"
    assert [step.worker_name for step in plan.steps] == ["analysis", "writer", "review"]
    assert plan.metadata["question_type"] == "analysis"


def test_task_planner_ignores_inline_file_references_by_default(tmp_path) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("# Findings\n- keep a structured trace\n", encoding="utf-8")

    plan = TaskPlanner().build_plan(f"Summarize `{notes}` for me.")

    assert plan.workflow_name == "research_then_write"
    assert [step.worker_name for step in plan.steps] == ["research", "writer"]
    assert plan.metadata["has_local_files"] is False


def test_task_planner_uses_analysis_workflow_when_inline_file_discovery_is_enabled(tmp_path) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("# Findings\n- keep a structured trace\n", encoding="utf-8")

    plan = TaskPlanner(allow_question_file_paths=True).build_plan(f"Summarize `{notes}` for me.")

    assert plan.workflow_name == "analysis_then_write"
    assert [step.worker_name for step in plan.steps] == ["analysis", "writer"]
    assert plan.metadata["has_local_files"] is True
    assert plan.metadata["discovered_context_file_count"] == 1


def test_task_planner_uses_analysis_workflow_for_explicit_context_files(tmp_path) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("# Findings\n- keep a structured trace\n", encoding="utf-8")

    plan = TaskPlanner().build_plan(
        "Summarize this file for me.",
        context_files=[str(notes)],
    )

    assert plan.workflow_name == "analysis_then_write"
    assert [step.worker_name for step in plan.steps] == ["analysis", "writer"]
    assert plan.metadata["has_local_files"] is True
    assert plan.metadata["context_file_count"] == 1


def test_task_planner_uses_analysis_workflow_for_explicit_context_urls() -> None:
    plan = TaskPlanner().build_plan(
        "Summarize this webpage for me.",
        context_urls=["https://example.com/report"],
    )

    assert plan.workflow_name == "analysis_then_write"
    assert [step.worker_name for step in plan.steps] == ["analysis", "writer"]
    assert plan.metadata["has_context_urls"] is True
    assert plan.metadata["context_url_count"] == 1


def test_task_planner_uses_hybrid_workflow_for_advisory_requests_with_context_files(tmp_path) -> None:
    notes = tmp_path / "metrics.csv"
    notes.write_text("quarter,revenue\nQ1,10\nQ2,20\n", encoding="utf-8")

    plan = TaskPlanner().build_plan(
        "Analyze this dataset and recommend what we should prioritize next.",
        context_files=[str(notes)],
    )

    assert plan.workflow_name == "research_then_analysis_then_write"
    assert [step.worker_name for step in plan.steps] == ["research", "analysis", "writer"]
    assert plan.metadata["question_type"] == "hybrid"
    assert plan.metadata["requires_research_support"] is True


def test_task_planner_uses_comparison_workflow_for_compare_requests_with_multiple_contexts(tmp_path) -> None:
    current = tmp_path / "current.csv"
    baseline = tmp_path / "baseline.csv"
    current.write_text("quarter,revenue\nQ1,10\nQ2,20\n", encoding="utf-8")
    baseline.write_text("quarter,revenue\nQ1,8\nQ2,12\n", encoding="utf-8")

    plan = TaskPlanner().build_plan(
        "Compare these datasets and summarize the most important differences.",
        context_files=[str(current), str(baseline)],
    )

    assert plan.workflow_name == "comparison_then_write"
    assert [step.worker_name for step in plan.steps] == ["comparison", "writer"]
    assert plan.metadata["question_type"] == "comparison"
    assert plan.metadata["requires_context_comparison"] is True


def test_task_planner_uses_hybrid_comparison_workflow_for_advisory_compare_requests(tmp_path) -> None:
    current = tmp_path / "current.csv"
    baseline = tmp_path / "baseline.csv"
    current.write_text("quarter,revenue\nQ1,10\nQ2,20\n", encoding="utf-8")
    baseline.write_text("quarter,revenue\nQ1,8\nQ2,12\n", encoding="utf-8")

    plan = TaskPlanner().build_plan(
        "Compare these datasets and recommend which one we should prioritize next.",
        context_files=[str(current), str(baseline)],
    )

    assert plan.workflow_name == "research_then_comparison_then_write"
    assert [step.worker_name for step in plan.steps] == ["research", "comparison", "writer"]
    assert plan.metadata["question_type"] == "hybrid_comparison"
    assert plan.metadata["requires_context_comparison"] is True
