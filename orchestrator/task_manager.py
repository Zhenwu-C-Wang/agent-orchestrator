from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from schemas.task_schema import TaskEnvelope, TaskType


class TaskManager:
    """Creates task envelopes with monotonic task identifiers."""

    def __init__(self) -> None:
        self._counter = 0

    def create_task(
        self,
        task_type: TaskType,
        input_payload: Mapping[str, Any],
        output_schema: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> TaskEnvelope:
        self._counter += 1
        return TaskEnvelope(
            task_id=f"task-{self._counter:04d}",
            task_type=task_type,
            input=dict(input_payload),
            output_schema=output_schema,
            metadata=dict(metadata or {}),
        )
