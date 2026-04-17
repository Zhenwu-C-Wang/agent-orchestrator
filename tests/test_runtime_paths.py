from __future__ import annotations

from pathlib import Path

from orchestrator.runtime_paths import UI_MODE_DESKTOP, UI_MODE_ENV_VAR, resolve_ui_runtime_paths


def test_repo_ui_runtime_paths_remain_artifact_relative() -> None:
    paths = resolve_ui_runtime_paths(mode="repo")

    assert paths.mode == "repo"
    assert paths.root_dir == "artifacts"
    assert paths.audit_dir == "artifacts/runs"
    assert paths.acceptance_dir == "artifacts/acceptance"
    assert paths.startup_diagnostics_path == "artifacts/startup-diagnostics.json"
    assert paths.cache_dir == ""


def test_desktop_ui_runtime_paths_use_macos_app_support_locations() -> None:
    home_dir = Path("/Users/tester")
    paths = resolve_ui_runtime_paths(
        mode=UI_MODE_DESKTOP,
        platform_name="darwin",
        home_dir=home_dir,
        env={},
    )

    assert paths.root_dir == "/Users/tester/Library/Application Support/Agent Orchestrator"
    assert paths.audit_dir.endswith("/Library/Application Support/Agent Orchestrator/runs")
    assert paths.acceptance_dir.endswith("/Library/Application Support/Agent Orchestrator/acceptance")
    assert paths.startup_diagnostics_path.endswith(
        "/Library/Application Support/Agent Orchestrator/startup-diagnostics.json"
    )
    assert paths.cache_dir == "/Users/tester/Library/Caches/Agent Orchestrator/structured-results"


def test_desktop_ui_runtime_paths_honor_xdg_locations_on_linux() -> None:
    home_dir = Path("/home/tester")
    paths = resolve_ui_runtime_paths(
        platform_name="linux",
        home_dir=home_dir,
        env={
            UI_MODE_ENV_VAR: UI_MODE_DESKTOP,
            "XDG_DATA_HOME": "/tmp/xdg-data",
            "XDG_CACHE_HOME": "/tmp/xdg-cache",
        },
    )

    assert paths.root_dir == "/tmp/xdg-data/agent-orchestrator"
    assert paths.audit_dir == "/tmp/xdg-data/agent-orchestrator/runs"
    assert paths.acceptance_dir == "/tmp/xdg-data/agent-orchestrator/acceptance"
    assert paths.startup_diagnostics_path == "/tmp/xdg-data/agent-orchestrator/startup-diagnostics.json"
    assert paths.cache_dir == "/tmp/xdg-cache/agent-orchestrator/structured-results"
