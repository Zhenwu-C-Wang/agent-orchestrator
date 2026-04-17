from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from orchestrator.resource_paths import project_status_path


class ProjectStatus(BaseModel):
    current_phase: str
    current_milestone: str
    next_milestone: str | None = None
    summary: str
    completed_items: list[str] = Field(default_factory=list)
    next_items: list[str] = Field(default_factory=list)


def default_status_path() -> Path:
    return project_status_path(anchor_file=__file__)


def load_project_status(path: str | Path | None = None) -> ProjectStatus | None:
    target = Path(path) if path is not None else default_status_path()
    if not target.exists():
        return None

    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        return ProjectStatus.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError):
        return None
