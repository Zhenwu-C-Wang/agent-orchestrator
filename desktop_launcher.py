from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, Callable

from orchestrator.resource_paths import required_ui_resources, resolve_resource_root
from orchestrator.runtime_paths import (
    UI_MODE_DESKTOP,
    UI_MODE_ENV_VAR,
    resolve_ui_runtime_paths,
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8501
DEFAULT_BROWSER_TIMEOUT_SECONDS = 15.0
APP_DISPLAY_NAME = "Agent Orchestrator"
STARTUP_DIAGNOSTICS_FILENAME = "startup-diagnostics.json"
REQUIRED_APP_MODULES = (
    "orchestrator.bootstrap",
    "orchestrator.inspection",
    "orchestrator.planner",
    "orchestrator.project_status",
    "schemas.result_schema",
    "tools.acceptance",
    "tools.audit",
    "tools.cache",
)


@dataclass(frozen=True)
class WorkflowSmokeTestCase:
    name: str
    question: str
    context_filenames: tuple[str, ...]
    expected_workflow: str
    expected_tool_names: tuple[str, ...] = ()


WORKFLOW_SMOKE_TEST_CASES = (
    WorkflowSmokeTestCase(
        name="Research quickstart",
        question="How should I bootstrap a supervisor-worker agent system?",
        context_filenames=(),
        expected_workflow="research_then_write",
    ),
    WorkflowSmokeTestCase(
        name="CSV analysis quickstart",
        question="Summarize the most important changes in this data.",
        context_filenames=("quarterly_metrics.csv",),
        expected_workflow="analysis_then_write",
        expected_tool_names=("local_file_context", "csv_analysis", "data_computation"),
    ),
)


def get_resource_root() -> Path:
    return resolve_resource_root()


APP_PATH = get_resource_root() / "app.py"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Launch the Streamlit UI through a packaging-friendly Python entrypoint. "
            "This is intended as the basis for future desktop app packaging."
        )
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help="Host address for the local Streamlit server.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="Port for the local Streamlit server.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the local UI server without opening a browser window automatically.",
    )
    parser.add_argument(
        "--browser-timeout-seconds",
        type=float,
        default=DEFAULT_BROWSER_TIMEOUT_SECONDS,
        help="How long to wait for the local server before opening the browser.",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Verify packaged UI dependencies and required app modules, then exit.",
    )
    parser.add_argument(
        "--workflow-smoke-test",
        action="store_true",
        help=(
            "Run bundled fake-runner starter workflows so packaged-app first-run "
            "behavior can be validated without a repo checkout."
        ),
    )
    parser.add_argument(
        "--diagnose-startup",
        action="store_true",
        help="Print startup diagnostics for packaged-app troubleshooting.",
    )
    parser.add_argument(
        "--write-diagnostics",
        default=None,
        help=(
            "Optional path where startup diagnostics should also be written as JSON. "
            "Packaged failures already write to the desktop support directory by default."
        ),
    )
    return parser.parse_args(argv)


def build_launch_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def build_flag_options(host: str, port: int) -> dict[str, Any]:
    return {
        "server.headless": True,
        "server.address": host,
        "server.port": port,
        "browser.gatherUsageStats": False,
        "global.developmentMode": False,
    }


def _wait_for_port(
    host: str,
    port: int,
    timeout_seconds: float,
    poll_interval_seconds: float = 0.1,
) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=poll_interval_seconds):
                return True
        except OSError:
            time.sleep(poll_interval_seconds)
    return False


def _open_browser_when_ready(
    host: str,
    port: int,
    timeout_seconds: float,
    open_browser_fn: Callable[..., bool] = webbrowser.open,
) -> None:
    if _wait_for_port(host, port, timeout_seconds=timeout_seconds):
        open_browser_fn(build_launch_url(host, port), new=1)


def _schedule_browser_open(
    host: str,
    port: int,
    timeout_seconds: float,
    open_browser_fn: Callable[..., bool] = webbrowser.open,
) -> threading.Thread:
    thread = threading.Thread(
        target=_open_browser_when_ready,
        args=(host, port, timeout_seconds, open_browser_fn),
        daemon=True,
        name="agent-orchestrator-browser-launcher",
    )
    thread.start()
    return thread


def _format_missing_dependency_message(exc: ModuleNotFoundError) -> str:
    missing_module = exc.name or "unknown module"
    return (
        f"{APP_DISPLAY_NAME} could not start because a required UI dependency "
        f"is missing: `{missing_module}`. "
        "Rebuild the desktop app or install UI dependencies with "
        "`pip install -e '.[ui]'`."
    )


