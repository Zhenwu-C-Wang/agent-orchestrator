from __future__ import annotations

from pydantic import BaseModel

from schemas.result_schema import ResearchResult


class ResearchTaskInput(BaseModel):
    question: str


class WriterTaskInput(BaseModel):
    question: str
    research: ResearchResult
