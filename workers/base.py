from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from models.model_runner import ModelRequest, StructuredModelRunner
from schemas.task_schema import TaskEnvelope
from schemas.tool_schema import ToolInvocation

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
        self._last_tool_invocations: list[ToolInvocation] = []

    def run(self, task: TaskEnvelope) -> OutputModelT:
        validated_input = self.input_model.model_validate(task.input)
        self._last_tool_invocations = []
        request = self.build_request(validated_input)
        try:
            return self.runner.generate_structured(request, self.output_model)
        finally:
            self._last_run_metadata = self._merge_run_metadata(self._collect_runner_metadata())

    def consume_last_run_metadata(self) -> dict[str, object]:
        metadata = dict(self._last_run_metadata)
        self._last_run_metadata = {}
        return metadata

    def consume_last_tool_invocations(self) -> list[ToolInvocation]:
        invocations = list(self._last_tool_invocations)
        self._last_tool_invocations = []
        return invocations

    def set_last_tool_invocations(self, invocations: list[ToolInvocation]) -> None:
        self._last_tool_invocations = list(invocations)

    def _collect_runner_metadata(self) -> dict[str, object]:
        getter = getattr(self.runner, "get_last_invocation_metadata", None)
        if not callable(getter):
            return {}
        metadata = getter()
        return dict(metadata) if isinstance(metadata, dict) else {}

    def _merge_run_metadata(self, metadata: dict[str, object]) -> dict[str, object]:
        merged = dict(metadata)
        if self._last_tool_invocations:
            merged["tool_invocation_count"] = len(self._last_tool_invocations)
            merged["tool_names"] = [invocation.tool_name for invocation in self._last_tool_invocations]
            merged["tool_invocations"] = [
                invocation.model_dump() for invocation in self._last_tool_invocations
            ]
        return merged

    @abstractmethod
    def build_request(self, payload: InputModelT) -> ModelRequest:
        raise NotImplementedError
