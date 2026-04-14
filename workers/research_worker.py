from __future__ import annotations

from models.model_runner import ModelRequest, StructuredModelRunner
from models.prompt_manager import PromptManager
from schemas.result_schema import ResearchResult
from schemas.worker_schema import ResearchTaskInput
from workers.base import BaseWorker


class ResearchWorker(BaseWorker[ResearchTaskInput, ResearchResult]):
    name = "research"
    input_model = ResearchTaskInput
    output_model = ResearchResult

    def __init__(self, runner: StructuredModelRunner, prompt_manager: PromptManager) -> None:
        super().__init__(runner=runner, prompt_manager=prompt_manager)

    def build_request(self, payload: ResearchTaskInput) -> ModelRequest:
        return self.prompt_manager.build_research_request(payload.question)
