from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.audit import AuditStore


def _cost_estimate(token_estimate: int, *, runner: str | None) -> float:
    if runner in {None, "fake"}:
        return 0.0
    return round((token_estimate / 1000) * 0.0005, 6)


def render_audit_report(audit_dir: str | Path, *, limit: int | None = None) -> str:
    store = AuditStore(audit_dir)
    records = store.list_records(limit=limit)
    if not records:
        return "# Orchestration Run Report\n\nNo audit records found."

    status_counts = Counter(record.status for record in records)
    failure_counts = Counter(record.error or "unknown" for record in records if record.error)
    worker_durations: dict[str, list[int]] = defaultdict(list)
    tool_durations: dict[str, list[int]] = defaultdict(list)
    token_estimate = 0

    for record in records:
        for trace in record.traces:
            worker_durations[trace.worker_name].append(trace.duration_ms)
        if record.result is not None:
            token_estimate += max(1, len(record.result.model_dump_json()) // 4)
            for invocation in record.result.tool_invocations:
                tool_durations[invocation.tool_name].append(invocation.duration_ms)

    runner = records[0].metadata.get("runner")
    lines = [
        "# Orchestration Run Report",
        "",
        f"- Runs: `{len(records)}`",
        f"- Completed: `{status_counts.get('completed', 0)}`",
        f"- Failed: `{status_counts.get('failed', 0)}`",
        f"- Token estimate: `{token_estimate}`",
        f"- Cost estimate: `${_cost_estimate(token_estimate, runner=runner):.6f}`",
        "",
        "## Worker Timeline",
        "",
        "| Worker | Calls | Total | Average |",
        "| --- | ---: | ---: | ---: |",
    ]
    for worker_name, durations in sorted(worker_durations.items()):
        total = sum(durations)
        average = int(total / len(durations)) if durations else 0
        lines.append(f"| `{worker_name}` | {len(durations)} | {total}ms | {average}ms |")

    lines.extend(["", "## Tool Breakdown", ""])
    if not tool_durations:
        lines.append("No tool invocations recorded.")
    else:
        lines.extend(
            [
                "| Tool | Calls | Total | Average |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for tool_name, durations in sorted(tool_durations.items()):
            total = sum(durations)
            average = int(total / len(durations)) if durations else 0
            lines.append(f"| `{tool_name}` | {len(durations)} | {total}ms | {average}ms |")

    lines.extend(["", "## Top Failures", ""])
    if not failure_counts:
        lines.append("No failures recorded.")
    else:
        for error, count in failure_counts.most_common(5):
            lines.append(f"- `{count}` x {error}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a markdown report from audit JSON records.")
    parser.add_argument("--audit-dir", required=True)
    parser.add_argument("--output-file", default=None)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = render_audit_report(args.audit_dir, limit=args.limit)
    if args.output_file:
        Path(args.output_file).write_text(report, encoding="utf-8")
    else:
        print(report)


if __name__ == "__main__":
    main()
