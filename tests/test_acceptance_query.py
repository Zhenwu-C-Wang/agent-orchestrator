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
                    question="How should I bootstrap a supervisor-worker agent system?",
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


def test_acceptance_store_compares_records(tmp_path) -> None:
    _seed_acceptance_records(tmp_path)
    store = AcceptanceStore(tmp_path)
    current = store.latest_record()
    assert current is not None
    baseline = store.previous_record(current.run_id)
    assert baseline is not None

    comparison = store.compare_records(current, baseline)

    assert comparison.current_run_id == current.run_id
    assert comparison.baseline_run_id == baseline.run_id
    assert comparison.passed_cases_delta == -1
    assert comparison.failed_cases_delta == 1
    assert comparison.warning_count_delta == 1
    assert comparison.regression_count == 1
    assert comparison.improvement_count == 0
    assert comparison.case_comparisons[0].regression is True


def test_acceptance_runs_cli_compares_records(tmp_path) -> None:
    _seed_acceptance_records(tmp_path)
    store = AcceptanceStore(tmp_path)
    current = store.latest_record()
    assert current is not None
    baseline = store.previous_record(current.run_id)
    assert baseline is not None

    compared = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.acceptance_runs",
            "--report-dir",
            str(tmp_path),
            "compare",
            current.run_id,
            "--baseline-run-id",
            baseline.run_id,
            "--output",
            "json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    compared_payload = json.loads(compared.stdout)

    assert compared_payload["current_run_id"] == current.run_id
    assert compared_payload["baseline_run_id"] == baseline.run_id
    assert compared_payload["regression_count"] == 1
    assert compared_payload["case_comparisons"][0]["regression"] is True
