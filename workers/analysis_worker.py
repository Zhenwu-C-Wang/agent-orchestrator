from __future__ import annotations

from models.model_runner import ModelRequest, StructuredModelRunner
from models.prompt_manager import PromptManager
from schemas.result_schema import AnalysisResult
from schemas.worker_schema import AnalysisTaskInput
from workers.base import BaseWorker


class AnalysisWorker(BaseWorker[AnalysisTaskInput, AnalysisResult]):
    name = "analysis"
    input_model = AnalysisTaskInput
    output_model = AnalysisResult

    def __init__(self, runner: StructuredModelRunner, prompt_manager: PromptManager) -> None:
        super().__init__(runner=runner, prompt_manager=prompt_manager)

    def build_request(self, payload: AnalysisTaskInput) -> ModelRequest:
        return self.prompt_manager.build_analysis_request(payload.question)
