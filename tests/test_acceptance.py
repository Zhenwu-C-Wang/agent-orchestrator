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
    csv_case = next(case for case in report.case_results if "quarterly metrics dataset and summarize" in case.question)
    hybrid_case = next(case for case in report.case_results if "prioritize next" in case.question)
    json_case = next(case for case in report.case_results if "quarterly metrics JSON snapshot" in case.question)
    assert "quarterly metrics dataset" in csv_case.question
    assert csv_case.result is not None
    assert csv_case.result.workflow_plan.metadata["context_file_count"] == 1
    assert [invocation.tool_name for invocation in csv_case.result.tool_invocations] == [
        "local_file_context",
        "csv_analysis",
        "data_computation",
    ]
    assert hybrid_case.result is not None
    assert hybrid_case.result.workflow_plan.workflow_name == "research_then_analysis_then_write"
    assert [trace.worker_name for trace in hybrid_case.result.traces] == [
        "research",
        "analysis",
        "writer",
    ]
    assert "quarterly metrics JSON snapshot" in json_case.question
    assert json_case.result is not None
    assert json_case.result.workflow_plan.metadata["context_file_count"] == 1
    assert [invocation.tool_name for invocation in json_case.result.tool_invocations] == [
        "local_file_context",
        "json_analysis",
        "data_computation",
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
    csv_case = next(case for case in payload["case_results"] if "quarterly metrics dataset and summarize" in case["question"])
    hybrid_case = next(case for case in payload["case_results"] if "prioritize next" in case["question"])
    json_case = next(case for case in payload["case_results"] if "quarterly metrics JSON snapshot" in case["question"])
    assert "quarterly metrics dataset" in csv_case["question"]
    assert len(csv_case["result"]["tool_invocations"]) == 3
    assert hybrid_case["result"]["workflow_plan"]["workflow_name"] == "research_then_analysis_then_write"
    assert [invocation["tool_name"] for invocation in json_case["result"]["tool_invocations"]] == [
        "local_file_context",
        "json_analysis",
        "data_computation",
    ]
    record_payload = json.loads(records[0].read_text(encoding="utf-8"))
    assert record_payload["status"] == "passed"
    assert record_payload["report"]["passed_cases"] == len(ACCEPTANCE_QUESTIONS)
