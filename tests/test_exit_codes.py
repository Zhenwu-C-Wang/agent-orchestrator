from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_main_cli_returns_configuration_exit_code() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            "How should I bootstrap a supervisor-worker system?",
            "--max-retries",
            "-1",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 3
    assert "configuration-error:" in completed.stderr


def test_main_cli_returns_model_invocation_exit_code() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            "How should I bootstrap a supervisor-worker system?",
            "--runner",
            "ollama",
            "--model",
            "qwen2.5:14b",
            "--base-url",
            "http://127.0.0.1:9",
            "--max-retries",
            "0",
            "--retry-backoff-seconds",
            "0",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 4
    assert "model-invocation-error:" in completed.stderr


def test_main_cli_returns_workflow_execution_exit_code_for_tool_failure() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "main.py",
            "Summarize the most important findings from this webpage.",
            "--runner",
            "fake",
            "--context-url",
            "http://127.0.0.1:1/context",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 6
    assert "workflow-execution-error:" in completed.stderr
    assert "http_fetch failed" in completed.stderr


def test_runs_cli_returns_audit_query_exit_code_for_missing_run(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.runs",
            "--audit-dir",
            str(tmp_path),
            "show",
            "missing-run-id",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 7
    assert "audit-query-error:" in completed.stderr


def test_acceptance_cli_returns_acceptance_failed_exit_code() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.acceptance",
            "--runner",
            "ollama",
            "--model",
            "qwen2.5:14b",
            "--base-url",
            "http://127.0.0.1:9",
            "--max-retries",
            "0",
            "--retry-backoff-seconds",
            "0",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 8
    assert "acceptance-failed:" in completed.stderr
    assert "Passed: 0/10" in completed.stdout


def test_cache_cli_returns_cache_query_exit_code_when_prune_lacks_ttl(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.cache",
            "--cache-dir",
            str(tmp_path),
            "prune",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 9
    assert "cache-query-error:" in completed.stderr


def test_acceptance_runs_cli_returns_acceptance_query_exit_code_for_missing_run(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.acceptance_runs",
            "--report-dir",
            str(tmp_path),
            "show",
            "missing-run-id",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 10
    assert "acceptance-query-error:" in completed.stderr


def test_acceptance_runs_cli_returns_acceptance_query_exit_code_without_baseline(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.acceptance",
            "--runner",
            "fake",
            "--report-dir",
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0

    compare = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.acceptance_runs",
            "--report-dir",
            str(tmp_path),
            "compare",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert compare.returncode == 10
    assert "acceptance-query-error:" in compare.stderr
