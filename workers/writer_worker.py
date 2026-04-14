from __future__ import annotations

from models.model_runner import ModelRequest, StructuredModelRunner
from models.prompt_manager import PromptManager
from schemas.result_schema import FinalAnswer
from schemas.worker_schema import WriterTaskInput
from workers.base import BaseWorker


class WriterWorker(BaseWorker[WriterTaskInput, FinalAnswer]):
    name = "writer"
    input_model = WriterTaskInput
    output_model = FinalAnswer

    def __init__(self, runner: StructuredModelRunner, prompt_manager: PromptManager) -> None:
        super().__init__(runner=runner, prompt_manager=prompt_manager)

    def build_request(self, payload: WriterTaskInput) -> ModelRequest:
        return self.prompt_manager.build_writer_request(
            question=payload.question,
            research=payload.research,
        )
