from __future__ import annotations

import argparse
from dataclasses import dataclass
from time import perf_counter

from orchestrator.bootstrap import build_supervisor
from orchestrator.resource_paths import sample_data_path
from schemas.acceptance_schema import AcceptanceCaseResult, AcceptanceReport
from schemas.result_schema import WorkflowResult
from tools.acceptance import AcceptanceLogger
from tools.errors import AcceptanceFailedError, run_cli

ACCEPTANCE_SAMPLE_CSV = str(sample_data_path("quarterly_metrics.csv"))
ACCEPTANCE_SAMPLE_COMPARISON_CSV = str(sample_data_path("quarterly_metrics_baseline.csv"))
ACCEPTANCE_SAMPLE_JSON = str(sample_data_path("quarterly_metrics.json"))


@dataclass(frozen=True)
class AcceptanceCaseDefinition:
    question: str
    context_files: tuple[str, ...] = ()
    context_urls: tuple[str, ...] = ()

ACCEPTANCE_CASES = [
    AcceptanceCaseDefinition("How should I bootstrap a supervisor-worker agent system?"),
    AcceptanceCaseDefinition("What are the tradeoffs of fake runners versus local models in an MVP?"),
    AcceptanceCaseDefinition("How should I define worker schemas before adding more workers?"),
    AcceptanceCaseDefinition("What risks appear when a supervisor directly writes the final answer?"),
    AcceptanceCaseDefinition("When should I add retry, cache, and audit layers to this system?"),
    AcceptanceCaseDefinition(
        "Analyze the bundled quarterly metrics dataset and summarize the most important changes.",
        context_files=(ACCEPTANCE_SAMPLE_CSV,),
    ),
    AcceptanceCaseDefinition(
        "Analyze the bundled quarterly metrics dataset and recommend what we should prioritize next.",
        context_files=(ACCEPTANCE_SAMPLE_CSV,),
    ),
    AcceptanceCaseDefinition(
        "Compare the bundled quarterly metrics datasets and summarize the most important differences.",
        context_files=(ACCEPTANCE_SAMPLE_CSV, ACCEPTANCE_SAMPLE_COMPARISON_CSV),
    ),
    AcceptanceCaseDefinition(
        "Compare the bundled quarterly metrics datasets and recommend which one we should prioritize next.",
        context_files=(ACCEPTANCE_SAMPLE_CSV, ACCEPTANCE_SAMPLE_COMPARISON_CSV),
    ),
    AcceptanceCaseDefinition(
        "Analyze the bundled quarterly metrics JSON snapshot and summarize the most important changes.",
        context_files=(ACCEPTANCE_SAMPLE_JSON,),
    ),
]
ACCEPTANCE_QUESTIONS = [case.question for case in ACCEPTANCE_CASES]

def _has_content(value: str) -> bool:
    return bool(value and value.strip())


