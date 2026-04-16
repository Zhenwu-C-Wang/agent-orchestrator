from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from schemas.acceptance_schema import AcceptanceCaseComparison, AcceptanceCaseResult, AcceptanceComparison, AcceptanceRecord
from schemas.cache_schema import CacheEntry
from schemas.result_schema import WorkflowResult
from schemas.task_schema import WorkflowPlan

_URL_PATTERN = re.compile(r"https?://[^\s`]+")
_FILE_LIKE_PATTERN = re.compile(
    r"`[^`]+\.(?:csv|txt|md|json|py|yaml|yml)`|"
    r"(?:\./|\.\./|/)[^\s,;:]+|"
    r"[A-Za-z0-9_.\-/]+\.(?:csv|txt|md|json|py|yaml|yml)"
)


@dataclass(frozen=True)
class InspectionMetric:
    label: str
    value: str


@dataclass(frozen=True)
class PlanGuidance:
    headline: str
    summary: str
    metrics: list[InspectionMetric] = field(default_factory=list)
    guidance: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    step_rows: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ResultOverview:
    headline: str
    summary: str
    metrics: list[InspectionMetric] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AcceptanceOverview:
    headline: str
    summary: str
    metrics: list[InspectionMetric] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    changed_case_rows: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class CacheOverview:
    headline: str
    summary: str
    metrics: list[InspectionMetric] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    recent_entry_rows: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class AcceptanceCaseDetail:
    headline: str
    summary: str
    metrics: list[InspectionMetric] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    trace_rows: list[dict[str, Any]] = field(default_factory=list)
    tool_rows: list[dict[str, Any]] = field(default_factory=list)
    final_answer_preview: str | None = None
    result_overview: ResultOverview | None = None


@dataclass(frozen=True)
class CacheEntryDetail:
    headline: str
    summary: str
    metrics: list[InspectionMetric] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    metadata_rows: list[dict[str, str]] = field(default_factory=list)
    response_preview: str | None = None


def build_plan_guidance(plan: WorkflowPlan, *, question: str) -> PlanGuidance:
    metadata = plan.metadata
    explicit_file_count = int(metadata.get("context_file_count", 0))
    explicit_url_count = int(metadata.get("context_url_count", 0))
    discovered_file_count = int(metadata.get("discovered_context_file_count", 0))
    discovered_url_count = int(metadata.get("discovered_context_url_count", 0))
    context_artifact_count = int(metadata.get("context_artifact_count", 0))
    compare_intent = bool(metadata.get("compare_intent"))
    review_enabled = bool(metadata.get("review_enabled"))
    requires_research_support = bool(metadata.get("requires_research_support"))
    question_type = str(metadata.get("question_type", "research"))
    route_label = _route_label(plan.workflow_name)

    guidance = _route_guidance(plan.workflow_name, review_enabled=review_enabled)
    warnings: list[str] = []

    if _URL_PATTERN.search(question) and not metadata.get(
        "inline_context_url_discovery_enabled", False
    ) and explicit_url_count == 0:
        warnings.append(
            "The question includes a URL-like string, but inline URL discovery is disabled. "
            "Attach the URL explicitly in the sidebar or enable inline URL discovery."
        )
    if _FILE_LIKE_PATTERN.search(question) and not metadata.get(
        "inline_context_file_discovery_enabled", False
    ) and explicit_file_count == 0:
        warnings.append(
            "The question includes a file-like path, but inline file discovery is disabled. "
            "Attach the file explicitly in the sidebar or enable inline file discovery."
        )

    if plan.workflow_name == "analysis_then_write" and explicit_file_count + explicit_url_count == 0:
        warnings.append(
            "This route will analyze the request text only because no explicit files or URLs are attached."
        )
    if compare_intent and context_artifact_count < 2:
        warnings.append(
            "Comparison intent was detected, but fewer than two explicit contexts are attached. "
            "Attach at least two files or URLs to trigger the comparison route."
        )
    if question_type == "comparison" and not requires_research_support:
        warnings.append(
            "This stays on the narrower comparison route because the question asks for comparison, "
            "not recommendation or prioritization."
        )
    if question_type == "analysis" and (explicit_file_count + explicit_url_count) > 0 and not requires_research_support:
        warnings.append(
            "This stays on the narrower analysis route because the question asks for inspection or summary, "
            "not recommendation or prioritization."
        )

    if discovered_file_count:
        guidance.append(
            f"Inline file discovery matched {discovered_file_count} file reference(s); explicit attachments remain more predictable."
        )
    if discovered_url_count:
        guidance.append(
            f"Inline URL discovery matched {discovered_url_count} URL reference(s); explicit attachments remain more predictable."
        )

    summary = _plan_summary(
        workflow_name=plan.workflow_name,
        explicit_file_count=explicit_file_count,
        explicit_url_count=explicit_url_count,
        review_enabled=review_enabled,
    )
    metrics = [
        InspectionMetric("Steps", str(len(plan.steps))),
        InspectionMetric("Files", str(explicit_file_count)),
        InspectionMetric("URLs", str(explicit_url_count)),
        InspectionMetric("Review", "On" if review_enabled else "Off"),
    ]
    step_rows = [
        {
            "step": str(index),
            "worker": step.worker_name,
            "task_type": step.task_type.value,
            "output_schema": step.output_schema,
        }
        for index, step in enumerate(plan.steps, start=1)
    ]

    return PlanGuidance(
        headline=route_label,
        summary=summary,
        metrics=metrics,
        guidance=guidance,
        warnings=warnings,
        step_rows=step_rows,
    )


