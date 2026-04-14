from __future__ import annotations

from models.model_runner import ModelRequest, StructuredModelRunner, StructuredModelT
from schemas.result_schema import FinalAnswer, ResearchResult


class FakeModelRunner(StructuredModelRunner):
    """Deterministic runner used for tests and demos."""

    def generate_structured(
        self,
        request: ModelRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredModelT:
        question = str(request.payload.get("question", "")).strip()

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

        if response_model is FinalAnswer:
            research = request.payload["research"]
            summary = research["summary"]
            supporting_points = list(research["key_points"])
            limitations = list(research["caveats"]) + [
                "The fake runner proves the orchestration contract, not model quality.",
            ]
            payload = {
                "question": question,
                "answer": (
                    f"{summary} "
                    "Recommended next step: keep the first release synchronous, "
                    "schema-first, and easy to inspect."
                ),
                "supporting_points": supporting_points,
                "limitations": limitations,
            }
            return response_model.model_validate(payload)

        raise ValueError(f"Unsupported response model for fake runner: {response_model.__name__}")
