from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolInvocation(BaseModel):
    tool_name: str
    purpose: str
    status: str
    input_summary: str
    output_summary: str | None = None
    duration_ms: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
