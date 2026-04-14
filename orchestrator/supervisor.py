from __future__ import annotations

from time import perf_counter

from orchestrator.router import TaskRouter
from orchestrator.task_manager import TaskManager
from schemas.result_schema import FinalAnswer, ResearchResult, ReviewResult, WorkflowResult
from schemas.task_schema import TaskTrace, TaskType
from tools.audit import AuditLogger


class Supervisor:
    """Executes the fixed workflow and collects structured traces."""

    def __init__(
        self,
        workers: dict[str, object],
        router: TaskRouter | None = None,
        task_manager: TaskManager | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.workers = workers
        self.router = router or TaskRouter()
        self.task_manager = task_manager or TaskManager()
        self.audit_logger = audit_logger

    def run(self, question: str) -> WorkflowResult:
        context: dict[str, object] = {}
        traces: list[TaskTrace] = []
        research_result: ResearchResult | None = None
        final_answer: FinalAnswer | None = None
        review_result: ReviewResult | None = None

        for step in self.router.plan(question):
            task_input = self.router.build_task_input(step, question, context)
            task = self.task_manager.create_task(
                task_type=step.task_type,
                input_payload=task_input,
                output_schema=step.output_schema,
                metadata={"question": question},
            )

            started_at = perf_counter()
            caught_exc: Exception | None = None
            try:
                worker = self.workers[step.worker_name]
                result = worker.run(task)
                error = None
                status = "completed"
            except Exception as exc:
                result = None
                error = str(exc)
                status = "failed"
                caught_exc = exc
            finally:
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
            elif step.task_type is TaskType.WRITING:
                final_answer = result
                context["final_answer"] = result
            elif step.task_type is TaskType.REVIEW:
                review_result = result
                context["review"] = result

        if research_result is None or final_answer is None:
            raise RuntimeError("Workflow did not produce both research and final answer outputs.")

        workflow_result = WorkflowResult(
            question=question,
            research=research_result,
            final_answer=final_answer,
            review=review_result,
            traces=traces,
        )
        if self.audit_logger is not None:
            self.audit_logger.record_success(workflow_result)
        return workflow_result
