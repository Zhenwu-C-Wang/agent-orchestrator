from __future__ import annotations

from models.cached_runner import CachedModelRunner
from models.fake_runner import FakeModelRunner
from models.ollama_client import OllamaClient
from models.ollama_runner import OllamaModelRunner
from models.prompt_manager import PromptManager
from orchestrator.router import TaskRouter
from orchestrator.supervisor import Supervisor
from schemas.result_schema import WorkflowResult
from tools.audit import AuditLogger
from tools.cache import StructuredResultCache
from tools.retry import RetryPolicy
from workers.research_worker import ResearchWorker
from workers.review_worker import ReviewWorker
from workers.writer_worker import WriterWorker


def build_supervisor(
    *,
    runner_name: str,
    model: str = "llama3.1",
    base_url: str = "http://localhost:11434",
    enable_review: bool = False,
    audit_dir: str | None = None,
    cache_dir: str | None = None,
    max_retries: int = 1,
    retry_backoff_seconds: float = 0.25,
) -> Supervisor:
    model_name = None if runner_name == "fake" else model
    if runner_name == "fake":
        runner = FakeModelRunner()
    elif runner_name == "ollama":
        runner = OllamaModelRunner(
            model=model,
            client=OllamaClient(base_url=base_url),
            retry_policy=RetryPolicy(
                max_retries=max_retries,
                backoff_seconds=retry_backoff_seconds,
            ),
        )
    else:
        raise ValueError(f"Unsupported runner: {runner_name}")

    if cache_dir:
        runner = CachedModelRunner(
            runner=runner,
            cache=StructuredResultCache(cache_dir),
            namespace={
                "runner": runner_name,
                "model": model_name,
            },
        )

    prompt_manager = PromptManager()
    workers = {
        "research": ResearchWorker(runner=runner, prompt_manager=prompt_manager),
        "writer": WriterWorker(runner=runner, prompt_manager=prompt_manager),
        "review": ReviewWorker(runner=runner, prompt_manager=prompt_manager),
    }
    audit_logger = None
    if audit_dir:
        audit_logger = AuditLogger(
            audit_dir,
            metadata={
                "runner": runner_name,
                "model": model_name,
                "review_enabled": enable_review,
                "cache_enabled": bool(cache_dir),
                "cache_dir": cache_dir,
                "max_retries": max_retries,
                "retry_backoff_seconds": retry_backoff_seconds,
            },
        )
    return Supervisor(
        workers=workers,
        router=TaskRouter(enable_review=enable_review),
        audit_logger=audit_logger,
    )


def format_pretty(result: WorkflowResult) -> str:
    lines = [
        f"Question: {result.question}",
        "",
        "Research Summary:",
        result.research.summary,
        "",
        "Final Answer:",
        result.final_answer.answer,
        "",
        "Review Verdict:",
        result.review.verdict if result.review else "Review stage disabled.",
        "",
        "Supporting Points:",
        *[f"- {point}" for point in result.final_answer.supporting_points],
        "",
        "Trace:",
        *[
            f"- {trace.task_id} | {trace.worker_name} | {trace.status} | {trace.duration_ms}ms"
            for trace in result.traces
        ],
    ]
    return "\n".join(lines)
