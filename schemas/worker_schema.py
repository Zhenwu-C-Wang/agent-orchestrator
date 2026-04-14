from __future__ import annotations

from pydantic import BaseModel

from schemas.result_schema import FinalAnswer, ResearchResult


class ResearchTaskInput(BaseModel):
    question: str


class WriterTaskInput(BaseModel):
    question: str
    research: ResearchResult


class ReviewTaskInput(BaseModel):
    question: str
    research: ResearchResult
    final_answer: FinalAnswer
