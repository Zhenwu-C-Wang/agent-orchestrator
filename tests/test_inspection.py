from __future__ import annotations

from orchestrator.inspection import build_plan_guidance, build_result_overview
from orchestrator.planner import TaskPlanner

from main import build_supervisor


def test_plan_guidance_warns_when_question_contains_url_but_inline_discovery_is_disabled() -> None:
    planner = TaskPlanner(enable_review=False, allow_question_urls=False)
    plan = planner.build_plan("Summarize the report at https://example.com/status.")

    guidance = build_plan_guidance(
        plan,
        question="Summarize the report at https://example.com/status.",
    )

    assert guidance.headline == "Research Route"
    assert any("inline URL discovery is disabled" in warning for warning in guidance.warnings)


def test_plan_guidance_describes_hybrid_route_for_advisory_context_requests(tmp_path) -> None:
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("quarter,revenue\nQ1,10\nQ2,12\n", encoding="utf-8")

    planner = TaskPlanner()
    plan = planner.build_plan(
        "Analyze this dataset and recommend what we should prioritize next.",
        context_files=[str(csv_path)],
    )

    guidance = build_plan_guidance(
        plan,
        question="Analyze this dataset and recommend what we should prioritize next.",
    )

    assert guidance.headline == "Hybrid Advisory Route"
    assert "broadest bounded route" in guidance.summary
    assert any("Research frames the question" in item for item in guidance.guidance)


def test_result_overview_highlights_hybrid_workflow_and_suggests_review(tmp_path) -> None:
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("quarter,revenue\nQ1,10\nQ2,20\n", encoding="utf-8")

    supervisor = build_supervisor(runner_name="fake")
    result = supervisor.run_with_context(
        "Analyze this dataset and recommend what we should prioritize next.",
        context_files=[str(csv_path)],
    )

    overview = build_result_overview(result)

    assert overview.headline == "Hybrid Advisory Route Inspection"
    assert any("Research captured" in item for item in overview.highlights)
    assert any("Analysis captured" in item for item in overview.highlights)
    assert any("Enable the review stage" in item for item in overview.next_actions)
    assert any(metric.label == "Tools" and metric.value == "3" for metric in overview.metrics)
