from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from schemas.result_schema import WorkflowResult


class AcceptanceCaseResult(BaseModel):
    question: str
    passed: bool
    duration_ms: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace_order: list[str] = Field(default_factory=list)
    result: WorkflowResult | None = None


class AcceptanceReport(BaseModel):
    runner: str
    model: str | None = None
    enable_review: bool = False
    total_cases: int
    passed_cases: int
    failed_cases: int
    case_results: list[AcceptanceCaseResult] = Field(default_factory=list)


class AcceptanceRecord(BaseModel):
    run_id: str
    status: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    report: AcceptanceReport
