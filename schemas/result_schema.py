from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.task_schema import TaskTrace


class ResearchResult(BaseModel):
    question: str
    summary: str
    key_points: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class FinalAnswer(BaseModel):
    question: str
    answer: str
    supporting_points: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    question: str
    consistent: bool
    verdict: str
    issues: list[str] = Field(default_factory=list)
    checked_points: list[str] = Field(default_factory=list)


class WorkflowResult(BaseModel):
    question: str
    research: ResearchResult
    final_answer: FinalAnswer
    review: ReviewResult | None = None
    traces: list[TaskTrace] = Field(default_factory=list)
