from __future__ import annotations

import sys
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from schemas.tool_schema import ToolInvocation


class AgentOrchestratorError(Exception):
    exit_code = 1
    error_code = "application-error"


class ConfigurationError(AgentOrchestratorError):
    exit_code = 3
    error_code = "configuration-error"


class ModelInvocationError(AgentOrchestratorError):
    exit_code = 4
    error_code = "model-invocation-error"


class ModelResponseFormatError(AgentOrchestratorError):
    exit_code = 5
    error_code = "model-response-format-error"


class WorkflowExecutionError(AgentOrchestratorError):
    exit_code = 6
    error_code = "workflow-execution-error"


class ToolExecutionError(WorkflowExecutionError):
    def __init__(
        self,
        message: str,
        *,
        invocations: list["ToolInvocation"] | None = None,
    ) -> None:
        super().__init__(message)
        self.invocations = list(invocations or [])


class AuditQueryError(AgentOrchestratorError):
    exit_code = 7
    error_code = "audit-query-error"


class AcceptanceFailedError(AgentOrchestratorError):
    exit_code = 8
    error_code = "acceptance-failed"


class CacheQueryError(AgentOrchestratorError):
    exit_code = 9
    error_code = "cache-query-error"


class AcceptanceQueryError(AgentOrchestratorError):
    exit_code = 10
    error_code = "acceptance-query-error"


def run_cli(entrypoint: Callable[[], int | None]) -> None:
    try:
        exit_code = entrypoint()
        raise SystemExit(0 if exit_code is None else exit_code)
    except AgentOrchestratorError as exc:
        print(f"{exc.error_code}: {exc}", file=sys.stderr)
        raise SystemExit(exc.exit_code) from exc
    except Exception as exc:
        error = WorkflowExecutionError(str(exc))
        print(f"{error.error_code}: {error}", file=sys.stderr)
        raise SystemExit(error.exit_code) from exc
