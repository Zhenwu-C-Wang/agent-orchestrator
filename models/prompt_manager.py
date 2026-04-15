from __future__ import annotations

import json

from models.model_runner import ModelRequest
from schemas.result_schema import AnalysisResult, FinalAnswer, ResearchResult


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

    def build_analysis_request(self, question: str) -> ModelRequest:
        return self.build_analysis_request_with_tools(question, tool_context={})

    def build_analysis_request_with_tools(
        self,
        question: str,
        *,
        tool_context: dict[str, object],
    ) -> ModelRequest:
        tool_context_json = json.dumps(tool_context, ensure_ascii=True)
        return ModelRequest(
            task_type="analysis",
            system_prompt=(
                "You are an analysis worker in a supervisor-driven system. "
                "Return only valid JSON that matches the required schema."
            ),
            user_prompt=(
                "Analyze the user's request and produce a concise analysis brief.\n"
                "Return JSON with keys: question, summary, findings, metrics, caveats.\n"
                "When tool context is provided, ground the analysis in that context and mention "
                "what was inspected.\n"
                f"Question: {question}"
                f"\nTool Context JSON: {tool_context_json}"
            ),
            payload={"question": question, "tool_context": tool_context},
        )

    def build_writer_request(
        self,
        question: str,
        research: ResearchResult | None = None,
        analysis: AnalysisResult | None = None,
    ) -> ModelRequest:
        if research is None and analysis is None:
            raise ValueError("build_writer_request requires either research or analysis.")
        intermediate_name = "ResearchResult" if research is not None else "AnalysisResult"
        intermediate_payload = (
            research.model_dump() if research is not None else analysis.model_dump()
        )
        return ModelRequest(
            task_type="writing",
            system_prompt=(
                "You are a writing worker in a supervisor-driven system. "
                "Return only valid JSON that matches the required schema."
            ),
            user_prompt=(
                "Use the intermediate worker result to produce the final answer.\n"
                "Return JSON with keys: question, answer, supporting_points, limitations.\n"
                f"Question: {question}\n"
                f"{intermediate_name} JSON: {json.dumps(intermediate_payload, ensure_ascii=True)}"
            ),
            payload={
                "question": question,
                "research": research.model_dump() if research is not None else None,
                "analysis": analysis.model_dump() if analysis is not None else None,
            },
        )

    def build_review_request(
        self,
        question: str,
        research: ResearchResult | None,
        analysis: AnalysisResult | None,
        final_answer: FinalAnswer,
    ) -> ModelRequest:
        if research is None and analysis is None:
            raise ValueError("build_review_request requires either research or analysis.")
        intermediate_name = "ResearchResult" if research is not None else "AnalysisResult"
        intermediate_payload = (
            research.model_dump() if research is not None else analysis.model_dump()
        )
        return ModelRequest(
            task_type="review",
            system_prompt=(
                "You are a review worker in a supervisor-driven system. "
                "Check whether the final answer stays supported by the intermediate worker result. "
                "Return only valid JSON that matches the required schema."
            ),
            user_prompt=(
                "Review whether the final answer is consistent with the intermediate worker result.\n"
                "Be strict about support and contradictions, but do not critique writing style.\n"
                "Return JSON with keys: question, consistent, verdict, issues, checked_points.\n"
                f"Question: {question}\n"
                f"{intermediate_name} JSON: {json.dumps(intermediate_payload, ensure_ascii=True)}\n"
                f"FinalAnswer JSON: {json.dumps(final_answer.model_dump(), ensure_ascii=True)}"
            ),
            payload={
                "question": question,
                "research": research.model_dump() if research is not None else None,
                "analysis": analysis.model_dump() if analysis is not None else None,
                "final_answer": final_answer.model_dump(),
            },
        )
