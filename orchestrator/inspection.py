from __future__ import annotations

import re
from dataclasses import dataclass, field

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


def build_plan_guidance(plan: WorkflowPlan, *, question: str) -> PlanGuidance:
    metadata = plan.metadata
    explicit_file_count = int(metadata.get("context_file_count", 0))
    explicit_url_count = int(metadata.get("context_url_count", 0))
    discovered_file_count = int(metadata.get("discovered_context_file_count", 0))
    discovered_url_count = int(metadata.get("discovered_context_url_count", 0))
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
    if result.workflow_plan.workflow_name == "research_then_write":
        next_actions.append("Attach explicit files or URLs on the next run if you want grounded context analysis.")
    elif result.workflow_plan.workflow_name == "analysis_then_write":
        next_actions.append(
            "Ask for a recommendation, strategy, or prioritization decision to trigger the broader hybrid route next time."
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


def _route_label(workflow_name: str) -> str:
    if workflow_name == "research_then_analysis_then_write":
        return "Hybrid Advisory Route"
    if workflow_name == "analysis_then_write":
        return "Analysis Route"
    return "Research Route"


def _route_guidance(workflow_name: str, *, review_enabled: bool) -> list[str]:
    if workflow_name == "research_then_analysis_then_write":
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
    if workflow_name == "research_then_analysis_then_write":
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


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped
