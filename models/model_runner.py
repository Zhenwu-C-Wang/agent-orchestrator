from __future__ import annotations

from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, Field

StructuredModelT = TypeVar("StructuredModelT", bound=BaseModel)


class ModelRequest(BaseModel):
    task_type: str
    system_prompt: str
    user_prompt: str
    payload: dict[str, Any] = Field(default_factory=dict)


class StructuredModelRunner(Protocol):
    def generate_structured(
        self,
        request: ModelRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredModelT:
        ...

    def get_last_invocation_metadata(self) -> dict[str, Any]:
        ...
