from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    RESEARCH = "research"
    WRITING = "writing"
    REVIEW = "review"


class TaskEnvelope(BaseModel):
    task_id: str
    task_type: TaskType
    input: dict[str, Any]
    output_schema: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowStep(BaseModel):
    task_type: TaskType
    worker_name: str
    output_schema: str


class TaskTrace(BaseModel):
    task_id: str
    task_type: TaskType
    worker_name: str
    status: str
    duration_ms: int
    output_schema: str
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
