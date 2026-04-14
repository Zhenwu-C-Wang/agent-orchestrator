from __future__ import annotations

import argparse
import json

from schemas.acceptance_schema import AcceptanceComparison, AcceptanceRecord
from tools.acceptance import AcceptanceStore
from tools.errors import AcceptanceQueryError, run_cli


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect persisted acceptance records.")
    parser.add_argument(
        "--report-dir",
        default="artifacts/acceptance",
        help="Directory containing acceptance JSON artifacts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List recent acceptance runs.")
    list_parser.add_argument("--limit", type=int, default=10, help="Maximum number of runs to show.")
    list_parser.add_argument(
        "--status",
        choices=["passed", "failed", "all"],
        default="all",
        help="Filter runs by status.",
    )
    list_parser.add_argument(
        "--output",
        choices=["pretty", "json"],
        default="pretty",
        help="Output mode.",
    )

    show_parser = subparsers.add_parser("show", help="Show one acceptance run by run_id.")
    show_parser.add_argument("run_id", help="The run_id to inspect.")
    show_parser.add_argument(
        "--output",
        choices=["pretty", "json"],
        default="pretty",
        help="Output mode.",
    )

    latest_parser = subparsers.add_parser("latest", help="Show the most recent acceptance run.")
    latest_parser.add_argument(
        "--status",
        choices=["passed", "failed", "all"],
        default="all",
        help="Filter latest run by status.",
    )
    latest_parser.add_argument(
        "--output",
        choices=["pretty", "json"],
        default="pretty",
        help="Output mode.",
    )

    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare one acceptance run against a baseline run.",
    )
    compare_parser.add_argument(
        "run_id",
        nargs="?",
        default=None,
        help="The current run_id to compare. Defaults to the latest run.",
    )
    compare_parser.add_argument(
        "--baseline-run-id",
        default=None,
        help="Explicit baseline run_id. Defaults to the previous run before the current one.",
    )
    compare_parser.add_argument(
        "--output",
        choices=["pretty", "json"],
        default="pretty",
        help="Output mode.",
    )
    return parser.parse_args()


def _normalize_status_filter(value: str) -> str | None:
    return None if value == "all" else value


def format_summary(store: AcceptanceStore, record: AcceptanceRecord) -> str:
    summary = store.summarize_record(record)
    return (
        f"{summary['run_id']} | {summary['status']} | {summary['runner']} | "
        f"{summary['created_at']} | passed={summary['passed_cases']}/{summary['total_cases']} | "
        f"warnings={summary['warning_count']} | duration_ms={summary['duration_ms']}"
    )


def format_detail(store: AcceptanceStore, record: AcceptanceRecord) -> str:
    summary = store.summarize_record(record)
    lines = [
        f"Run ID: {summary['run_id']}",
        f"Status: {summary['status']}",
        f"Created At: {summary['created_at']}",
        f"Runner: {summary['runner']}",
        f"Model: {summary['model'] or 'n/a'}",
        f"Review Enabled: {summary['review_enabled']}",
        f"Passed: {summary['passed_cases']}/{summary['total_cases']}",
        f"Failed Cases: {summary['failed_cases']}",
        f"Warnings: {summary['warning_count']}",
        f"Duration Ms: {summary['duration_ms']}",
        "Cases:",
        *[
            (
                f"- [{'PASS' if case.passed else 'FAIL'}] {case.question} | "
                f"duration_ms={case.duration_ms} | errors={len(case.errors)} | warnings={len(case.warnings)}"
            )
            for case in record.report.case_results
        ],
    ]
    return "\n".join(lines)


def format_comparison(comparison: AcceptanceComparison) -> str:
    changed_cases = [case for case in comparison.case_comparisons if case.changed]
    lines = [
        f"Current Run ID: {comparison.current_run_id}",
        f"Baseline Run ID: {comparison.baseline_run_id}",
        f"Current Status: {comparison.current_status}",
        f"Baseline Status: {comparison.baseline_status}",
        f"Passed Delta: {comparison.passed_cases_delta}",
        f"Failed Delta: {comparison.failed_cases_delta}",
        f"Warning Delta: {comparison.warning_count_delta}",
        f"Regressions: {comparison.regression_count}",
        f"Improvements: {comparison.improvement_count}",
        "Changed Cases:",
    ]
    if not changed_cases:
        lines.append("- none")
    else:
        lines.extend(
            (
                f"- {case.question} | "
                f"baseline_passed={case.baseline_passed} | current_passed={case.current_passed} | "
                f"baseline_warnings={case.baseline_warning_count} | current_warnings={case.current_warning_count} | "
                f"regression={case.regression} | improvement={case.improvement}"
            )
            for case in changed_cases
        )
    return "\n".join(lines)


def _main() -> None:
    args = parse_args()
    store = AcceptanceStore(args.report_dir)

    if args.command == "list":
        status = _normalize_status_filter(args.status)
        records = store.list_records(limit=args.limit, status=status)
        if args.output == "json":
            print(json.dumps([store.summarize_record(record) for record in records], indent=2))
        else:
            print("\n".join(format_summary(store, record) for record in records))
        return

    if args.command == "show":
        record = store.get_record(args.run_id)
        if record is None:
            raise AcceptanceQueryError(f"Acceptance run not found: {args.run_id}")
        if args.output == "json":
            print(record.model_dump_json(indent=2))
        else:
            print(format_detail(store, record))
        return

    if args.command == "latest":
        status = _normalize_status_filter(args.status)
        record = store.latest_record(status=status)
        if record is None:
            raise AcceptanceQueryError("No acceptance records found.")
        if args.output == "json":
            print(record.model_dump_json(indent=2))
        else:
            print(format_detail(store, record))
        return

    if args.command == "compare":
        current = store.get_record(args.run_id) if args.run_id else store.latest_record()
        if current is None:
            if args.run_id:
                raise AcceptanceQueryError(f"Acceptance run not found: {args.run_id}")
            raise AcceptanceQueryError("No acceptance records found.")

        baseline = (
            store.get_record(args.baseline_run_id)
            if args.baseline_run_id
            else store.previous_record(current.run_id)
        )
        if baseline is None:
            if args.baseline_run_id:
                raise AcceptanceQueryError(f"Acceptance baseline run not found: {args.baseline_run_id}")
            raise AcceptanceQueryError("No baseline acceptance record found.")

        comparison = store.compare_records(current, baseline)
        if args.output == "json":
            print(comparison.model_dump_json(indent=2))
        else:
            print(format_comparison(comparison))
        return


if __name__ == "__main__":
    run_cli(_main)
