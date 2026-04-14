from __future__ import annotations

from models.model_runner import ModelRequest, StructuredModelRunner
from models.prompt_manager import PromptManager
from schemas.result_schema import ReviewResult
from schemas.worker_schema import ReviewTaskInput
from workers.base import BaseWorker


class ReviewWorker(BaseWorker[ReviewTaskInput, ReviewResult]):
    name = "review"
    input_model = ReviewTaskInput
    output_model = ReviewResult

    def __init__(self, runner: StructuredModelRunner, prompt_manager: PromptManager) -> None:
        super().__init__(runner=runner, prompt_manager=prompt_manager)

    def build_request(self, payload: ReviewTaskInput) -> ModelRequest:
        return self.prompt_manager.build_review_request(
            question=payload.question,
            research=payload.research,
            final_answer=payload.final_answer,
        )