def build_result_overview(result: WorkflowResult) -> ResultOverview:
    total_duration_ms = sum(trace.duration_ms for trace in result.traces)
    cache_hits = sum(1 for trace in result.traces if trace.metadata.get("cache_hit") is True)
    route_label = _route_label(result.workflow_plan.workflow_name)

    summary_parts = [_result_summary(result)]
    if result.review is not None:
        summary_parts.append(
            "Review marked the answer as consistent."
            if result.review.consistent
            else "Review flagged follow-up issues."
        )

    highlights: list[str] = []
    if result.research is not None:
        highlights.append(
            f"Research captured {len(result.research.key_points)} key point(s) and {len(result.research.caveats)} caveat(s)."
        )
    if result.analysis is not None:
        highlights.append(
            f"Analysis captured {len(result.analysis.findings)} finding(s), {len(result.analysis.metrics)} metric(s), "
            f"and {len(result.analysis.caveats)} caveat(s)."
        )
    if result.comparison is not None:
        highlights.append(
            f"Comparison captured {len(result.comparison.comparisons)} comparison point(s), "
            f"{len(result.comparison.metrics)} metric(s), and {len(result.comparison.caveats)} caveat(s)."
        )
    highlights.append(
        f"Final answer includes {len(result.final_answer.supporting_points)} supporting point(s) and "
        f"{len(result.final_answer.limitations)} limitation(s)."
    )
    if result.review is not None:
        highlights.append(
            f"Review checked {len(result.review.checked_points)} point(s) and surfaced {len(result.review.issues)} issue(s)."
        )

    next_actions: list[str] = []
    if result.review is None:
        next_actions.append(
            "Enable the review stage when you want an explicit consistency check on the final answer."
        )
    elif not result.review.consistent:
        next_actions.append("Address the review issues before treating this run as ready to share or automate.")
    if result.analysis is not None and result.analysis.caveats:
        next_actions.append("Inspect the analysis caveats before acting on the recommendation or summary.")
    if result.comparison is not None and result.comparison.caveats:
        next_actions.append("Inspect the comparison caveats before acting on differences or ranking decisions.")
    if result.workflow_plan.workflow_name == "research_then_write":
        next_actions.append("Attach explicit files or URLs on the next run if you want grounded context analysis.")
    elif result.workflow_plan.workflow_name == "analysis_then_write":
        next_actions.append(
            "Ask for a recommendation, strategy, or prioritization decision to trigger the broader hybrid route next time."
        )
    elif result.workflow_plan.workflow_name == "comparison_then_write":
        next_actions.append(
            "Ask which option, region, or source you should prioritize next to trigger the broader hybrid comparison route."
        )
    elif result.review is None:
        next_actions.append("This already uses the broadest bounded route today; add review when you need a validation gate.")

    metrics = [
        InspectionMetric("Steps", str(len(result.traces))),
        InspectionMetric("Tools", str(len(result.tool_invocations))),
        InspectionMetric("Duration", _format_duration(total_duration_ms)),
        InspectionMetric("Cache Hits", str(cache_hits)),
    ]

    return ResultOverview(
        headline=f"{route_label} Inspection",
        summary=" ".join(summary_parts),
        metrics=metrics,
        highlights=highlights,
        next_actions=_dedupe_preserve_order(next_actions),
    )


