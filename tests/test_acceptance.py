import json
import subprocess
import sys
from pathlib import Path

from orchestrator.acceptance import ACCEPTANCE_QUESTIONS, ACCEPTANCE_SAMPLE_CSV, run_acceptance


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
    tool_case = report.case_results[-1]
    assert ACCEPTANCE_SAMPLE_CSV in tool_case.question
    assert tool_case.result is not None
    assert [invocation.tool_name for invocation in tool_case.result.tool_invocations] == [
        "local_file_context",
        "csv_analysis",
    ]


def test_acceptance_dataset_passes_with_fake_runner_and_review() -> None:
    report = run_acceptance(
        runner_name="fake",
        model="unused",
        base_url="http://localhost:11434",
        enable_review=True,
    )

    assert report.total_cases == len(ACCEPTANCE_QUESTIONS)
    assert report.failed_cases == 0
    assert all(
        case.trace_order == [step.worker_name for step in case.result.workflow_plan.steps]
        for case in report.case_results
        if case.result is not None
    )


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
    last_case = payload["case_results"][-1]
    assert ACCEPTANCE_SAMPLE_CSV in last_case["question"]
    assert len(last_case["result"]["tool_invocations"]) == 2
    record_payload = json.loads(records[0].read_text(encoding="utf-8"))
    assert record_payload["status"] == "passed"
    assert record_payload["report"]["passed_cases"] == len(ACCEPTANCE_QUESTIONS)
