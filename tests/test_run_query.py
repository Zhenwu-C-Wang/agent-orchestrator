from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from main import build_supervisor
from tools.audit import AuditStore


REPO_ROOT = Path(__file__).resolve().parents[1]


def _seed_audit_records(tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("month,visits\nJan,10\nFeb,11\n", encoding="utf-8")
    success_supervisor = build_supervisor(
        runner_name="fake",
        enable_review=True,
        audit_dir=str(tmp_path),
        cache_dir=str(tmp_path / "cache"),
    )
    success_supervisor.run_with_context(
        "Analyze this dataset and summarize the biggest changes.",
        context_files=[str(csv_path)],
    )

    failure_supervisor = build_supervisor(
        runner_name="fake",
        audit_dir=str(tmp_path),
    )

    class BrokenWorker:
        def run(self, task) -> None:
            raise RuntimeError("writer exploded")

    failure_supervisor.workers["writer"] = BrokenWorker()
    with pytest.raises(RuntimeError, match="writer exploded"):
        failure_supervisor.run("How should I define worker schemas before adding more workers?")


def test_audit_store_lists_and_filters_records(tmp_path) -> None:
    _seed_audit_records(tmp_path)
    store = AuditStore(tmp_path)

    all_records = store.list_records()
    failed_records = store.list_records(status="failed")
    latest_record = store.latest_record()

    assert len(all_records) == 2
    assert len(failed_records) == 1
    assert failed_records[0].status == "failed"
    assert latest_record is not None
    assert latest_record.status == "failed"
    assert store.get_record(latest_record.run_id) is not None
    completed_record = store.latest_record(status="completed")
    assert completed_record is not None
    assert store.summarize_record(completed_record)["tool_invocation_count"] == 2


def test_runs_cli_lists_and_shows_records(tmp_path) -> None:
    _seed_audit_records(tmp_path)
    store = AuditStore(tmp_path)
    latest = store.latest_record()
    assert latest is not None

    listed = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.runs",
            "--audit-dir",
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
            "orchestrator.runs",
            "--audit-dir",
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
            "orchestrator.runs",
            "--audit-dir",
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
    assert any(entry["workflow_name"] == "analysis_then_write" for entry in listed_payload)
    assert any(entry["tool_invocation_count"] == 2 for entry in listed_payload)
    assert shown_payload["run_id"] == latest.run_id
    assert latest_payload["run_id"] == latest.run_id
