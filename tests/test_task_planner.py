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
