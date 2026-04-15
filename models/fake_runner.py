from __future__ import annotations

from models.model_runner import ModelRequest, StructuredModelRunner, StructuredModelT
from schemas.result_schema import AnalysisResult, FinalAnswer, ResearchResult, ReviewResult


class FakeModelRunner(StructuredModelRunner):
    """Deterministic runner used for tests and demos."""

    def __init__(self) -> None:
        self._last_invocation_metadata: dict[str, object] = {}

    def generate_structured(
        self,
        request: ModelRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredModelT:
        question = str(request.payload.get("question", "")).strip()
        self._last_invocation_metadata = {
            "runner": "fake",
            "model": None,
            "cache_enabled": False,
            "cache_hit": False,
            "cache_status": "disabled",
            "attempt_count": 1,
            "retry_count": 0,
        }

        if response_model is ResearchResult:
            payload = {
                "question": question,
                "summary": f"Research summary for: {question}",
                "key_points": [
                    "Start with a narrow workflow before adding more workers.",
                    "Keep intermediate worker outputs structured for composition.",
                    "Separate orchestration logic from model invocation details.",
                ],
                "caveats": [
                    "This research output is deterministic and not grounded in external sources.",
                    "A real local model may require stronger prompt constraints for schema stability.",
                ],
                "sources": ["internal:fake-runner"],
            }
            return response_model.model_validate(payload)

        if response_model is AnalysisResult:
            payload = {
                "question": question,
                "summary": f"Analysis summary for: {question}",
                "findings": [
                    "Start with a narrow analysis objective before adding more tooling.",
                    "Keep derived findings structured so downstream synthesis can stay deterministic.",
                    "Expose caveats whenever the analysis depends on local or incomplete context.",
                ],
                "metrics": [
                    "workflow_path=analysis_then_write",
                    "tool_mode=simulated",
                ],
                "caveats": [
                    "This analysis output is deterministic and does not execute real code.",
                    "Real tool-backed analysis will require stronger validation around inputs and outputs.",
                ],
            }
            return response_model.model_validate(payload)

        if response_model is FinalAnswer:
            research = request.payload.get("research")
            analysis = request.payload.get("analysis")
            if research is not None:
                summary = research["summary"]
                supporting_points = list(research["key_points"])
                limitations = list(research["caveats"])
                recommendation = (
                    "Recommended next step: keep the first release synchronous, "
                    "schema-first, and easy to inspect."
                )
            elif analysis is not None:
                summary = analysis["summary"]
                supporting_points = list(analysis["findings"])
                limitations = list(analysis["caveats"])
                recommendation = (
                    "Recommended next step: connect a guarded tool path so analysis "
                    "requests can inspect local data directly."
                )
            else:
                raise ValueError("Fake writer payload requires research or analysis.")
            limitations.append("The fake runner proves the orchestration contract, not model quality.")
            payload = {
                "question": question,
                "answer": f"{summary} {recommendation}",
                "supporting_points": supporting_points,
                "limitations": limitations,
            }
            return response_model.model_validate(payload)

        if response_model is ReviewResult:
            research = request.payload.get("research")
            analysis = request.payload.get("analysis")
            final_answer = request.payload["final_answer"]
            checked_points = list(final_answer["supporting_points"])
            if research is not None:
                checked_points = list(research["key_points"]) + checked_points
            if analysis is not None:
                checked_points = list(analysis["findings"]) + checked_points
            payload = {
                "question": question,
                "consistent": True,
                "verdict": "The final answer remains aligned with the intermediate worker output.",
                "issues": [],
                "checked_points": checked_points,
            }
            return response_model.model_validate(payload)

        raise ValueError(f"Unsupported response model for fake runner: {response_model.__name__}")

    def get_last_invocation_metadata(self) -> dict[str, object]:
        return dict(self._last_invocation_metadata)
