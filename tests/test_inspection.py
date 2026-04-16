from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from schemas.acceptance_schema import AcceptanceCaseComparison, AcceptanceCaseResult, AcceptanceRecord, AcceptanceReport
from orchestrator.inspection import (
    build_acceptance_overview,
    build_acceptance_case_detail,
    build_acceptance_export_payload,
    build_cache_overview,
    build_cache_entry_detail,
    build_cache_export_payload,
    build_plan_guidance,
    build_result_overview,
    format_acceptance_export_markdown,
    format_cache_export_markdown,
)
from orchestrator.planner import TaskPlanner
from tools.acceptance import AcceptanceLogger, AcceptanceStore
from tools.cache import StructuredResultCache
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


def test_plan_guidance_warns_when_comparison_intent_has_only_one_context(tmp_path) -> None:
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("quarter,revenue\nQ1,10\nQ2,12\n", encoding="utf-8")

    planner = TaskPlanner()
    plan = planner.build_plan(
        "Compare this dataset and summarize the most important differences.",
        context_files=[str(csv_path)],
    )

    guidance = build_plan_guidance(
        plan,
        question="Compare this dataset and summarize the most important differences.",
    )

    assert guidance.headline == "Analysis Route"
    assert any("Attach at least two files or URLs" in warning for warning in guidance.warnings)


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


def test_result_overview_highlights_comparison_workflow(tmp_path) -> None:
    current = tmp_path / "current.csv"
    baseline = tmp_path / "baseline.csv"
    current.write_text("quarter,revenue\nQ1,10\nQ2,20\n", encoding="utf-8")
    baseline.write_text("quarter,revenue\nQ1,8\nQ2,12\n", encoding="utf-8")

    supervisor = build_supervisor(runner_name="fake")
    result = supervisor.run_with_context(
        "Compare these datasets and summarize the most important differences.",
        context_files=[str(current), str(baseline)],
    )

    overview = build_result_overview(result)

    assert overview.headline == "Comparison Route Inspection"
    assert any("Comparison captured" in item for item in overview.highlights)
    assert any("broader hybrid comparison route" in item for item in overview.next_actions)


def test_acceptance_overview_highlights_regressions(tmp_path) -> None:
    logger = AcceptanceLogger(tmp_path, metadata={"source": "test"})
    logger.record_report(
        AcceptanceReport(
            runner="fake",
            model=None,
            enable_review=False,
            total_cases=2,
            passed_cases=2,
            failed_cases=0,
            case_results=[
                AcceptanceCaseResult(
                    question="How should I bootstrap a supervisor-worker agent system?",
                    passed=True,
                    duration_ms=5,
                ),
                AcceptanceCaseResult(
                    question="What risks appear when a supervisor directly writes the final answer?",
                    passed=True,
                    duration_ms=5,
                ),
            ],
        )
    )
    logger.record_report(
        AcceptanceReport(
            runner="fake",
            model=None,
            enable_review=False,
            total_cases=2,
            passed_cases=1,
            failed_cases=1,
            case_results=[
                AcceptanceCaseResult(
                    question="How should I bootstrap a supervisor-worker agent system?",
                    passed=False,
                    duration_ms=7,
                    errors=["writer drifted from research"],
                    warnings=["review gap"],
                ),
                AcceptanceCaseResult(
                    question="What risks appear when a supervisor directly writes the final answer?",
                    passed=True,
                    duration_ms=5,
                ),
            ],
        )
    )

    store = AcceptanceStore(tmp_path)
    current = store.latest_record()
    assert current is not None
    baseline = store.previous_record(current.run_id)
    assert baseline is not None

    overview = build_acceptance_overview(
        current,
        comparison=store.compare_records(current, baseline),
    )

    assert overview.headline == "Acceptance Report"
    assert any(metric.label == "Passed" and metric.value == "1/2" for metric in overview.metrics)
    assert any("regressions" in warning.lower() for warning in overview.warnings)
    assert overview.changed_case_rows[0]["regression"] is True


