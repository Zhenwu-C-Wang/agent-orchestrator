from __future__ import annotations

from models.cached_runner import CachedModelRunner
from models.fake_runner import FakeModelRunner
from models.ollama_client import OllamaClient
from models.ollama_runner import OllamaModelRunner
from models.prompt_manager import PromptManager
from orchestrator.planner import TaskPlanner
from orchestrator.router import TaskRouter
from orchestrator.supervisor import Supervisor
from schemas.result_schema import WorkflowResult
from tools.audit import AuditLogger
from tools.cache import StructuredResultCache
from tools.csv_analysis_tool import CSVAnalysisTool
from tools.data_computation_tool import DataComputationTool
from tools.errors import ConfigurationError
from tools.http_fetch_tool import HttpFetchTool
from tools.json_analysis_tool import JSONAnalysisTool
from tools.local_file_tool import LocalFileContextTool
from tools.registry import ToolManager
from tools.retry import RetryPolicy
from workers.analysis_worker import AnalysisWorker
from workers.comparison_worker import ComparisonWorker
from workers.research_worker import ResearchWorker
from workers.review_worker import ReviewWorker
from workers.writer_worker import WriterWorker


def build_supervisor(
    *,
    runner_name: str,
    model: str = "llama3.1",
    base_url: str = "http://localhost:11434",
    enable_review: bool = False,
    allow_inline_context_files: bool = False,
    allow_inline_context_urls: bool = False,
    audit_dir: str | None = None,
    cache_dir: str | None = None,
    cache_max_age_seconds: float | None = None,
    max_retries: int = 1,
    retry_backoff_seconds: float = 0.25,
) -> Supervisor:
    if max_retries < 0:
        raise ConfigurationError("max_retries must be greater than or equal to 0.")
    if retry_backoff_seconds < 0:
        raise ConfigurationError("retry_backoff_seconds must be greater than or equal to 0.")
    if cache_max_age_seconds is not None and cache_max_age_seconds < 0:
        raise ConfigurationError("cache_max_age_seconds must be greater than or equal to 0.")
    if cache_max_age_seconds is not None and not cache_dir:
        raise ConfigurationError("cache_max_age_seconds requires cache_dir.")

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
            cache=StructuredResultCache(
                cache_dir,
                max_age_seconds=cache_max_age_seconds,
            ),
            namespace={
                "runner": runner_name,
                "model": model_name,
            },
        )

    prompt_manager = PromptManager()
    tool_manager = ToolManager(
        tools=[
            LocalFileContextTool(),
            CSVAnalysisTool(),
            JSONAnalysisTool(),
            DataComputationTool(),
            HttpFetchTool(),
        ],
        allow_question_file_paths=allow_inline_context_files,
        allow_question_urls=allow_inline_context_urls,
    )
    workers = {
        "analysis": AnalysisWorker(
            runner=runner,
            prompt_manager=prompt_manager,
            tool_manager=tool_manager,
        ),
        "comparison": ComparisonWorker(
            runner=runner,
            prompt_manager=prompt_manager,
            tool_manager=tool_manager,
        ),
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
                "inline_context_file_discovery_enabled": allow_inline_context_files,
                "inline_context_url_discovery_enabled": allow_inline_context_urls,
                "cache_enabled": bool(cache_dir),
                "cache_dir": cache_dir,
                "cache_max_age_seconds": cache_max_age_seconds,
                "max_retries": max_retries,
                "retry_backoff_seconds": retry_backoff_seconds,
            },
        )
    return Supervisor(
        workers=workers,
        planner=TaskPlanner(
            enable_review=enable_review,
            allow_question_file_paths=allow_inline_context_files,
            allow_question_urls=allow_inline_context_urls,
        ),
        router=TaskRouter(),
        audit_logger=audit_logger,
    )