def build_acceptance_overview(
    record: AcceptanceRecord,
    *,
    comparison: AcceptanceComparison | None = None,
) -> AcceptanceOverview:
    warning_count = sum(len(case.warnings) for case in record.report.case_results)
    duration_ms = sum(case.duration_ms for case in record.report.case_results)
    failed_questions = [case.question for case in record.report.case_results if not case.passed]
    highlighted_failures = failed_questions[:3]
    metrics = [
        InspectionMetric("Passed", f"{record.report.passed_cases}/{record.report.total_cases}"),
        InspectionMetric("Failed", str(record.report.failed_cases)),
        InspectionMetric("Warnings", str(warning_count)),
        InspectionMetric("Duration", _format_duration(duration_ms)),
    ]
    summary = (
        f"This acceptance run finished with status `{record.status}` on runner `{record.report.runner}`."
    )
    if comparison is not None:
        summary = (
            f"{summary} Baseline comparison shows {comparison.regression_count} regression(s) "
            f"and {comparison.improvement_count} improvement(s)."
        )

    highlights = [
        f"Review was {'enabled' if record.report.enable_review else 'disabled'} for this run.",
        f"The report covers {record.report.total_cases} acceptance case(s).",
    ]
    if highlighted_failures:
        highlights.append(
            f"Failed case sample: {', '.join(highlighted_failures)}."
        )
    if record.report.model is not None:
        highlights.append(f"Model: {record.report.model}.")

    warnings: list[str] = []
    if record.report.failed_cases > 0:
        warnings.append("This acceptance run has failing cases and should not be treated as a clean baseline.")
    if comparison is not None and comparison.regression_count > 0:
        warnings.append("The baseline comparison detected regressions in one or more acceptance cases.")
    if comparison is not None and comparison.warning_count_delta > 0:
        warnings.append("The current run produced more warnings than the selected baseline.")

    next_actions: list[str] = []
    if record.report.failed_cases > 0:
        next_actions.append("Inspect the failing acceptance cases before promoting this run or using it as a baseline.")
    if comparison is None:
        next_actions.append("Persist another acceptance report if you want baseline comparisons in this inspection view.")
    elif comparison.regression_count > 0:
        next_actions.append("Address the regressed cases before treating this run as an improvement over the baseline.")
    elif comparison.improvement_count > 0:
        next_actions.append("Keep the baseline around for one more run if you want to verify that the improvements hold.")
    else:
        next_actions.append("The baseline comparison is stable; use a newer workload if you want to increase coverage.")

    changed_case_rows: list[dict[str, Any]] = []
    if comparison is not None:
        changed_case_rows = [
            {
                "question": case.question,
                "baseline_passed": case.baseline_passed,
                "current_passed": case.current_passed,
                "baseline_warnings": case.baseline_warning_count,
                "current_warnings": case.current_warning_count,
                "regression": case.regression,
                "improvement": case.improvement,
            }
            for case in comparison.case_comparisons
            if case.changed
        ]

    return AcceptanceOverview(
        headline="Acceptance Report",
        summary=summary,
        metrics=metrics,
        highlights=highlights,
        warnings=warnings,
        next_actions=_dedupe_preserve_order(next_actions),
        changed_case_rows=changed_case_rows,
    )