def test_cache_overview_warns_about_expired_entries(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    supervisor = build_supervisor(
        runner_name="fake",
        enable_review=True,
        cache_dir=str(cache_dir),
    )
    supervisor.run("How should I bootstrap a supervisor-worker system?")

    aged_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    for path in cache_dir.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["created_at"] = aged_timestamp
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    cache = StructuredResultCache(cache_dir, max_age_seconds=60)
    overview = build_cache_overview(
        cache.summarize_cache(),
        recent_entries=[cache.summarize_entry(entry) for entry in cache.list_entries(limit=5)],
    )

    assert overview.headline == "Cache Health"
    assert any(metric.label == "Expired" and metric.value == "3" for metric in overview.metrics)
    assert any("Expired cache entries are present" in warning for warning in overview.warnings)


def test_acceptance_case_detail_surfaces_result_and_regression(tmp_path) -> None:
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("quarter,revenue\nQ1,10\nQ2,20\n", encoding="utf-8")

    supervisor = build_supervisor(runner_name="fake")
    result = supervisor.run_with_context(
        "Analyze this dataset and recommend what we should prioritize next.",
        context_files=[str(csv_path)],
    )
    case = AcceptanceCaseResult(
        question=result.question,
        passed=False,
        duration_ms=25,
        errors=["writer drifted from evidence"],
        warnings=["manual regression flag"],
        trace_order=[trace.worker_name for trace in result.traces],
        result=result,
    )
    comparison = AcceptanceCaseComparison(
        question=result.question,
        current_present=True,
        baseline_present=True,
        current_passed=False,
        baseline_passed=True,
        changed=True,
        regression=True,
        improvement=False,
        current_error_count=1,
        baseline_error_count=0,
        current_warning_count=1,
        baseline_warning_count=0,
        duration_ms_delta=5,
    )

    detail = build_acceptance_case_detail(case, case_comparison=comparison)

    assert detail.headline == "Acceptance Case Detail"
    assert any(metric.label == "Passed" and metric.value == "No" for metric in detail.metrics)
    assert any("regressed" in warning.lower() for warning in detail.warnings)
    assert detail.result_overview is not None
    assert detail.trace_rows[0]["worker"] == "research"
    assert detail.tool_rows[0]["tool_name"] == "local_file_context"
    assert detail.final_answer_preview is not None


def test_cache_entry_detail_surfaces_preview_and_expiry(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    supervisor = build_supervisor(
        runner_name="fake",
        enable_review=True,
        cache_dir=str(cache_dir),
    )
    supervisor.run("How should I bootstrap a supervisor-worker system?")

    cache = StructuredResultCache(cache_dir, max_age_seconds=60)
    entry = cache.list_entries(limit=1)[0]
    detail = build_cache_entry_detail(entry, expired=False)

    assert detail.headline == "Cache Entry Detail"
    assert any(metric.label == "Response" for metric in detail.metrics)
    assert detail.response_preview is not None
    assert any(row["key"] == "task_type" for row in detail.metadata_rows)


def test_acceptance_export_payload_and_markdown_include_selected_case(tmp_path) -> None:
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("quarter,revenue\nQ1,10\nQ2,20\n", encoding="utf-8")

    supervisor = build_supervisor(runner_name="fake")
    result = supervisor.run_with_context(
        "Analyze this dataset and recommend what we should prioritize next.",
        context_files=[str(csv_path)],
    )
    case = AcceptanceCaseResult(
        question=result.question,
        passed=True,
        duration_ms=25,
        trace_order=[trace.worker_name for trace in result.traces],
        result=result,
    )
    record = AcceptanceRecord(
        run_id="acceptance-run-1",
        status="completed",
        created_at="2026-04-16T00:00:00+00:00",
        report=AcceptanceReport(
            runner="fake",
            model=None,
            enable_review=False,
            total_cases=1,
            passed_cases=1,
            failed_cases=0,
            case_results=[case],
        ),
    )

    payload = build_acceptance_export_payload(record, selected_case=case)
    markdown = format_acceptance_export_markdown(record, selected_case=case)

    assert payload["overview"]["headline"] == "Acceptance Report"
    assert payload["selected_case"]["question"] == result.question
    assert payload["selected_case_detail"]["headline"] == "Acceptance Case Detail"
    assert "## Selected Case" in markdown
    assert result.question in markdown


def test_cache_export_payload_and_markdown_include_selected_entry(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    supervisor = build_supervisor(
        runner_name="fake",
        enable_review=True,
        cache_dir=str(cache_dir),
    )
    supervisor.run("How should I bootstrap a supervisor-worker system?")

    cache = StructuredResultCache(cache_dir, max_age_seconds=60)
    entries = cache.list_entries(limit=5)
    entry = entries[0]
    recent_entries = [cache.summarize_entry(item) for item in entries]

    payload = build_cache_export_payload(
        cache.summarize_cache(),
        recent_entries=recent_entries,
        selected_entry=entry,
        expired=False,
    )
    markdown = format_cache_export_markdown(
        cache.summarize_cache(),
        recent_entries=recent_entries,
        selected_entry=entry,
        expired=False,
    )

    assert payload["overview"]["headline"] == "Cache Health"
    assert payload["selected_entry"]["cache_key"] == entry.cache_key
    assert payload["selected_entry_detail"]["headline"] == "Cache Entry Detail"
    assert "## Selected Entry" in markdown
    assert entry.cache_key in markdown
