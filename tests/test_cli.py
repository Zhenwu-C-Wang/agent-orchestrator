from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


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
