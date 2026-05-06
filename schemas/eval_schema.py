from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from schemas.result_schema import WorkflowResult


class EvalCaseResult(BaseModel):
    case_id: str
    category: str
    question: str
    passed: bool
    duration_ms: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked: bool = False
    expected_block: bool = False
    tool_error: bool = False
    attack_succeeded: bool = False
    false_block: bool = False
    token_estimate: int = 0
    cost_estimate_usd: float = 0.0
    trace_order: list[str] = Field(default_factory=list)
    tool_names: list[str] = Field(default_factory=list)
    result: WorkflowResult | None = None


class EvalMetrics(BaseModel):
    total_cases: int
    passed_cases: int
    failed_cases: int
    success_rate: float
    tool_error_rate: float
    policy_block_rate: float
    false_block_rate: float
    attack_success_rate: float
    p50_latency_ms: int
    p95_latency_ms: int
    token_estimate: int
    cost_estimate_usd: float


class EvalVariantReport(BaseModel):
    name: str
    description: str
    runner: str
    model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    metrics: EvalMetrics
    case_results: list[EvalCaseResult] = Field(default_factory=list)


class EvalReport(BaseModel):
    suite_name: str
    total_cases: int
    variants: list[EvalVariantReport] = Field(default_factory=list)
