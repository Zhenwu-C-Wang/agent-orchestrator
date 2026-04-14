from __future__ import annotations

import argparse
from time import perf_counter

from pydantic import BaseModel, Field

from orchestrator.bootstrap import build_supervisor
from schemas.result_schema import WorkflowResult

ACCEPTANCE_QUESTIONS = [
    "How should I bootstrap a supervisor-worker agent system?",
    "What are the tradeoffs of fake runners versus local models in an MVP?",
    "How should I define worker schemas before adding more workers?",
    "What risks appear when a supervisor directly writes the final answer?",
    "When should I add retry, cache, and audit layers to this system?",
]


class AcceptanceCaseResult(BaseModel):
    question: str
    passed: bool
    duration_ms: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace_order: list[str] = Field(default_factory=list)
    result: WorkflowResult | None = None


class AcceptanceReport(BaseModel):
    runner: str
    model: str | None = None
    enable_review: bool = False
    total_cases: int
    passed_cases: int
    failed_cases: int
    case_results: list[AcceptanceCaseResult] = Field(default_factory=list)


def _has_content(value: str) -> bool:
    return bool(value and value.strip())


def evaluate_result(result: WorkflowResult, *, expect_review: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not _has_content(result.research.summary):
        errors.append("Research summary is empty.")
    if not result.research.key_points:
        errors.append("Research key_points are empty.")
    if not _has_content(result.final_answer.answer):
        errors.append("Final answer is empty.")
    if not result.final_answer.supporting_points:
        errors.append("Final answer supporting_points are empty.")

    trace_order = [trace.worker_name for trace in result.traces]
    expected_order = ["research", "writer", "review"] if expect_review else ["research", "writer"]
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

    overlapping_points = set(result.research.key_points) & set(result.final_answer.supporting_points)
    if not overlapping_points:
        warnings.append("Writer output did not reuse any research key_points verbatim.")

    return errors, warnings


def run_acceptance(
    *,
    runner_name: str,
    model: str,
    base_url: str,
    enable_review: bool = False,
    audit_dir: str | None = None,
    max_retries: int = 1,
    retry_backoff_seconds: float = 0.25,
) -> AcceptanceReport:
    supervisor = build_supervisor(
        runner_name=runner_name,
        model=model,
        base_url=base_url,
        enable_review=enable_review,
        audit_dir=audit_dir,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
    )

    case_results: list[AcceptanceCaseResult] = []

    for question in ACCEPTANCE_QUESTIONS:
        started_at = perf_counter()
        errors: list[str] = []
        warnings: list[str] = []
        result: WorkflowResult | None = None

        try:
            result = supervisor.run(question)
            errors, warnings = evaluate_result(result, expect_review=enable_review)
        except Exception as exc:
            errors = [str(exc)]

        duration_ms = int((perf_counter() - started_at) * 1000)
        case_results.append(
            AcceptanceCaseResult(
                question=question,
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_acceptance(
        runner_name=args.runner,
        model=args.model,
        base_url=args.base_url,
        enable_review=args.with_review,
        audit_dir=args.audit_dir,
        max_retries=args.max_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
    )
    if args.output == "json":
        print(report.model_dump_json(indent=2))
    else:
        print(format_report(report))


if __name__ == "__main__":
    main()