def build_cache_overview(
    summary: dict[str, Any],
    *,
    recent_entries: list[dict[str, Any]],
) -> CacheOverview:
    total_entries = int(summary.get("total_entries", 0))
    expired_entries = int(summary.get("expired_entries", 0))
    active_entries = int(summary.get("active_entries", 0))
    max_age_seconds = summary.get("max_age_seconds")
    metrics = [
        InspectionMetric("Total", str(total_entries)),
        InspectionMetric("Active", str(active_entries)),
        InspectionMetric("Expired", str(expired_entries)),
        InspectionMetric("TTL", str(max_age_seconds) if max_age_seconds is not None else "Off"),
    ]

    summary_text = (
        "This cache snapshot summarizes the local structured-result cache used by the active runner configuration."
    )
    task_types = sorted(
        {
            str(entry.get("task_type") or "n/a")
            for entry in recent_entries
        }
    )
    highlights: list[str] = []
    if recent_entries:
        highlights.append(f"Recent entries cover {len(task_types)} task type(s): {', '.join(task_types)}.")
        highlights.append(f"Most recent cache entry: {recent_entries[0]['created_at']}.")
    else:
        highlights.append("No cache entries are currently available in this directory.")

    warnings: list[str] = []
    if expired_entries > 0:
        warnings.append("Expired cache entries are present. Prune them if you want an accurate active snapshot.")
    if total_entries == 0:
        warnings.append("The cache is empty, so this surface cannot yet show reuse patterns.")

    next_actions: list[str] = []
    if total_entries == 0:
        next_actions.append("Run a workflow with caching enabled to populate this inspection view.")
    if max_age_seconds is None:
        next_actions.append("Configure a cache TTL if you want expiry and prune guidance in this view.")
    elif expired_entries > 0:
        next_actions.append("Run the cache prune command to remove expired entries before relying on hit rates.")
    else:
        next_actions.append("The cache is healthy; compare runner and task-type spread if you want to tune reuse.")

    return CacheOverview(
        headline="Cache Health",
        summary=summary_text,
        metrics=metrics,
        highlights=highlights,
        warnings=warnings,
        next_actions=_dedupe_preserve_order(next_actions),
        recent_entry_rows=recent_entries,
    )


def build_acceptance_case_detail(
    case: AcceptanceCaseResult,
    *,
    case_comparison: AcceptanceCaseComparison | None = None,
) -> AcceptanceCaseDetail:
    metrics = [
        InspectionMetric("Passed", "Yes" if case.passed else "No"),
        InspectionMetric("Errors", str(len(case.errors))),
        InspectionMetric("Warnings", str(len(case.warnings))),
        InspectionMetric("Duration", _format_duration(case.duration_ms)),
    ]
    summary = (
        "This acceptance case passed."
        if case.passed
        else "This acceptance case failed and should be inspected before using the run as a baseline."
    )
    if case_comparison is not None and case_comparison.changed:
        summary = (
            f"{summary} Relative to baseline, regression={case_comparison.regression}, "
            f"improvement={case_comparison.improvement}."
        )

    highlights = [
        f"Trace order length: {len(case.trace_order)}.",
    ]
    if case.result is not None:
        highlights.append(f"Workflow: {case.result.workflow_plan.workflow_name}.")
        highlights.append(f"Tool invocations: {len(case.result.tool_invocations)}.")
    if case_comparison is not None and case_comparison.changed:
        highlights.append(
            f"Baseline warnings: {case_comparison.baseline_warning_count}, current warnings: {case_comparison.current_warning_count}."
        )

    warnings = list(case.warnings)
    if not case.passed:
        warnings.extend(case.errors)
    if case_comparison is not None and case_comparison.regression:
        warnings.append("This case regressed relative to the selected baseline.")

    next_actions: list[str] = []
    if not case.passed:
        next_actions.append("Inspect the failing result or error path before trusting this case outcome.")
    if case.result is None:
        next_actions.append("This case has no structured workflow result, so audit artifacts are the next place to inspect.")
    elif case.result.review is None:
        next_actions.append("Enable review on a follow-up run if you want a stricter validation path for this case.")
    if case_comparison is not None and case_comparison.improvement:
        next_actions.append("Keep comparing against the previous baseline to verify that this improvement remains stable.")

    trace_rows: list[dict[str, Any]] = []
    tool_rows: list[dict[str, Any]] = []
    final_answer_preview: str | None = None
    result_overview: ResultOverview | None = None
    if case.result is not None:
        result_overview = build_result_overview(case.result)
        trace_rows = [
            {
                "worker": trace.worker_name,
                "task_type": trace.task_type.value,
                "status": trace.status,
                "duration_ms": str(trace.duration_ms),
            }
            for trace in case.result.traces
        ]
        tool_rows = [
            {
                "tool_name": invocation.tool_name,
                "status": invocation.status,
                "duration_ms": str(invocation.duration_ms),
                "output_summary": invocation.output_summary or "n/a",
            }
            for invocation in case.result.tool_invocations
        ]
        final_answer_preview = case.result.final_answer.answer

    return AcceptanceCaseDetail(
        headline="Acceptance Case Detail",
        summary=summary,
        metrics=metrics,
        highlights=highlights,
        warnings=_dedupe_preserve_order(warnings),
        next_actions=_dedupe_preserve_order(next_actions),
        trace_rows=trace_rows,
        tool_rows=tool_rows,
        final_answer_preview=final_answer_preview,
        result_overview=result_overview,
    )