def evaluate_result(result: WorkflowResult, *, expect_review: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    expects_tool_path = bool(result.workflow_plan.metadata.get("has_local_files"))

    intermediate_points: list[str] = []
    if result.research is not None:
        if not _has_content(result.research.summary):
            errors.append("Research summary is empty.")
        if not result.research.key_points:
            errors.append("Research key_points are empty.")
        intermediate_points.extend(result.research.key_points)
    if result.analysis is not None:
        if not _has_content(result.analysis.summary):
            errors.append("Analysis summary is empty.")
        if not result.analysis.findings:
            errors.append("Analysis findings are empty.")
        intermediate_points.extend(result.analysis.findings)
    if result.comparison is not None:
        if not _has_content(result.comparison.summary):
            errors.append("Comparison summary is empty.")
        if not result.comparison.comparisons:
            errors.append("Comparison points are empty.")
        intermediate_points.extend(result.comparison.comparisons)
    if result.research is None and result.analysis is None and result.comparison is None:
        errors.append("No intermediate worker result was returned.")
    if not _has_content(result.final_answer.answer):
        errors.append("Final answer is empty.")
    if not result.final_answer.supporting_points:
        errors.append("Final answer supporting_points are empty.")

    trace_order = [trace.worker_name for trace in result.traces]
    expected_order = [step.worker_name for step in result.workflow_plan.steps]
    if trace_order != expected_order:
        errors.append(f"Unexpected trace order: {trace_order}")
    if any(trace.status != "completed" for trace in result.traces):
        errors.append("One or more workflow steps did not complete successfully.")
    if expect_review and result.review is None:
        errors.append("Review stage was enabled but no review result was returned.")
    if not expect_review and result.review is not None:
        warnings.append("Review result was returned even though review stage was not requested.")
    if result.review is not None:
        if not _has_content(result.review.verdict):
            errors.append("Review verdict is empty.")
        if not result.review.consistent and not result.review.issues:
            warnings.append("Review marked the answer inconsistent but did not provide issues.")

    if expects_tool_path:
        if not result.tool_invocations:
            errors.append("Tool-backed workflow did not record any tool invocations.")
        elif any(invocation.status != "completed" for invocation in result.tool_invocations):
            errors.append("One or more tool invocations did not complete successfully.")
    elif result.tool_invocations:
        warnings.append("Tool invocations were recorded for a workflow that did not require local files.")

    overlapping_points = set(intermediate_points) & set(result.final_answer.supporting_points)
    if not overlapping_points:
        warnings.append("Writer output did not reuse any intermediate worker points verbatim.")

    return errors, warnings


def run_acceptance(
    *,
    runner_name: str,
    model: str,
    base_url: str,
    enable_review: bool = False,
    audit_dir: str | None = None,
    cache_dir: str | None = None,
    cache_max_age_seconds: float | None = None,
    max_retries: int = 1,
    retry_backoff_seconds: float = 0.25,
) -> AcceptanceReport:
    supervisor = build_supervisor(
        runner_name=runner_name,
        model=model,
        base_url=base_url,
        enable_review=enable_review,
        audit_dir=audit_dir,
        cache_dir=cache_dir,
        cache_max_age_seconds=cache_max_age_seconds,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
    )

    case_results: list[AcceptanceCaseResult] = []

    for case in ACCEPTANCE_CASES:
        started_at = perf_counter()
        errors: list[str] = []
        warnings: list[str] = []
        result: WorkflowResult | None = None

        try:
            if case.context_files or case.context_urls:
                result = supervisor.run_with_context(
                    case.question,
                    context_files=list(case.context_files),
                    context_urls=list(case.context_urls),
                )
            else:
                result = supervisor.run(case.question)
            errors, warnings = evaluate_result(result, expect_review=enable_review)
        except Exception as exc:
            errors = [str(exc)]

        duration_ms = int((perf_counter() - started_at) * 1000)
        case_results.append(
            AcceptanceCaseResult(
                question=case.question,
                passed=not errors,
                duration_ms=duration_ms,
                errors=errors,
                warnings=warnings,
                trace_order=[trace.worker_name for trace in result.traces] if result else [],
                result=result,
            )
        )

    passed_cases = sum(1 for case in case_results if case.passed)
    return AcceptanceReport(
        runner=runner_name,
        model=None if runner_name == "fake" else model,
        enable_review=enable_review,
        total_cases=len(case_results),
        passed_cases=passed_cases,
        failed_cases=len(case_results) - passed_cases,
        case_results=case_results,
    )


def format_report(report: AcceptanceReport) -> str:
    lines = [
        f"Runner: {report.runner}",
        f"Model: {report.model or 'n/a'}",
        f"Review: {'enabled' if report.enable_review else 'disabled'}",
        f"Passed: {report.passed_cases}/{report.total_cases}",
        "",
    ]
    for index, case in enumerate(report.case_results, start=1):
        lines.append(
            f"{index}. [{'PASS' if case.passed else 'FAIL'}] {case.question} ({case.duration_ms}ms)"
        )
        if case.errors:
            lines.extend(f"   error: {error}" for error in case.errors)
        if case.warnings:
            lines.extend(f"   warning: {warning}" for warning in case.warnings)
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the acceptance dataset against the orchestrator.")
    parser.add_argument(
        "--runner",
        choices=["fake", "ollama"],
        default="fake",
        help="Which runner to validate.",
    )
    parser.add_argument(
        "--model",
        default="qwen2.5:14b",
        help="Local model name when using the Ollama runner.",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:11434",
        help="Base URL for the Ollama server.",
    )
    parser.add_argument(
        "--output",
        choices=["pretty", "json"],
        default="pretty",
        help="Output mode.",
    )
    parser.add_argument(
        "--with-review",
        action="store_true",
        help="Enable the optional ReviewWorker stage.",
    )
    parser.add_argument(
        "--audit-dir",
        default=None,
        help="Optional directory where one JSON audit record will be written per question.",
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Optional directory for request-level structured result caching.",
    )
    parser.add_argument(
        "--cache-max-age-seconds",
        type=float,
        default=None,
        help="Optional TTL for cache entries. Requires --cache-dir.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="Maximum number of model-layer retries for the Ollama runner.",
    )
    parser.add_argument(
        "--retry-backoff-seconds",
        type=float,
        default=0.25,
        help="Base backoff delay between Ollama retries.",
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        help="Optional directory where one JSON acceptance report record will be written per run.",
    )
    return parser.parse_args()


def _main() -> None:
    args = parse_args()
    report = run_acceptance(
        runner_name=args.runner,
        model=args.model,
        base_url=args.base_url,
        enable_review=args.with_review,
        audit_dir=args.audit_dir,
        cache_dir=args.cache_dir,
        cache_max_age_seconds=args.cache_max_age_seconds,
        max_retries=args.max_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
    )
    if args.report_dir:
        AcceptanceLogger(
            args.report_dir,
            metadata={
                "runner": args.runner,
                "model": None if args.runner == "fake" else args.model,
                "review_enabled": args.with_review,
                "audit_dir": args.audit_dir,
                "cache_dir": args.cache_dir,
                "cache_max_age_seconds": args.cache_max_age_seconds,
                "max_retries": args.max_retries,
                "retry_backoff_seconds": args.retry_backoff_seconds,
            },
        ).record_report(report)
    if args.output == "json":
        print(report.model_dump_json(indent=2))
    else:
        print(format_report(report))
    if report.failed_cases > 0:
        raise AcceptanceFailedError(
            f"{report.failed_cases} of {report.total_cases} acceptance cases failed."
        )


if __name__ == "__main__":
    run_cli(_main)
