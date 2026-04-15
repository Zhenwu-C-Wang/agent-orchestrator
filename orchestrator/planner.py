from __future__ import annotations

from schemas.task_schema import TaskType, WorkflowPlan, WorkflowStep
from tools.registry import find_http_urls, find_local_file_paths


class TaskPlanner:
    """Builds a bounded workflow plan from the user's request."""

    def __init__(
        self,
        *,
        enable_review: bool = False,
        allow_question_file_paths: bool = False,
        allow_question_urls: bool = False,
    ) -> None:
        self.enable_review = enable_review
        self.allow_question_file_paths = allow_question_file_paths
        self.allow_question_urls = allow_question_urls

    def build_plan(
        self,
        question: str,
        *,
        context_files: list[str] | None = None,
        context_urls: list[str] | None = None,
    ) -> WorkflowPlan:
        lowered = question.lower()
        discovered_local_files = (
            find_local_file_paths(question) if self.allow_question_file_paths else []
        )
        discovered_context_urls = find_http_urls(question) if self.allow_question_urls else []
        has_local_files = bool(discovered_local_files or context_files)
        has_context_urls = bool(discovered_context_urls or context_urls)
        is_analysis = any(
            keyword in lowered
            for keyword in ("analyze", "analyse", "analysis", "dataset", "csv", "data file")
        ) or has_local_files or has_context_urls

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
            if has_local_files:
                rationale = (
                    "The request references one or more local files, so the workflow starts with "
                    "AnalysisWorker and its tool-backed analysis path before synthesis."
                )
            elif has_context_urls:
                rationale = (
                    "The request references one or more URLs, so the workflow starts with "
                    "AnalysisWorker and its HTTP-backed analysis path before synthesis."
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
                "has_local_files": has_local_files,
                "context_file_count": len(context_files or []),
                "discovered_context_file_count": len(discovered_local_files),
                "inline_context_file_discovery_enabled": self.allow_question_file_paths,
                "has_context_urls": has_context_urls,
                "context_url_count": len(context_urls or []),
                "discovered_context_url_count": len(discovered_context_urls),
                "inline_context_url_discovery_enabled": self.allow_question_urls,
            },
        )
