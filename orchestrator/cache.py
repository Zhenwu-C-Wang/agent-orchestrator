from __future__ import annotations

import argparse
from typing import Any

from tools.cache import StructuredResultCache
from tools.errors import CacheQueryError, run_cli


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect or manage the local structured-result cache.")
    parser.add_argument(
        "--cache-dir",
        required=True,
        help="Directory that stores structured cache entries.",
    )
    parser.add_argument(
        "--max-age-seconds",
        type=float,
        default=None,
        help="Optional TTL used to mark entries as expired.",
    )
    parser.add_argument(
        "--output",
        choices=["pretty", "json"],
        default="pretty",
        help="Output mode.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List cache entries.")
    list_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of entries to return.",
    )

    subparsers.add_parser("stats", help="Show cache summary stats.")
    subparsers.add_parser("prune", help="Delete entries considered expired by --max-age-seconds.")
    subparsers.add_parser("clear", help="Delete all cache entries.")
    return parser.parse_args()


def _format_pretty(payload: Any) -> str:
    if isinstance(payload, list):
        if not payload:
            return "No cache entries found."
        lines: list[str] = []
        for entry in payload:
            lines.append(
                " | ".join(
                    [
                        entry["created_at"],
                        entry["cache_key"],
                        f"expired={entry['expired']}",
                        f"runner={entry['runner'] or 'n/a'}",
                        f"model={entry['model'] or 'n/a'}",
                        f"task={entry['task_type'] or 'n/a'}",
                    ]
                )
            )
        return "\n".join(lines)

    if isinstance(payload, dict):
        if "removed_entries" in payload:
            summary = payload["summary"]
            return "\n".join(
                [
                    f"Removed Entries: {payload['removed_entries']}",
                    f"Directory: {summary['directory']}",
                    f"Total Entries: {summary['total_entries']}",
                    f"Expired Entries: {summary['expired_entries']}",
                    f"Active Entries: {summary['active_entries']}",
                    f"Max Age Seconds: {summary['max_age_seconds'] if summary['max_age_seconds'] is not None else 'n/a'}",
                ]
            )
        return "\n".join(
            [
                f"Directory: {payload['directory']}",
                f"Total Entries: {payload['total_entries']}",
                f"Expired Entries: {payload['expired_entries']}",
                f"Active Entries: {payload['active_entries']}",
                f"Max Age Seconds: {payload['max_age_seconds'] if payload['max_age_seconds'] is not None else 'n/a'}",
            ]
        )

    return str(payload)


def _main() -> None:
    args = parse_args()
    if args.command == "list" and args.limit is not None and args.limit < 0:
        raise CacheQueryError("list requires --limit to be greater than or equal to 0.")

    cache = StructuredResultCache(
        args.cache_dir,
        max_age_seconds=args.max_age_seconds,
    )

    if args.command == "list":
        payload: Any = [
            cache.summarize_entry(entry)
            for entry in cache.list_entries(limit=args.limit)
        ]
    elif args.command == "stats":
        payload = cache.summarize_cache()
    elif args.command == "prune":
        if args.max_age_seconds is None:
            raise CacheQueryError("prune requires --max-age-seconds.")
        payload = {
            "removed_entries": cache.prune_expired(),
            "summary": cache.summarize_cache(),
        }
    elif args.command == "clear":
        payload = {
            "removed_entries": cache.clear(),
            "summary": cache.summarize_cache(),
        }
    else:
        raise CacheQueryError(f"Unsupported cache command: {args.command}")

    if args.output == "json":
        import json

        print(json.dumps(payload, indent=2))
    else:
        print(_format_pretty(payload))


if __name__ == "__main__":
    run_cli(_main)
