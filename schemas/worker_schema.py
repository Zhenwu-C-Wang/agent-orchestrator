from __future__ import annotations

from pydantic import BaseModel, model_validator

from schemas.result_schema import AnalysisResult, FinalAnswer, ResearchResult


class ResearchTaskInput(BaseModel):
    question: str


class AnalysisTaskInput(BaseModel):
    question: str
    context_files: list[str] = []
    context_urls: list[str] = []
    research: ResearchResult | None = None


class WriterTaskInput(BaseModel):
    question: str
    research: ResearchResult | None = None
    analysis: AnalysisResult | None = None

    @model_validator(mode="after")
    def validate_intermediate_result(self) -> "WriterTaskInput":
        if self.research is None and self.analysis is None:
            raise ValueError("WriterTaskInput requires either research or analysis.")
        return self


class ReviewTaskInput(BaseModel):
    question: str
    research: ResearchResult | None = None
    analysis: AnalysisResult | None = None
    final_answer: FinalAnswer

    @model_validator(mode="after")
    def validate_intermediate_result(self) -> "ReviewTaskInput":
        if self.research is None and self.analysis is None:
            raise ValueError("ReviewTaskInput requires either research or analysis.")
        return self
