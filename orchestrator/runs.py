from __future__ import annotations

import argparse
import json

from schemas.audit_schema import AuditRecord
from tools.audit import AuditStore
from tools.errors import AuditQueryError, run_cli


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect persisted audit records.")
    parser.add_argument(
        "--audit-dir",
        default="artifacts/runs",
        help="Directory containing audit JSON artifacts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List recent runs.")
    list_parser.add_argument("--limit", type=int, default=10, help="Maximum number of runs to show.")
    list_parser.add_argument(
        "--status",
        choices=["completed", "failed", "all"],
        default="all",
        help="Filter runs by status.",
    )
    list_parser.add_argument(
        "--output",
        choices=["pretty", "json"],
        default="pretty",
        help="Output mode.",
    )

    show_parser = subparsers.add_parser("show", help="Show one run by run_id.")
    show_parser.add_argument("run_id", help="The run_id to inspect.")
    show_parser.add_argument(
        "--output",
        choices=["pretty", "json"],
        default="pretty",
        help="Output mode.",
    )

    latest_parser = subparsers.add_parser("latest", help="Show the most recent run.")
    latest_parser.add_argument(
        "--status",
        choices=["completed", "failed", "all"],
        default="all",
        help="Filter latest run by status.",
    )
    latest_parser.add_argument(
        "--output",
        choices=["pretty", "json"],
        default="pretty",
        help="Output mode.",
    )
    return parser.parse_args()


def _normalize_status_filter(value: str) -> str | None:
    return None if value == "all" else value


def format_summary(store: AuditStore, record: AuditRecord) -> str:
    summary = store.summarize_record(record)
    worker_order = " -> ".join(summary["worker_order"])
    return (
        f"{summary['run_id']} | {summary['status']} | {summary['runner']} | "
        f"{summary['created_at']} | {worker_order} | tools={summary['tool_invocation_count']} | "
        f"cache_hits={summary['cache_hits']} | "
        f"{summary['question']}"
    )


def format_detail(store: AuditStore, record: AuditRecord) -> str:
    summary = store.summarize_record(record)
    lines = [
        f"Run ID: {summary['run_id']}",
        f"Status: {summary['status']}",
        f"Created At: {summary['created_at']}",
        f"Question: {summary['question']}",
        f"Runner: {summary['runner']}",
        f"Model: {summary['model'] or 'n/a'}",
        f"Review Enabled: {summary['review_enabled']}",
        f"Tool Invocations: {summary['tool_invocation_count']}",
        f"Cache Hits: {summary['cache_hits']}",
        "Traces:",
        *[
            (
                f"- {trace.task_id} | {trace.worker_name} | {trace.status} | "
                f"cache_status={trace.metadata.get('cache_status')} | "
                f"cache_hit={trace.metadata.get('cache_hit')} | "
                f"attempts={trace.metadata.get('attempt_count')}"
            )
            for trace in record.traces
        ],
    ]
    if record.error:
        lines.extend(["Error:", record.error])
    return "\n".join(lines)


def _main() -> None:
    args = parse_args()
    store = AuditStore(args.audit_dir)

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
            raise AuditQueryError(f"Run not found: {args.run_id}")
        if args.output == "json":
            print(record.model_dump_json(indent=2))
        else:
            print(format_detail(store, record))
        return

    if args.command == "latest":
        status = _normalize_status_filter(args.status)
        record = store.latest_record(status=status)
        if record is None:
            raise AuditQueryError("No audit records found.")
        if args.output == "json":
            print(record.model_dump_json(indent=2))
        else:
            print(format_detail(store, record))
        return


if __name__ == "__main__":
    run_cli(_main)
