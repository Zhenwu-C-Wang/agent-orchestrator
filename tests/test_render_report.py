from orchestrator.bootstrap import build_supervisor
from scripts.render_report import render_audit_report


def test_render_audit_report_summarizes_runs(tmp_path) -> None:
    supervisor = build_supervisor(runner_name="fake", audit_dir=str(tmp_path))
    supervisor.run("How should I bootstrap a supervisor-worker agent system?")

    report = render_audit_report(tmp_path)

    assert "# Orchestration Run Report" in report
    assert "- Runs: `1`" in report
    assert "| `research` |" in report
    assert "No failures recorded." in report
