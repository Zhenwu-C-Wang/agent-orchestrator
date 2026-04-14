from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from schemas.acceptance_schema import AcceptanceCaseResult, AcceptanceReport
from tools.acceptance import AcceptanceLogger, AcceptanceStore


REPO_ROOT = Path(__file__).resolve().parents[1]


def _seed_acceptance_records(tmp_path: Path) -> None:
    logger = AcceptanceLogger(tmp_path, metadata={"source": "test"})
    logger.record_report(
        AcceptanceReport(
            runner="fake",
            model=None,
            enable_review=False,
            total_cases=5,
            passed_cases=5,
            failed_cases=0,
            case_results=[
                AcceptanceCaseResult(
                    question="How should I bootstrap a supervisor-worker agent system?",
                    passed=True,
                    duration_ms=5,
                )
            ],
        )
    )
    logger.record_report(
        AcceptanceReport(
            runner="ollama",
            model="qwen2.5:14b",
            enable_review=True,
            total_cases=5,
            passed_cases=4,
            failed_cases=1,
            case_results=[
                AcceptanceCaseResult(
                    question="What risks appear when a supervisor directly writes the final answer?",
                    passed=False,
                    duration_ms=12,
                    errors=["writer drifted from research"],
                    warnings=["review flagged inconsistency"],
                )
            ],
        )
    )


def test_acceptance_store_lists_and_filters_records(tmp_path) -> None:
    _seed_acceptance_records(tmp_path)
    store = AcceptanceStore(tmp_path)

    all_records = store.list_records()
    failed_records = store.list_records(status="failed")
    latest_record = store.latest_record()

    assert len(all_records) == 2
    assert len(failed_records) == 1
    assert failed_records[0].status == "failed"
    assert latest_record is not None
    assert store.get_record(latest_record.run_id) is not None


def test_acceptance_runs_cli_lists_and_shows_records(tmp_path) -> None:
    _seed_acceptance_records(tmp_path)
    store = AcceptanceStore(tmp_path)
    latest = store.latest_record()
    assert latest is not None

    listed = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.acceptance_runs",
            "--report-dir",
            str(tmp_path),
            "list",
            "--output",
            "json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    listed_payload = json.loads(listed.stdout)

    shown = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.acceptance_runs",
            "--report-dir",
            str(tmp_path),
            "show",
            latest.run_id,
            "--output",
            "json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    shown_payload = json.loads(shown.stdout)

    latest_cmd = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.acceptance_runs",
            "--report-dir",
            str(tmp_path),
            "latest",
            "--output",
            "json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    latest_payload = json.loads(latest_cmd.stdout)

    assert len(listed_payload) == 2
    assert shown_payload["run_id"] == latest.run_id
    assert latest_payload["run_id"] == latest.run_id
