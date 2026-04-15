from __future__ import annotations

from schemas.task_schema import TaskType, WorkflowPlan, WorkflowStep


class TaskRouter:
    """Builds task inputs for a bounded workflow plan."""

    def plan(self, workflow_plan: WorkflowPlan) -> list[WorkflowStep]:
        return list(workflow_plan.steps)

    def build_task_input(self, step: WorkflowStep, question: str, context: dict) -> dict:
        if step.task_type is TaskType.RESEARCH:
            return {"question": question}
        if step.task_type is TaskType.ANALYSIS:
            return {
                "question": question,
                "context_files": list(context.get("context_files", [])),
                "context_urls": list(context.get("context_urls", [])),
                "research": (
                    context["research"].model_dump() if "research" in context else None
                ),
            }
        if step.task_type is TaskType.WRITING:
            return {
                "question": question,
                "research": (
                    context["research"].model_dump() if "research" in context else None
                ),
                "analysis": (
                    context["analysis"].model_dump() if "analysis" in context else None
                ),
            }
        if step.task_type is TaskType.REVIEW:
            return {
                "question": question,
                "research": (
                    context["research"].model_dump() if "research" in context else None
                ),
                "analysis": (
                    context["analysis"].model_dump() if "analysis" in context else None
                ),
                "final_answer": context["final_answer"].model_dump(),
            }
        raise ValueError(f"Unsupported task type: {step.task_type}")
