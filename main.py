from __future__ import annotations

import argparse

from orchestrator.bootstrap import build_supervisor, format_pretty


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
        choices=["pretty", "json"],
        default="pretty",
        help="Output mode.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    supervisor = build_supervisor(
        runner_name=args.runner,
        model=args.model,
        base_url=args.base_url,
    )
    result = supervisor.run(args.question)
    if args.output == "json":
        print(result.model_dump_json(indent=2))
    else:
        print(format_pretty(result))


if __name__ == "__main__":
    main()
