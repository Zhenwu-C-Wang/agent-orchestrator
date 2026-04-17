from __future__ import annotations

import argparse
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
from orchestrator.runtime_paths import UI_MODE_DESKTOP, UI_MODE_ENV_VAR

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8501
DEFAULT_BROWSER_TIMEOUT_SECONDS = 15.0
APP_DISPLAY_NAME = "Agent Orchestrator"
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


def get_resource_root() -> Path:
    return resolve_resource_root(anchor_file=__file__)


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
        "--diagnose-startup",
        action="store_true",
        help="Print startup diagnostics for packaged-app troubleshooting.",
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
    required_resources = resources or required_ui_resources(anchor_file=__file__)
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
            for relative_path, resource_path in required_ui_resources(anchor_file=__file__)
        ],
        "module_specs": [
            _describe_module_spec("streamlit"),
            _describe_module_spec("streamlit.web"),
            _describe_module_spec("orchestrator.bootstrap"),
        ],
    }


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
            print(json.dumps(build_startup_diagnostics(), indent=2))
        if args.smoke_test:
            verify_desktop_packaging_ready()
            return

        launch_desktop_ui(
            host=args.host,
            port=args.port,
            open_browser=not args.no_browser,
            browser_timeout_seconds=args.browser_timeout_seconds,
        )
    except SystemExit as exc:
        if exc.code not in (None, 0):
            _handle_launch_failure(str(exc))
        raise
    except Exception as exc:  # pragma: no cover - defensive startup path
        message = f"{APP_DISPLAY_NAME} failed to start: {type(exc).__name__}: {exc}"
        _handle_launch_failure(message)
        raise SystemExit(message) from exc


if __name__ == "__main__":
    main()
