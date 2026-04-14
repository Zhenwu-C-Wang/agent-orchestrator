from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from main import build_supervisor


REPO_ROOT = Path(__file__).resolve().parents[1]


def _seed_cache(cache_dir: Path) -> None:
    supervisor = build_supervisor(
        runner_name="fake",
        enable_review=True,
        cache_dir=str(cache_dir),
    )
    supervisor.run("How should I bootstrap a supervisor-worker system?")


def _age_cache_files(cache_dir: Path, *, age_seconds: int) -> None:
    timestamp = (datetime.now(timezone.utc) - timedelta(seconds=age_seconds)).isoformat()
    for path in cache_dir.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["created_at"] = timestamp
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_cache_cli_lists_and_summarizes_entries(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    _seed_cache(cache_dir)

    listed = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.cache",
            "--cache-dir",
            str(cache_dir),
            "--output",
            "json",
            "list",
            "--limit",
            "2",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    listed_payload = json.loads(listed.stdout)

    stats = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.cache",
            "--cache-dir",
            str(cache_dir),
            "--output",
            "json",
            "stats",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    stats_payload = json.loads(stats.stdout)

    assert len(listed_payload) == 2
    assert all(entry["expired"] is False for entry in listed_payload)
    assert stats_payload["total_entries"] == 3
    assert stats_payload["active_entries"] == 3
    assert stats_payload["expired_entries"] == 0


def test_cache_cli_prunes_expired_entries_and_clears(tmp_path) -> None:
    cache_dir = tmp_path / "cache"
    _seed_cache(cache_dir)
    _age_cache_files(cache_dir, age_seconds=120)

    pruned = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.cache",
            "--cache-dir",
            str(cache_dir),
            "--max-age-seconds",
            "60",
            "--output",
            "json",
            "prune",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    pruned_payload = json.loads(pruned.stdout)

    _seed_cache(cache_dir)
    cleared = subprocess.run(
        [
            sys.executable,
            "-m",
            "orchestrator.cache",
            "--cache-dir",
            str(cache_dir),
            "--output",
            "json",
            "clear",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    cleared_payload = json.loads(cleared.stdout)

    assert pruned_payload["removed_entries"] == 3
    assert pruned_payload["summary"]["total_entries"] == 0
    assert cleared_payload["removed_entries"] == 3
    assert cleared_payload["summary"]["total_entries"] == 0
