from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_cli_outputs_json_workflow_result() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            "How should I define worker schemas before adding more workers?",
            "--runner",
            "fake",
            "--output",
            "json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["question"].startswith("How should I define worker schemas")
    assert payload["workflow_plan"]["workflow_name"] == "research_then_write"
    assert payload["research"]["sources"] == ["internal:fake-runner"]
    assert payload["analysis"] is None
    assert len(payload["traces"]) == 2


def test_cli_outputs_tool_invocations_for_local_csv_analysis(tmp_path) -> None:
    csv_path = tmp_path / "metrics.csv"
    csv_path.write_text("day,visits\nMon,5\nTue,8\nWed,13\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            f"Analyze `{csv_path}` and summarize the biggest changes.",
            "--runner",
            "fake",
            "--output",
            "json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["workflow_plan"]["workflow_name"] == "analysis_then_write"
    assert payload["research"] is None
    assert payload["analysis"]["summary"].startswith("Analysis summary for:")
    assert [invocation["tool_name"] for invocation in payload["tool_invocations"]] == [
        "local_file_context",
        "csv_analysis",
    ]


def test_cli_accepts_explicit_context_file_argument(tmp_path) -> None:
    csv_path = tmp_path / "metrics.csv"
    csv_path.write_text("day,visits\nMon,5\nTue,8\nWed,13\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            "Summarize the most important changes in this data.",
            "--runner",
            "fake",
            "--context-file",
            str(csv_path),
            "--output",
            "json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["workflow_plan"]["workflow_name"] == "analysis_then_write"
    assert payload["workflow_plan"]["metadata"]["context_file_count"] == 1
    assert [invocation["tool_name"] for invocation in payload["tool_invocations"]] == [
        "local_file_context",
        "csv_analysis",
    ]


def test_cli_outputs_markdown_workflow_result() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            "How should I bootstrap a supervisor-worker system?",
            "--runner",
            "fake",
            "--output",
            "markdown",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = completed.stdout

    assert payload.startswith("# Workflow Result")
    assert "## Final Answer" in payload
    assert "## Trace" in payload
    assert "- Workflow: `research_then_write`" in payload


def test_cli_outputs_markdown_tool_section_for_analysis(tmp_path) -> None:
    csv_path = tmp_path / "metrics.csv"
    csv_path.write_text("day,visits\nMon,5\nTue,8\nWed,13\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            f"Analyze `{csv_path}` and summarize the biggest changes.",
            "--runner",
            "fake",
            "--output",
            "markdown",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = completed.stdout

    assert "## Tool Invocations" in payload
    assert "### `local_file_context`" in payload
    assert "### `csv_analysis`" in payload
    assert "- Workflow: `analysis_then_write`" in payload
