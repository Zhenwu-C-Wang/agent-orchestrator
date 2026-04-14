from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from schemas.result_schema import WorkflowResult
from schemas.task_schema import TaskTrace


class AuditRecord(BaseModel):
    run_id: str
    status: str
    created_at: str
    question: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    traces: list[TaskTrace] = Field(default_factory=list)
    result: WorkflowResult | None = None
    error: str | None = None
