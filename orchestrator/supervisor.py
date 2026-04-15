from __future__ import annotations

from time import perf_counter

from orchestrator.planner import TaskPlanner
from orchestrator.router import TaskRouter
from orchestrator.task_manager import TaskManager
from schemas.result_schema import AnalysisResult, FinalAnswer, ResearchResult, ReviewResult, WorkflowResult
from schemas.task_schema import TaskTrace, TaskType
from schemas.tool_schema import ToolInvocation
from tools.audit import AuditLogger


class Supervisor:
    """Executes the fixed workflow and collects structured traces."""

    def __init__(
        self,
        workers: dict[str, object],
        planner: TaskPlanner | None = None,
        router: TaskRouter | None = None,
        task_manager: TaskManager | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.workers = workers
        self.planner = planner or TaskPlanner()
        self.router = router or TaskRouter()
        self.task_manager = task_manager or TaskManager()
        self.audit_logger = audit_logger

    def run(self, question: str) -> WorkflowResult:
        return self.run_with_context(question, context_files=None)

    def run_with_context(
        self,
        question: str,
        *,
        context_files: list[str] | None = None,
    ) -> WorkflowResult:
        normalized_context_files = list(context_files or [])
        context: dict[str, object] = {
            "context_files": normalized_context_files,
        }
        traces: list[TaskTrace] = []
        tool_invocations: list[ToolInvocation] = []
        workflow_plan = self.planner.build_plan(question, context_files=normalized_context_files)
        research_result: ResearchResult | None = None
        analysis_result: AnalysisResult | None = None
        final_answer: FinalAnswer | None = None
        review_result: ReviewResult | None = None

        for step in self.router.plan(workflow_plan):
            task_input = self.router.build_task_input(step, question, context)
            task = self.task_manager.create_task(
                task_type=step.task_type,
                input_payload=task_input,
                output_schema=step.output_schema,
                metadata={
                    "question": question,
                    "context_files": normalized_context_files,
                },
            )

            started_at = perf_counter()
            caught_exc: Exception | None = None
            trace_metadata: dict[str, object] = {}
            worker = self.workers[step.worker_name]
            try:
                result = worker.run(task)
                error = None
                status = "completed"
            except Exception as exc:
                result = None
                error = str(exc)
                status = "failed"
                caught_exc = exc
            finally:
                if hasattr(worker, "consume_last_run_metadata"):
                    trace_metadata = worker.consume_last_run_metadata()
                if hasattr(worker, "consume_last_tool_invocations"):
                    tool_invocations.extend(worker.consume_last_tool_invocations())
                duration_ms = int((perf_counter() - started_at) * 1000)
                traces.append(
                    TaskTrace(
                        task_id=task.task_id,
                        task_type=step.task_type,
                        worker_name=step.worker_name,
                        status=status,
                        duration_ms=duration_ms,
                        output_schema=step.output_schema,
                        error=error,
                        metadata=trace_metadata,
                    )
                )

            if caught_exc is not None:
                if self.audit_logger is not None:
                    self.audit_logger.record_failure(
                        question=question,
                        traces=traces,
                        error=error or str(caught_exc),
                    )
                raise caught_exc

            if step.task_type is TaskType.RESEARCH:
                research_result = result
                context["research"] = result
            elif step.task_type is TaskType.ANALYSIS:
                analysis_result = result
                context["analysis"] = result
            elif step.task_type is TaskType.WRITING:
                final_answer = result
                context["final_answer"] = result
            elif step.task_type is TaskType.REVIEW:
                review_result = result
                context["review"] = result

        if final_answer is None:
            raise RuntimeError("Workflow did not produce a final answer output.")
        if research_result is None and analysis_result is None:
            raise RuntimeError("Workflow did not produce an intermediate worker output.")

        workflow_result = WorkflowResult(
            question=question,
            workflow_plan=workflow_plan,
            research=research_result,
            analysis=analysis_result,
            final_answer=final_answer,
            review=review_result,
            tool_invocations=tool_invocations,
            traces=traces,
        )
        if self.audit_logger is not None:
            self.audit_logger.record_success(workflow_result)
        return workflow_result