def _load_streamlit_bootstrap() -> Any:
    try:
        from streamlit.web import bootstrap
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency failure path
        raise SystemExit(_format_missing_dependency_message(exc)) from exc
    except Exception as exc:  # pragma: no cover - dependency failure path
        raise SystemExit(
            f"{APP_DISPLAY_NAME} could not initialize the packaged Streamlit UI: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    return bootstrap


def _load_supervisor_builder() -> Callable[..., Any]:
    try:
        from orchestrator.bootstrap import build_supervisor
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency failure path
        raise SystemExit(_format_missing_dependency_message(exc)) from exc
    except Exception as exc:  # pragma: no cover - dependency failure path
        raise SystemExit(
            f"{APP_DISPLAY_NAME} could not initialize the packaged workflow smoke test: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    return build_supervisor


def _verify_required_app_modules(
    module_loader: Callable[[str], object] = importlib.import_module,
) -> None:
    missing_modules: list[str] = []
    for module_name in REQUIRED_APP_MODULES:
        try:
            module_loader(module_name)
        except ModuleNotFoundError as exc:
            if exc.name == module_name:
                missing_modules.append(module_name)
                continue
            raise SystemExit(_format_missing_dependency_message(exc)) from exc

    if missing_modules:
        joined_modules = ", ".join(f"`{module_name}`" for module_name in missing_modules)
        raise SystemExit(
            f"{APP_DISPLAY_NAME} could not start because packaged app modules are missing: "
            f"{joined_modules}. Rebuild the desktop app so the full UI stack is bundled."
        )


def _verify_required_ui_resources(
    resources: tuple[tuple[str, Path], ...] | None = None,
) -> None:
    required_resources = resources or required_ui_resources()
    missing_resources = [
        relative_path for relative_path, resource_path in required_resources if not resource_path.exists()
    ]
    if missing_resources:
        joined_resources = ", ".join(f"`{relative_path}`" for relative_path in missing_resources)
        raise SystemExit(
            f"{APP_DISPLAY_NAME} could not start because bundled UI resources are missing: "
            f"{joined_resources}. Rebuild the desktop app so starter tasks and packaged status views are bundled."
        )


def verify_desktop_packaging_ready(
    bootstrap_loader: Callable[[], Any] = _load_streamlit_bootstrap,
    module_loader: Callable[[str], object] = importlib.import_module,
    resources: tuple[tuple[str, Path], ...] | None = None,
) -> None:
    bootstrap_loader()
    if not APP_PATH.exists():
        raise SystemExit(f"{APP_DISPLAY_NAME} could not find the packaged UI script at {APP_PATH}.")
    _verify_required_app_modules(module_loader=module_loader)
    _verify_required_ui_resources(resources=resources)


def _resolve_workflow_smoke_context_files(case: WorkflowSmokeTestCase) -> list[str]:
    from orchestrator.resource_paths import sample_data_path

    return [str(sample_data_path(filename)) for filename in case.context_filenames]


def _summarize_workflow_smoke_case(case: WorkflowSmokeTestCase, result: Any) -> dict[str, object]:
    workflow_name = result.workflow_plan.workflow_name
    tool_names = [invocation.tool_name for invocation in result.tool_invocations]
    tool_statuses = [
        {
            "tool_name": invocation.tool_name,
            "status": invocation.status,
        }
        for invocation in result.tool_invocations
    ]
    failed_tool_names = [
        invocation.tool_name
        for invocation in result.tool_invocations
        if invocation.status != "completed"
    ]

    if workflow_name != case.expected_workflow:
        raise SystemExit(
            f"Packaged workflow smoke test `{case.name}` selected `{workflow_name}`, "
            f"expected `{case.expected_workflow}`."
        )

    if case.expected_tool_names:
        missing_tool_names = [
            tool_name for tool_name in case.expected_tool_names if tool_name not in tool_names
        ]
        if missing_tool_names:
            joined_missing = ", ".join(f"`{tool_name}`" for tool_name in missing_tool_names)
            raise SystemExit(
                f"Packaged workflow smoke test `{case.name}` did not invoke the expected tools: "
                f"{joined_missing}."
            )
    elif tool_names:
        joined_tools = ", ".join(f"`{tool_name}`" for tool_name in tool_names)
        raise SystemExit(
            f"Packaged workflow smoke test `{case.name}` unexpectedly invoked tools: "
            f"{joined_tools}."
        )

    if failed_tool_names:
        joined_failed = ", ".join(f"`{tool_name}`" for tool_name in failed_tool_names)
        raise SystemExit(
            f"Packaged workflow smoke test `{case.name}` recorded failed tool invocations: "
            f"{joined_failed}."
        )

    final_answer = getattr(result.final_answer, "answer", "").strip()
    if not final_answer:
        raise SystemExit(
            f"Packaged workflow smoke test `{case.name}` did not produce a final answer."
        )

    return {
        "name": case.name,
        "question": case.question,
        "context_files": _resolve_workflow_smoke_context_files(case),
        "workflow_name": workflow_name,
        "tool_names": tool_names,
        "tool_statuses": tool_statuses,
        "trace_count": len(result.traces),
    }


def run_packaged_workflow_smoke_tests(
    supervisor_builder: Callable[..., Any] | None = None,
) -> dict[str, object]:
    os.environ[UI_MODE_ENV_VAR] = UI_MODE_DESKTOP
    runtime_paths = resolve_ui_runtime_paths(mode=UI_MODE_DESKTOP)
    audit_dir = Path(runtime_paths.audit_dir)
    before_records = sorted(audit_dir.glob("*.json")) if audit_dir.exists() else []

    build_supervisor = supervisor_builder or _load_supervisor_builder()
    supervisor = build_supervisor(
        runner_name="fake",
        audit_dir=runtime_paths.audit_dir,
    )

    case_summaries: list[dict[str, object]] = []
    for case in WORKFLOW_SMOKE_TEST_CASES:
        context_files = _resolve_workflow_smoke_context_files(case)
        result = supervisor.run_with_context(case.question, context_files=context_files)
        case_summaries.append(_summarize_workflow_smoke_case(case, result))

    after_records = sorted(audit_dir.glob("*.json")) if audit_dir.exists() else []
    new_record_count = len(after_records) - len(before_records)
    if new_record_count < len(WORKFLOW_SMOKE_TEST_CASES):
        raise SystemExit(
            "Packaged workflow smoke test did not persist the expected number of audit records "
            f"under `{runtime_paths.audit_dir}`."
        )

    return {
        "status": "completed",
        "runner": "fake",
        "runtime_paths": {
            "root_dir": runtime_paths.root_dir,
            "audit_dir": runtime_paths.audit_dir,
            "acceptance_dir": runtime_paths.acceptance_dir,
            "cache_dir": runtime_paths.cache_dir,
            "startup_diagnostics_path": runtime_paths.startup_diagnostics_path,
        },
        "audit_records_written": new_record_count,
        "cases": case_summaries,
    }


def _describe_module_spec(module_name: str) -> dict[str, object]:
    try:
        spec = importlib.util.find_spec(module_name)
    except Exception as exc:  # pragma: no cover - defensive diagnostics
        return {
            "module": module_name,
            "error": f"{type(exc).__name__}: {exc}",
        }

    if spec is None:
        return {
            "module": module_name,
            "found": False,
        }

    return {
        "module": module_name,
        "found": True,
        "origin": spec.origin,
        "submodule_search_locations": list(spec.submodule_search_locations or []),
    }


def build_startup_diagnostics() -> dict[str, object]:
    resource_root = get_resource_root()
    streamlit_dir = resource_root / "streamlit"
    runtime_paths = resolve_ui_runtime_paths(mode=UI_MODE_DESKTOP)
    streamlit_entries = []
    if streamlit_dir.exists():
        streamlit_entries = sorted(path.name for path in streamlit_dir.iterdir())[:20]

    return {
        "frozen": getattr(sys, "frozen", False),
        "executable": sys.executable,
        "resource_root": str(resource_root),
        "resource_root_exists": resource_root.exists(),
        "app_path": str(APP_PATH),
        "app_path_exists": APP_PATH.exists(),
        "desktop_runtime_paths": {
            "root_dir": runtime_paths.root_dir,
            "audit_dir": runtime_paths.audit_dir,
            "acceptance_dir": runtime_paths.acceptance_dir,
            "cache_dir": runtime_paths.cache_dir,
            "startup_diagnostics_path": str(default_startup_diagnostics_path()),
        },
        "sys_path": sys.path,
        "streamlit_dir": str(streamlit_dir),
        "streamlit_dir_exists": streamlit_dir.exists(),
        "streamlit_dir_entries": streamlit_entries,
        "required_ui_resources": [
            {
                "resource": relative_path,
                "path": str(resource_path),
                "exists": resource_path.exists(),
            }
            for relative_path, resource_path in required_ui_resources()
        ],
        "module_specs": [
            _describe_module_spec("streamlit"),
            _describe_module_spec("streamlit.web"),
            _describe_module_spec("orchestrator.bootstrap"),
        ],
    }


def build_workflow_smoke_test_diagnostics(
    workflow_smoke_test: dict[str, object],
) -> dict[str, object]:
    diagnostics = build_startup_diagnostics()
    diagnostics["workflow_smoke_test"] = workflow_smoke_test
    return diagnostics


def default_startup_diagnostics_path() -> Path:
    runtime_paths = resolve_ui_runtime_paths(mode=UI_MODE_DESKTOP)
    return Path(runtime_paths.startup_diagnostics_path)


def write_startup_diagnostics(
    *,
    target_path: str | Path | None = None,
    diagnostics: dict[str, object] | None = None,
) -> Path:
    destination = Path(target_path) if target_path is not None else default_startup_diagnostics_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = diagnostics or build_startup_diagnostics()
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination


def _persist_failure_diagnostics(
    *,
    error_message: str,
    target_path: str | Path | None = None,
) -> Path | None:
    if not getattr(sys, "frozen", False) and target_path is None:
        return None

    diagnostics = build_startup_diagnostics()
    diagnostics["startup_error"] = error_message
    return write_startup_diagnostics(target_path=target_path, diagnostics=diagnostics)


def _show_error_dialog(message: str) -> None:
    if sys.platform != "darwin":
        return

    escaped_message = message.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                (
                    f'display alert "{APP_DISPLAY_NAME}" '
                    f'message "{escaped_message}" as critical'
                ),
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return


def _handle_launch_failure(message: str) -> None:
    print(message, file=sys.stderr)
    if getattr(sys, "frozen", False):  # pragma: no branch - user-facing packaged path
        _show_error_dialog(message)


def launch_desktop_ui(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    open_browser: bool = True,
    browser_timeout_seconds: float = DEFAULT_BROWSER_TIMEOUT_SECONDS,
    bootstrap_module: Any | None = None,
    browser_scheduler: Callable[[str, int, float], object] | None = None,
) -> None:
    bootstrap = bootstrap_module or _load_streamlit_bootstrap()
    flags = build_flag_options(host, port)
    os.environ.setdefault(UI_MODE_ENV_VAR, UI_MODE_DESKTOP)

    # Fail fast in packaged mode if the first-run UI resources were not bundled.
    if getattr(sys, "frozen", False):
        _verify_required_ui_resources()

    if open_browser:
        scheduler = browser_scheduler or _schedule_browser_open
        scheduler(host, port, browser_timeout_seconds)

    bootstrap.load_config_options(flag_options=flags)
    bootstrap.run(str(APP_PATH), False, [], flags)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        if args.diagnose_startup:
            diagnostics = build_startup_diagnostics()
            print(json.dumps(diagnostics, indent=2))
            if args.write_diagnostics is not None:
                write_startup_diagnostics(
                    target_path=args.write_diagnostics,
                    diagnostics=diagnostics,
                )
        if args.smoke_test or args.workflow_smoke_test:
            verify_desktop_packaging_ready()
            workflow_smoke_test = None
            if args.workflow_smoke_test:
                workflow_smoke_test = run_packaged_workflow_smoke_tests()
            if args.write_diagnostics is not None:
                diagnostics = (
                    build_workflow_smoke_test_diagnostics(workflow_smoke_test)
                    if workflow_smoke_test is not None
                    else build_startup_diagnostics()
                )
                write_startup_diagnostics(
                    target_path=args.write_diagnostics,
                    diagnostics=diagnostics,
                )
            return

        launch_desktop_ui(
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser,
            browser_timeout_seconds=args.browser_timeout_seconds,
        )
    except SystemExit as exc:
        if exc.code not in (None, 0):
            diagnostics_path = _persist_failure_diagnostics(
                error_message=str(exc),
                target_path=args.write_diagnostics,
            )
            if diagnostics_path is not None:
                message_with_path = (
                    f"{exc}\nStartup diagnostics were written to: {diagnostics_path}"
                )
            else:
                message_with_path = str(exc)
            _handle_launch_failure(message_with_path)
            if diagnostics_path is not None:
                raise SystemExit(message_with_path)
        raise
    except Exception as exc:  # pragma: no cover - defensive startup path
        message = f"{APP_DISPLAY_NAME} failed to start: {type(exc).__name__}: {exc}"
        diagnostics_path = _persist_failure_diagnostics(
            error_message=message,
            target_path=args.write_diagnostics,
        )
        if diagnostics_path is not None:
            message = f"{message}\nStartup diagnostics were written to: {diagnostics_path}"
        _handle_launch_failure(message)
        raise SystemExit(message) from exc


if __name__ == "__main__":
    main()
