from __future__ import annotations

import sys
from collections.abc import Callable


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


class AuditQueryError(AgentOrchestratorError):
    exit_code = 7
    error_code = "audit-query-error"


class AcceptanceFailedError(AgentOrchestratorError):
    exit_code = 8
    error_code = "acceptance-failed"


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
