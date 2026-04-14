from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from models.model_runner import ModelRequest, StructuredModelRunner
from schemas.task_schema import TaskEnvelope

InputModelT = TypeVar("InputModelT", bound=BaseModel)
OutputModelT = TypeVar("OutputModelT", bound=BaseModel)


class BaseWorker(ABC, Generic[InputModelT, OutputModelT]):
    name: str
    input_model: type[InputModelT]
    output_model: type[OutputModelT]

    def __init__(self, runner: StructuredModelRunner, prompt_manager: object) -> None:
        self.runner = runner
        self.prompt_manager = prompt_manager
        self._last_run_metadata: dict[str, object] = {}

    def run(self, task: TaskEnvelope) -> OutputModelT:
        validated_input = self.input_model.model_validate(task.input)
        request = self.build_request(validated_input)
        try:
            return self.runner.generate_structured(request, self.output_model)
        finally:
            self._last_run_metadata = self._collect_runner_metadata()

    def consume_last_run_metadata(self) -> dict[str, object]:
        metadata = dict(self._last_run_metadata)
        self._last_run_metadata = {}
        return metadata

    def _collect_runner_metadata(self) -> dict[str, object]:
        getter = getattr(self.runner, "get_last_invocation_metadata", None)
        if not callable(getter):
            return {}
        metadata = getter()
        return dict(metadata) if isinstance(metadata, dict) else {}

    @abstractmethod
    def build_request(self, payload: InputModelT) -> ModelRequest:
        raise NotImplementedError
