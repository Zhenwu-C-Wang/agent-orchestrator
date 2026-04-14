from __future__ import annotations

import json

from models.model_runner import ModelRequest
from schemas.result_schema import FinalAnswer, ResearchResult


class PromptManager:
    """Builds task-specific prompts while keeping prompt text out of workers."""

    def build_research_request(self, question: str) -> ModelRequest:
        return ModelRequest(
            task_type="research",
            system_prompt=(
                "You are a research worker in a supervisor-driven system. "
                "Return only valid JSON that matches the required schema."
            ),
            user_prompt=(
                "Summarize the user's question into a concise research brief.\n"
                "Return JSON with keys: question, summary, key_points, caveats, sources.\n"
                f"Question: {question}"
            ),
            payload={"question": question},
        )

    def build_writer_request(self, question: str, research: ResearchResult) -> ModelRequest:
        return ModelRequest(
            task_type="writing",
            system_prompt=(
                "You are a writing worker in a supervisor-driven system. "
                "Return only valid JSON that matches the required schema."
            ),
            user_prompt=(
                "Use the research result to produce the final answer.\n"
                "Return JSON with keys: question, answer, supporting_points, limitations.\n"
                f"Question: {question}\n"
                f"Research JSON: {json.dumps(research.model_dump(), ensure_ascii=True)}"
            ),
            payload={"question": question, "research": research.model_dump()},
        )

    def build_review_request(
        self,
        question: str,
        research: ResearchResult,
        final_answer: FinalAnswer,
    ) -> ModelRequest:
        return ModelRequest(
            task_type="review",
            system_prompt=(
                "You are a review worker in a supervisor-driven system. "
                "Check whether the final answer stays supported by the research result. "
                "Return only valid JSON that matches the required schema."
            ),
            user_prompt=(
                "Review whether the final answer is consistent with the research result.\n"
                "Be strict about support and contradictions, but do not critique writing style.\n"
                "Return JSON with keys: question, consistent, verdict, issues, checked_points.\n"
                f"Question: {question}\n"
                f"Research JSON: {json.dumps(research.model_dump(), ensure_ascii=True)}\n"
                f"FinalAnswer JSON: {json.dumps(final_answer.model_dump(), ensure_ascii=True)}"
            ),
            payload={
                "question": question,
                "research": research.model_dump(),
                "final_answer": final_answer.model_dump(),
            },
        )
