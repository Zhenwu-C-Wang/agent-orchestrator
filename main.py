from __future__ import annotations

import argparse

from orchestrator.bootstrap import build_supervisor, format_markdown, format_pretty
from tools.errors import run_cli


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the supervisor-driven MVP workflow.")
    parser.add_argument("question", help="The user question to process.")
    parser.add_argument(
        "--runner",
        choices=["fake", "ollama"],
        default="fake",
        help="Which model runner to use.",
    )
    parser.add_argument(
        "--model",
        default="llama3.1",
        help="Local model name when using the Ollama runner.",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:11434",
        help="Base URL for the Ollama server.",
    )
    parser.add_argument(
        "--output",
        choices=["pretty", "json", "markdown"],
        default="pretty",
        help="Output mode.",
    )
    parser.add_argument(
        "--with-review",
        action="store_true",
        help="Enable the optional ReviewWorker stage.",
    )
    parser.add_argument(
        "--context-file",
        action="append",
        default=[],
        help="Optional local file path to attach as explicit analysis context. Repeat to add more than one.",
    )
    parser.add_argument(
        "--context-url",
        action="append",
        default=[],
        help="Optional URL to attach as explicit analysis context. Repeat to add more than one.",
    )
    parser.add_argument(
        "--audit-dir",
        default=None,
        help="Optional directory where one JSON audit record will be written per run.",
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
    return parser.parse_args()


def _main() -> None:
    args = parse_args()
    supervisor = build_supervisor(
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
    result = supervisor.run_with_context(
        args.question,
        context_files=args.context_file,
        context_urls=args.context_url,
    )
    if args.output == "json":
        print(result.model_dump_json(indent=2))
    elif args.output == "markdown":
        print(format_markdown(result))
    else:
        print(format_pretty(result))


if __name__ == "__main__":
    run_cli(_main)
