from __future__ import annotations

from models.model_runner import ModelRequest, StructuredModelRunner
from models.prompt_manager import PromptManager
from schemas.result_schema import AnalysisResult
from schemas.task_schema import TaskEnvelope
from schemas.worker_schema import AnalysisTaskInput
from tools.registry import ToolManager
from workers.base import BaseWorker


class AnalysisWorker(BaseWorker[AnalysisTaskInput, AnalysisResult]):
    name = "analysis"
    input_model = AnalysisTaskInput
    output_model = AnalysisResult

    def __init__(
        self,
        runner: StructuredModelRunner,
        prompt_manager: PromptManager,
        tool_manager: ToolManager | None = None,
    ) -> None:
        super().__init__(runner=runner, prompt_manager=prompt_manager)
        self.tool_manager = tool_manager

    def build_request(self, payload: AnalysisTaskInput) -> ModelRequest:
        return self.prompt_manager.build_analysis_request(payload.question)

    def run(self, task: TaskEnvelope) -> AnalysisResult:
        validated_input = self.input_model.model_validate(task.input)
        self.set_last_tool_invocations([])
        tool_context: dict[str, object] = {}
        tool_invocations = []
        if self.tool_manager is not None:
            tool_context, tool_invocations = self.tool_manager.run_for_task(
                task_type=self.name,
                question=validated_input.question,
                explicit_paths=validated_input.context_files,
            )
        self.set_last_tool_invocations(tool_invocations)
        request = self.prompt_manager.build_analysis_request_with_tools(
            validated_input.question,
            tool_context=tool_context,
        )
        try:
            return self.runner.generate_structured(request, self.output_model)
        finally:
            self._last_run_metadata = self._merge_run_metadata(self._collect_runner_metadata())
