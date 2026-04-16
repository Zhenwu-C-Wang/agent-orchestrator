from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

APP_DISPLAY_NAME = "Agent Orchestrator"
APP_SLUG = "agent-orchestrator"
UI_MODE_ENV_VAR = "AGENT_ORCHESTRATOR_UI_MODE"
UI_MODE_REPO = "repo"
UI_MODE_DESKTOP = "desktop"


@dataclass(frozen=True)
class UIRuntimePaths:
    mode: str
    root_dir: str
    audit_dir: str
    acceptance_dir: str
    cache_dir: str


def _resolve_mode(mode: str | None, env: Mapping[str, str]) -> str:
    return mode or env.get(UI_MODE_ENV_VAR, UI_MODE_REPO)


def _desktop_support_root(
    platform_name: str,
    home_dir: Path,
    env: Mapping[str, str],
) -> Path:
    if platform_name == "darwin":
        return home_dir / "Library" / "Application Support" / APP_DISPLAY_NAME
    if platform_name == "win32":
        base = Path(env.get("APPDATA") or (home_dir / "AppData" / "Roaming"))
        return base / APP_DISPLAY_NAME
    base = Path(env.get("XDG_DATA_HOME") or (home_dir / ".local" / "share"))
    return base / APP_SLUG


def _desktop_cache_root(
    platform_name: str,
    home_dir: Path,
    env: Mapping[str, str],
) -> Path:
    if platform_name == "darwin":
        return home_dir / "Library" / "Caches" / APP_DISPLAY_NAME
    if platform_name == "win32":
        base = Path(env.get("LOCALAPPDATA") or (home_dir / "AppData" / "Local"))
        return base / APP_DISPLAY_NAME / "Cache"
    base = Path(env.get("XDG_CACHE_HOME") or (home_dir / ".cache"))
    return base / APP_SLUG


def resolve_ui_runtime_paths(
    *,
    mode: str | None = None,
    platform_name: str | None = None,
    home_dir: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> UIRuntimePaths:
    resolved_env = env or os.environ
    resolved_mode = _resolve_mode(mode, resolved_env)

    if resolved_mode == UI_MODE_DESKTOP:
        current_platform = platform_name or sys.platform
        current_home = home_dir or Path.home()
        support_root = _desktop_support_root(current_platform, current_home, resolved_env)
        cache_root = _desktop_cache_root(current_platform, current_home, resolved_env)
        return UIRuntimePaths(
            mode=resolved_mode,
            root_dir=str(support_root),
            audit_dir=str(support_root / "runs"),
            acceptance_dir=str(support_root / "acceptance"),
            cache_dir=str(cache_root / "structured-results"),
        )

    return UIRuntimePaths(
        mode=UI_MODE_REPO,
        root_dir="artifacts",
        audit_dir="artifacts/runs",
        acceptance_dir="artifacts/acceptance",
        cache_dir="",
    )