def build_cache_entry_detail(
    entry: CacheEntry,
    *,
    expired: bool,
) -> CacheEntryDetail:
    response_model = str(entry.metadata.get("response_model") or "n/a")
    task_type = str(entry.metadata.get("task_type") or "n/a")
    runner = str(entry.metadata.get("runner") or "n/a")
    model = str(entry.metadata.get("model") or "n/a")
    metrics = [
        InspectionMetric("Expired", "Yes" if expired else "No"),
        InspectionMetric("Task", task_type),
        InspectionMetric("Response", response_model),
        InspectionMetric("Runner", runner),
    ]
    summary = (
        f"This cache entry stores a cached `{response_model}` response for task type `{task_type}`."
    )
    highlights = [
        f"Created at: {entry.created_at}.",
        f"Model: {model}.",
        f"Response fields: {', '.join(sorted(entry.response.keys())) if entry.response else 'none'}.",
    ]
    warnings: list[str] = []
    if expired:
        warnings.append("This cache entry is expired under the current TTL configuration.")
    if not entry.response:
        warnings.append("This cache entry has no response payload to preview.")

    next_actions: list[str] = []
    if expired:
        next_actions.append("Prune expired cache entries before using this snapshot to judge reuse quality.")
    else:
        next_actions.append("Compare this entry's task type and response model against neighboring entries to assess cache spread.")

    metadata_rows = [
        {"key": str(key), "value": str(value)}
        for key, value in sorted(entry.metadata.items())
    ]

    response_preview = _response_preview(entry.response)
    return CacheEntryDetail(
        headline="Cache Entry Detail",
        summary=summary,
        metrics=metrics,
        highlights=highlights,
        warnings=warnings,
        next_actions=_dedupe_preserve_order(next_actions),
        metadata_rows=metadata_rows,
        response_preview=response_preview,
    )


def _route_label(workflow_name: str) -> str:
    if workflow_name == "research_then_comparison_then_write":
        return "Hybrid Comparison Route"
    if workflow_name == "comparison_then_write":
        return "Comparison Route"
    if workflow_name == "research_then_analysis_then_write":
        return "Hybrid Advisory Route"
    if workflow_name == "analysis_then_write":
        return "Analysis Route"
    return "Research Route"