def format_pretty(result: WorkflowResult) -> str:
    lines = [
        f"Question: {result.question}",
        f"Workflow: {result.workflow_plan.workflow_name}",
        f"Rationale: {result.workflow_plan.rationale}",
        "",
    ]
    if result.research is not None:
        lines.extend(
            [
                "Research Summary:",
                result.research.summary,
                "",
            ]
        )
    if result.analysis is not None:
        lines.extend(
            [
                "Analysis Summary:",
                result.analysis.summary,
                "",
            ]
        )
    if result.comparison is not None:
        lines.extend(
            [
                "Comparison Summary:",
                result.comparison.summary,
                "",
            ]
        )
    lines.extend(
        [
            "Final Answer:",
            result.final_answer.answer,
            "",
            "Review Verdict:",
            result.review.verdict if result.review else "Review stage disabled.",
            "",
            "Supporting Points:",
            *[f"- {point}" for point in result.final_answer.supporting_points],
        ]
    )
    if result.tool_invocations:
        lines.extend(
            [
                "",
                "Tool Invocations:",
                *[
                    (
                        f"- {invocation.tool_name} | {invocation.status} | "
                        f"{invocation.output_summary or invocation.input_summary}"
                    )
                    for invocation in result.tool_invocations
                ],
            ]
        )
    lines.extend(
        [
            "",
            "Trace:",
            *[
                f"- {trace.task_id} | {trace.worker_name} | {trace.status} | {trace.duration_ms}ms"
                for trace in result.traces
            ],
        ]
    )
    return "\n".join(lines)


def format_markdown(result: WorkflowResult) -> str:
    lines = [
        "# Workflow Result",
        "",
        f"- Question: {result.question}",
        f"- Workflow: `{result.workflow_plan.workflow_name}`",
        f"- Rationale: {result.workflow_plan.rationale}",
        "",
    ]

    if result.research is not None:
        lines.extend(
            [
                "## Research",
                "",
                result.research.summary,
                "",
            ]
        )
        if result.research.key_points:
            lines.extend(["### Key Points", ""])
            lines.extend(f"- {point}" for point in result.research.key_points)
            lines.append("")
        if result.research.caveats:
            lines.extend(["### Caveats", ""])
            lines.extend(f"- {caveat}" for caveat in result.research.caveats)
            lines.append("")

    if result.analysis is not None:
        lines.extend(
            [
                "## Analysis",
                "",
                result.analysis.summary,
                "",
            ]
        )
        if result.analysis.findings:
            lines.extend(["### Findings", ""])
            lines.extend(f"- {finding}" for finding in result.analysis.findings)
            lines.append("")
        if result.analysis.metrics:
            lines.extend(["### Metrics", ""])
            lines.extend(f"- `{metric}`" for metric in result.analysis.metrics)
            lines.append("")
        if result.analysis.caveats:
            lines.extend(["### Caveats", ""])
            lines.extend(f"- {caveat}" for caveat in result.analysis.caveats)
            lines.append("")

    if result.comparison is not None:
        lines.extend(
            [
                "## Comparison",
                "",
                result.comparison.summary,
                "",
            ]
        )
        if result.comparison.comparisons:
            lines.extend(["### Comparisons", ""])
            lines.extend(f"- {item}" for item in result.comparison.comparisons)
            lines.append("")
        if result.comparison.metrics:
            lines.extend(["### Metrics", ""])
            lines.extend(f"- `{metric}`" for metric in result.comparison.metrics)
            lines.append("")
        if result.comparison.caveats:
            lines.extend(["### Caveats", ""])
            lines.extend(f"- {caveat}" for caveat in result.comparison.caveats)
            lines.append("")

    lines.extend(
        [
            "## Final Answer",
            "",
            result.final_answer.answer,
            "",
        ]
    )
    if result.final_answer.supporting_points:
        lines.extend(["### Supporting Points", ""])
        lines.extend(f"- {point}" for point in result.final_answer.supporting_points)
        lines.append("")
    if result.final_answer.limitations:
        lines.extend(["### Limitations", ""])
        lines.extend(f"- {limitation}" for limitation in result.final_answer.limitations)
        lines.append("")

    lines.extend(
        [
            "## Review",
            "",
            result.review.verdict if result.review else "Review stage disabled.",
            "",
        ]
    )

    if result.tool_invocations:
        lines.extend(["## Tool Invocations", ""])
        for invocation in result.tool_invocations:
            lines.extend(
                [
                    f"### `{invocation.tool_name}`",
                    "",
                    f"- Status: `{invocation.status}`",
                    f"- Purpose: {invocation.purpose}",
                    f"- Input: {invocation.input_summary}",
                    f"- Output: {invocation.output_summary or 'n/a'}",
                    f"- Duration: `{invocation.duration_ms}ms`",
                ]
            )
            if invocation.error:
                lines.append(f"- Error: {invocation.error}")
            lines.append("")

    lines.extend(
        [
            "## Trace",
            "",
            "| Task ID | Worker | Status | Duration |",
            "| --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        f"| `{trace.task_id}` | `{trace.worker_name}` | `{trace.status}` | `{trace.duration_ms}ms` |"
        for trace in result.traces
    )
    lines.append("")
    return "\n".join(lines)
