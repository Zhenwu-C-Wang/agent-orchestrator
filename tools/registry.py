from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol

from schemas.tool_schema import ToolInvocation

_BACKTICKED_PATH_PATTERN = re.compile(r"`([^`]+)`")
_PATH_TOKEN_PATTERN = re.compile(
    r"(?P<path>(?:\./|\.\./|/)[^\s,;:]+|[A-Za-z0-9_.\-/]+\.(?:csv|txt|md|json|py|yaml|yml))"
)


@dataclass
class ToolExecutionResult:
    context_updates: dict[str, Any] = field(default_factory=dict)
    input_summary: str | None = None
    output_summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Tool(Protocol):
    name: str
    purpose: str

    def supports(self, *, task_type: str, question: str, context: dict[str, Any]) -> bool:
        ...

    def run(self, *, task_type: str, question: str, context: dict[str, Any]) -> ToolExecutionResult:
        ...


def find_local_file_paths(question: str, *, base_dir: str | Path | None = None) -> list[Path]:
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    candidates: list[str] = []
    candidates.extend(match.group(1) for match in _BACKTICKED_PATH_PATTERN.finditer(question))
    candidates.extend(match.group("path") for match in _PATH_TOKEN_PATTERN.finditer(question))

    resolved: list[Path] = []
    seen: set[Path] = set()
    for raw in candidates:
        cleaned = raw.strip().strip("()[]{}<>\"'").rstrip(".,;:!?")
        if not cleaned:
            continue
        candidate = Path(cleaned).expanduser()
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if candidate in seen or not candidate.exists() or not candidate.is_file():
            continue
        seen.add(candidate)
        resolved.append(candidate)
    return resolved


class ToolManager:
    """Runs a bounded registry of local tools and records structured invocations."""

    def __init__(
        self,
        tools: list[Tool] | None = None,
        *,
        base_dir: str | Path | None = None,
    ) -> None:
        self.tools = list(tools or [])
        self.base_dir = Path(base_dir) if base_dir is not None else Path.cwd()

    def run_for_task(self, *, task_type: str, question: str) -> tuple[dict[str, Any], list[ToolInvocation]]:
        candidate_paths = find_local_file_paths(question, base_dir=self.base_dir)
        base_context: dict[str, Any] = {
            "candidate_paths": candidate_paths,
        }
        combined_context: dict[str, Any] = {}
        invocations: list[ToolInvocation] = []

        for tool in self.tools:
            context = {**base_context, **combined_context}
            if not tool.supports(task_type=task_type, question=question, context=context):
                continue

            started_at = perf_counter()
            try:
                execution = tool.run(task_type=task_type, question=question, context=context)
                duration_ms = int((perf_counter() - started_at) * 1000)
                combined_context.update(execution.context_updates)
                invocations.append(
                    ToolInvocation(
                        tool_name=tool.name,
                        purpose=tool.purpose,
                        status="completed",
                        input_summary=execution.input_summary or question,
                        output_summary=execution.output_summary,
                        duration_ms=duration_ms,
                        metadata=execution.metadata,
                    )
                )
            except Exception as exc:
                duration_ms = int((perf_counter() - started_at) * 1000)
                invocations.append(
                    ToolInvocation(
                        tool_name=tool.name,
                        purpose=tool.purpose,
                        status="failed",
                        input_summary=question,
                        duration_ms=duration_ms,
                        metadata={},
                        error=str(exc),
                    )
                )

        return combined_context, invocations