def _route_guidance(workflow_name: str, *, review_enabled: bool) -> list[str]:
    if workflow_name == "research_then_comparison_then_write":
        guidance = [
            "Use this route when you need broad reasoning plus a grounded comparison across multiple explicit contexts.",
            "Research frames the comparison before the comparison step consumes tool-backed context.",
            "The writer will synthesize both research and comparison into the final answer.",
        ]
    elif workflow_name == "comparison_then_write":
        guidance = [
            "Use this route when you need to compare two or more explicit files or URLs without adding broader research framing.",
            "Keep comparison inputs explicit so tool-backed differences stay auditable and predictable.",
            "Ask what you should recommend or prioritize next when you want the broader hybrid comparison route.",
        ]
    elif workflow_name == "research_then_analysis_then_write":
        guidance = [
            "Use this route when you need both high-level reasoning and grounded analysis over explicit files or URLs.",
            "Research frames the question before the analysis step consumes tool-backed context.",
            "The writer will synthesize both research and analysis into the final answer.",
        ]
    elif workflow_name == "analysis_then_write":
        guidance = [
            "Use this route for summaries and inspections over attached datasets or fetched page content.",
            "Keep files and URLs explicit so tool-backed analysis stays auditable and predictable.",
            "Ask what you should recommend or prioritize next when you want the broader hybrid route.",
        ]
    else:
        guidance = [
            "Use this route for open-ended knowledge questions that do not need tool-backed context.",
            "Attach explicit files or URLs when you want the answer grounded in local or remote artifacts.",
            "The writer will synthesize directly from the research result.",
        ]

    if review_enabled:
        guidance.append("Review is enabled, so the run will end with a consistency check over the final answer.")
    return guidance


def _plan_summary(
    *,
    workflow_name: str,
    explicit_file_count: int,
    explicit_url_count: int,
    review_enabled: bool,
) -> str:
    context_summary = (
        f"Attached context: {explicit_file_count} file(s), {explicit_url_count} URL(s)."
        if (explicit_file_count + explicit_url_count) > 0
        else "No explicit context is attached."
    )
    if workflow_name == "research_then_comparison_then_write":
        route_summary = (
            "This is the broadest comparison route today: research frames the request, "
            "comparison grounds it in tools, and writing synthesizes both."
        )
    elif workflow_name == "comparison_then_write":
        route_summary = (
            "This route goes straight into tool-backed comparison before the final synthesis step."
        )
    elif workflow_name == "research_then_analysis_then_write":
        route_summary = (
            "This is the broadest bounded route today: research frames the request, "
            "analysis grounds it in tools, and writing synthesizes both."
        )
    elif workflow_name == "analysis_then_write":
        route_summary = (
            "This route goes straight into tool-backed analysis before the final synthesis step."
        )
    else:
        route_summary = (
            "This route stays on the knowledge-oriented research path before the final synthesis step."
        )
    review_summary = "Review is enabled." if review_enabled else "Review is disabled."
    return f"{route_summary} {context_summary} {review_summary}"


def _result_summary(result: WorkflowResult) -> str:
    if result.workflow_plan.workflow_name == "research_then_comparison_then_write":
        return (
            "This run combined research framing with tool-backed comparison before producing the final answer."
        )
    if result.workflow_plan.workflow_name == "comparison_then_write":
        return "This run relied on tool-backed comparison before producing the final answer."
    if result.workflow_plan.workflow_name == "research_then_analysis_then_write":
        return (
            "This run combined research framing with tool-backed analysis before producing the final answer."
        )
    if result.workflow_plan.workflow_name == "analysis_then_write":
        return "This run relied on tool-backed analysis before producing the final answer."
    return "This run stayed on the research path before producing the final answer."


def _format_duration(duration_ms: int) -> str:
    if duration_ms < 1000:
        return f"{duration_ms} ms"
    return f"{duration_ms / 1000:.2f} s"


def _response_preview(response: dict[str, Any]) -> str | None:
    for key in ("answer", "summary", "verdict", "question"):
        value = response.get(key)
        if isinstance(value, str) and value.strip():
            return _truncate_text(value.strip(), max_chars=240)
    return None


def _truncate_text(value: str, *, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[: max_chars - 3].rstrip()}..."


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped
