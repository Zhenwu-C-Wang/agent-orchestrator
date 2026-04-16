from __future__ import annotations

import json
import subprocess
import sys
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread


REPO_ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def serve_text_page(body: str):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # pragma: no cover - exercised via subprocess
            payload = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/context"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


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
            "Analyze this dataset and summarize the biggest changes.",
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
    assert payload["research"] is None
    assert payload["analysis"]["summary"].startswith("Analysis summary for:")
    assert [invocation["tool_name"] for invocation in payload["tool_invocations"]] == [
        "local_file_context",
        "csv_analysis",
        "data_computation",
    ]


def test_cli_allows_inline_context_files_when_enabled(tmp_path) -> None:
    csv_path = tmp_path / "metrics.csv"
    csv_path.write_text("day,visits\nMon,5\nTue,8\nWed,13\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            f"Analyze `{csv_path}` and summarize the biggest changes.",
            "--runner",
            "fake",
            "--allow-inline-context-files",
            "--output",
            "json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["workflow_plan"]["metadata"]["inline_context_file_discovery_enabled"] is True
    assert [invocation["tool_name"] for invocation in payload["tool_invocations"]] == [
        "local_file_context",
        "csv_analysis",
        "data_computation",
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
        "data_computation",
    ]


def test_cli_accepts_explicit_json_context_file_argument(tmp_path) -> None:
    json_path = tmp_path / "metrics.json"
    json_path.write_text(
        (
            '[{"quarter":"2024-Q1","revenue":120,"active_users":400,"churn_rate":0.08},'
            '{"quarter":"2024-Q2","revenue":135,"active_users":430,"churn_rate":0.07}]'
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            "Summarize the most important changes in this JSON snapshot.",
            "--runner",
            "fake",
            "--context-file",
            str(json_path),
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
    assert [invocation["tool_name"] for invocation in payload["tool_invocations"]] == [
        "local_file_context",
        "json_analysis",
        "data_computation",
    ]
    assert "metrics.json" in payload["analysis"]["summary"]


def test_cli_accepts_explicit_context_url_argument() -> None:
    with serve_text_page("service status is healthy") as url:
        completed = subprocess.run(
            [
                sys.executable,
                "main.py",
                "Summarize the most important findings from this webpage.",
                "--runner",
                "fake",
                "--context-url",
                url,
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
    assert payload["workflow_plan"]["metadata"]["context_url_count"] == 1
    assert [invocation["tool_name"] for invocation in payload["tool_invocations"]] == ["http_fetch"]
    assert payload["tool_invocations"][0]["status"] == "completed"


def test_cli_routes_advisory_context_request_to_hybrid_workflow(tmp_path) -> None:
    csv_path = tmp_path / "metrics.csv"
    csv_path.write_text("quarter,revenue\nQ1,10\nQ2,20\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            "Analyze this dataset and recommend what we should prioritize next.",
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

    assert payload["workflow_plan"]["workflow_name"] == "research_then_analysis_then_write"
    assert payload["research"] is not None
    assert payload["analysis"] is not None
    assert [trace["worker_name"] for trace in payload["traces"]] == ["research", "analysis", "writer"]


def test_cli_routes_compare_request_to_comparison_workflow(tmp_path) -> None:
    current = tmp_path / "current.csv"
    baseline = tmp_path / "baseline.csv"
    current.write_text("quarter,revenue\nQ1,10\nQ2,20\n", encoding="utf-8")
    baseline.write_text("quarter,revenue\nQ1,8\nQ2,12\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            "Compare these datasets and summarize the most important differences.",
            "--runner",
            "fake",
            "--context-file",
            str(current),
            "--context-file",
            str(baseline),
            "--output",
            "json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["workflow_plan"]["workflow_name"] == "comparison_then_write"
    assert payload["comparison"] is not None
    assert payload["analysis"] is None
    assert [trace["worker_name"] for trace in payload["traces"]] == ["comparison", "writer"]
    assert [invocation["tool_name"] for invocation in payload["tool_invocations"]] == [
        "local_file_context",
        "csv_analysis",
        "data_computation",
    ]


def test_cli_routes_advisory_compare_request_to_hybrid_comparison_workflow(tmp_path) -> None:
    current = tmp_path / "current.csv"
    baseline = tmp_path / "baseline.csv"
    current.write_text("quarter,revenue\nQ1,10\nQ2,20\n", encoding="utf-8")
    baseline.write_text("quarter,revenue\nQ1,8\nQ2,12\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            "Compare these datasets and recommend which one we should prioritize next.",
            "--runner",
            "fake",
            "--context-file",
            str(current),
            "--context-file",
            str(baseline),
            "--output",
            "json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["workflow_plan"]["workflow_name"] == "research_then_comparison_then_write"
    assert payload["research"] is not None
    assert payload["comparison"] is not None
    assert [trace["worker_name"] for trace in payload["traces"]] == ["research", "comparison", "writer"]


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
            "Analyze this dataset and summarize the biggest changes.",
            "--runner",
            "fake",
            "--context-file",
            str(csv_path),
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
