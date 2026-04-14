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

    def run(self, task: TaskEnvelope) -> OutputModelT:
        validated_input = self.input_model.model_validate(task.input)
        request = self.build_request(validated_input)
        return self.runner.generate_structured(request, self.output_model)

    @abstractmethod
    def build_request(self, payload: InputModelT) -> ModelRequest:
        raise NotImplementedError
