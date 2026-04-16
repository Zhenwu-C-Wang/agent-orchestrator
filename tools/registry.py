from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse
from typing import Any, Protocol

from schemas.tool_schema import ToolInvocation
from tools.errors import ConfigurationError, ToolExecutionError

_BACKTICKED_PATH_PATTERN = re.compile(r"`([^`]+)`")
_URL_PATTERN = re.compile(r"(?P<url>https?://[^\s`]+)")
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


def normalize_local_file_paths(
    paths: list[str | Path] | None,
    *,
    base_dir: str | Path | None = None,
) -> list[Path]:
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    resolved: list[Path] = []
    seen: set[Path] = set()
    for raw in paths or []:
        cleaned = str(raw).strip().strip("()[]{}<>\"'").rstrip(".,;:!?")
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


def validate_explicit_local_file_paths(
    paths: list[str | Path] | None,
    *,
    base_dir: str | Path | None = None,
) -> list[Path]:
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    resolved: list[Path] = []
    seen: set[Path] = set()
    invalid: list[str] = []
    for raw in paths or []:
        cleaned = str(raw).strip().strip("()[]{}<>\"'").rstrip(".,;:!?")
        if not cleaned:
            invalid.append(str(raw))
            continue
        candidate = Path(cleaned).expanduser()
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if not candidate.exists() or not candidate.is_file():
            invalid.append(cleaned)
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        resolved.append(candidate)
    if invalid:
        raise ConfigurationError(f"Invalid context file(s): {', '.join(invalid)}")
    return resolved


def normalize_http_urls(urls: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in urls or []:
        cleaned = str(raw).strip().strip("()[]{}<>\"'").rstrip(".,;:!?")
        if not cleaned:
            continue
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def validate_explicit_http_urls(urls: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    invalid: list[str] = []
    for raw in urls or []:
        cleaned = str(raw).strip().strip("()[]{}<>\"'").rstrip(".,;:!?")
        if not cleaned:
            invalid.append(str(raw))
            continue
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            invalid.append(cleaned)
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    if invalid:
        raise ConfigurationError(f"Invalid context URL(s): {', '.join(invalid)}")
    return normalized


def find_local_file_paths(question: str, *, base_dir: str | Path | None = None) -> list[Path]:
    candidates: list[str] = []
    candidates.extend(match.group(1) for match in _BACKTICKED_PATH_PATTERN.finditer(question))
    candidates.extend(match.group("path") for match in _PATH_TOKEN_PATTERN.finditer(question))
    return normalize_local_file_paths(candidates, base_dir=base_dir)


def find_http_urls(question: str) -> list[str]:
    candidates = [match.group("url") for match in _URL_PATTERN.finditer(question)]
    return normalize_http_urls(candidates)


class ToolManager:
    """Runs a bounded registry of local tools and records structured invocations."""

    def __init__(
        self,
        tools: list[Tool] | None = None,
        *,
        base_dir: str | Path | None = None,
        allow_question_file_paths: bool = False,
        allow_question_urls: bool = False,
    ) -> None:
        self.tools = list(tools or [])
        self.base_dir = Path(base_dir) if base_dir is not None else Path.cwd()
        self.allow_question_file_paths = allow_question_file_paths
        self.allow_question_urls = allow_question_urls

    def run_for_task(
        self,
        *,
        task_type: str,
        question: str,
        explicit_paths: list[str | Path] | None = None,
        explicit_urls: list[str] | None = None,
    ) -> tuple[dict[str, Any], list[ToolInvocation]]:
        candidate_paths = self._candidate_paths(question=question, explicit_paths=explicit_paths)
        candidate_urls = self._candidate_urls(question=question, explicit_urls=explicit_urls)
        base_context: dict[str, Any] = {
            "candidate_paths": candidate_paths,
            "candidate_urls": candidate_urls,
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
                failed_invocation = ToolInvocation(
                    tool_name=tool.name,
                    purpose=tool.purpose,
                    status="failed",
                    input_summary=question,
                    duration_ms=duration_ms,
                    metadata={},
                    error=str(exc),
                )
                invocations.append(failed_invocation)
                raise ToolExecutionError(
                    f"{tool.name} failed: {exc}",
                    invocations=invocations,
                ) from exc

        return combined_context, invocations

    def _candidate_paths(
        self,
        *,
        question: str,
        explicit_paths: list[str | Path] | None = None,
    ) -> list[Path]:
        discovered = (
            find_local_file_paths(question, base_dir=self.base_dir)
            if self.allow_question_file_paths
            else []
        )
        explicit = validate_explicit_local_file_paths(explicit_paths, base_dir=self.base_dir)
        ordered: list[Path] = []
        seen: set[Path] = set()
        for path in [*explicit, *discovered]:
            if path in seen:
                continue
            seen.add(path)
            ordered.append(path)
        return ordered

    def _candidate_urls(
        self,
        *,
        question: str,
        explicit_urls: list[str] | None = None,
    ) -> list[str]:
        discovered = find_http_urls(question) if self.allow_question_urls else []
        explicit = validate_explicit_http_urls(explicit_urls)
        ordered: list[str] = []
        seen: set[str] = set()
        for url in [*explicit, *discovered]:
            if url in seen:
                continue
            seen.add(url)
            ordered.append(url)
        return ordered
