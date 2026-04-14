import json
import subprocess
import sys
from pathlib import Path

from orchestrator.acceptance import ACCEPTANCE_QUESTIONS, run_acceptance


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_acceptance_dataset_passes_with_fake_runner() -> None:
    report = run_acceptance(
        runner_name="fake",
        model="unused",
        base_url="http://localhost:11434",
    )

    assert report.total_cases == len(ACCEPTANCE_QUESTIONS)
    assert report.failed_cases == 0
    assert all(case.passed for case in report.case_results)


def test_acceptance_dataset_passes_with_fake_runner_and_review() -> None:
    report = run_acceptance(
        runner_name="fake",
        model="unused",
        base_url="http://localhost:11434",
        enable_review=True,
    )

    assert report.total_cases == len(ACCEPTANCE_QUESTIONS)
    assert report.failed_cases == 0
    assert all(case.trace_order == ["research", "writer", "review"] for case in report.case_results)


def test_acceptance_cli_writes_report_record(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.acceptance",
            "--runner",
            "fake",
            "--report-dir",
            str(tmp_path),
            "--output",
            "json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    records = list(tmp_path.glob("*.json"))

    assert payload["failed_cases"] == 0
    assert len(records) == 1
    record_payload = json.loads(records[0].read_text(encoding="utf-8"))
    assert record_payload["status"] == "passed"
    assert record_payload["report"]["passed_cases"] == len(ACCEPTANCE_QUESTIONS)
