from __future__ import annotations

from schemas.task_schema import TaskType, WorkflowPlan, WorkflowStep


class TaskPlanner:
    """Builds a bounded workflow plan from the user's request."""

    def __init__(self, *, enable_review: bool = False) -> None:
        self.enable_review = enable_review

    def build_plan(self, question: str) -> WorkflowPlan:
        lowered = question.lower()
        is_analysis = any(
            keyword in lowered
            for keyword in ("analyze", "analyse", "analysis", "dataset", "csv", "data file")
        )

        if is_analysis:
            steps = [
                WorkflowStep(
                    task_type=TaskType.ANALYSIS,
                    worker_name="analysis",
                    output_schema="AnalysisResult",
                ),
                WorkflowStep(
                    task_type=TaskType.WRITING,
                    worker_name="writer",
                    output_schema="FinalAnswer",
                ),
            ]
            rationale = (
                "The request looks data- or analysis-oriented, so the workflow starts with "
                "AnalysisWorker before synthesis."
            )
            workflow_name = "analysis_then_write"
        else:
            steps = [
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
            rationale = (
                "The request looks knowledge-oriented, so the workflow starts with "
                "ResearchWorker before synthesis."
            )
            workflow_name = "research_then_write"

        if self.enable_review:
            steps.append(
                WorkflowStep(
                    task_type=TaskType.REVIEW,
                    worker_name="review",
                    output_schema="ReviewResult",
                )
            )

        return WorkflowPlan(
            workflow_name=workflow_name,
            rationale=rationale,
            steps=steps,
            metadata={
                "review_enabled": self.enable_review,
                "question_type": "analysis" if is_analysis else "research",
            },
        )
