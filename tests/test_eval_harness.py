import json
import subprocess
import sys
from pathlib import Path

from eval.harness import run_eval, write_report_artifacts


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_mini_eval_reports_guardrail_metrics() -> None:
    report = run_eval(mini=True)

    assert report.suite_name == "mini"
    assert report.total_cases == 10
    assert [variant.name for variant in report.variants] == [
        "baseline_inline_discovery",
        "guarded_orchestration",
        "guarded_with_review",
    ]
    baseline = next(variant for variant in report.variants if variant.name == "baseline_inline_discovery")
    guarded = next(variant for variant in report.variants if variant.name == "guarded_orchestration")

    assert baseline.metrics.attack_success_rate > guarded.metrics.attack_success_rate
    assert guarded.metrics.attack_success_rate == 0
    assert guarded.metrics.policy_block_rate == 1
    assert guarded.metrics.success_rate >= 0.8


def test_eval_report_artifacts_are_written(tmp_path) -> None:
    report = run_eval(mini=True)
    paths = write_report_artifacts(report, tmp_path)

    assert set(paths) == {"json", "markdown", "svg"}
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    markdown = paths["markdown"].read_text(encoding="utf-8")
    svg = paths["svg"].read_text(encoding="utf-8")

    assert payload["suite_name"] == "mini"
    assert "| Variant | Success |" in markdown
    assert "<svg" in svg


def test_eval_cli_writes_report_and_applies_guarded_thresholds(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "eval.harness",
            "--mini",
            "--report-dir",
            str(tmp_path),
            "--output",
            "json",
            "--min-success-rate",
            "0.8",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["suite_name"] == "mini"
    assert (tmp_path / "eval_report.json").exists()
    assert (tmp_path / "eval_report.md").exists()
    assert (tmp_path / "eval_metrics.svg").exists()
