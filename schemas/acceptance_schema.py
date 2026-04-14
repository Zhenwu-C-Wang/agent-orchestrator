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


class AcceptanceCaseComparison(BaseModel):
    question: str
    current_present: bool
    baseline_present: bool
    current_passed: bool | None = None
    baseline_passed: bool | None = None
    changed: bool
    regression: bool = False
    improvement: bool = False
    current_error_count: int = 0
    baseline_error_count: int = 0
    current_warning_count: int = 0
    baseline_warning_count: int = 0
    duration_ms_delta: int | None = None


class AcceptanceComparison(BaseModel):
    current_run_id: str
    baseline_run_id: str
    current_status: str
    baseline_status: str
    current_created_at: str
    baseline_created_at: str
    current_passed_cases: int
    baseline_passed_cases: int
    passed_cases_delta: int
    current_failed_cases: int
    baseline_failed_cases: int
    failed_cases_delta: int
    current_warning_count: int
    baseline_warning_count: int
    warning_count_delta: int
    regression_count: int
    improvement_count: int
    case_comparisons: list[AcceptanceCaseComparison] = Field(default_factory=list)
