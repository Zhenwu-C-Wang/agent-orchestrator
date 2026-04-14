from __future__ import annotations

from schemas.task_schema import TaskType, WorkflowStep


class TaskRouter:
    """Defines the fixed workflow and task inputs for the MVP."""

    def plan(self, question: str) -> list[WorkflowStep]:
        return [
            WorkflowStep(
                task_type=TaskType.RESEARCH,
                worker_name="research",
                output_schema="ResearchResult",
            ),
            WorkflowStep(
                task_type=TaskType.WRITING,
                worker_name="writer",
                output_schema="FinalAnswer",
            ),
        ]

    def build_task_input(self, step: WorkflowStep, question: str, context: dict) -> dict:
        if step.task_type is TaskType.RESEARCH:
            return {"question": question}
        if step.task_type is TaskType.WRITING:
            return {
                "question": question,
                "research": context["research"].model_dump(),
            }
        raise ValueError(f"Unsupported task type: {step.task_type}")
