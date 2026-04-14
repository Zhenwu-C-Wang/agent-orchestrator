from __future__ import annotations

from models.fake_runner import FakeModelRunner
from models.ollama_client import OllamaClient
from models.ollama_runner import OllamaModelRunner
from models.prompt_manager import PromptManager
from orchestrator.supervisor import Supervisor
from schemas.result_schema import WorkflowResult
from workers.research_worker import ResearchWorker
from workers.writer_worker import WriterWorker


def build_supervisor(
    *,
    runner_name: str,
    model: str = "llama3.1",
    base_url: str = "http://localhost:11434",
) -> Supervisor:
    if runner_name == "fake":
        runner = FakeModelRunner()
    elif runner_name == "ollama":
        runner = OllamaModelRunner(
            model=model,
            client=OllamaClient(base_url=base_url),
        )
    else:
        raise ValueError(f"Unsupported runner: {runner_name}")

    prompt_manager = PromptManager()
    workers = {
        "research": ResearchWorker(runner=runner, prompt_manager=prompt_manager),
        "writer": WriterWorker(runner=runner, prompt_manager=prompt_manager),
    }
    return Supervisor(workers=workers)


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
