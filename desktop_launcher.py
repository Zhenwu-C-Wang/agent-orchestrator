from __future__ import annotations

import argparse
import socket
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, Callable

APP_PATH = Path(__file__).resolve().parent / "app.py"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8501
DEFAULT_BROWSER_TIMEOUT_SECONDS = 15.0


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
    return parser.parse_args(argv)


def build_launch_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def build_flag_options(host: str, port: int) -> dict[str, Any]:
    return {
        "server.headless": True,
        "server.address": host,
        "server.port": port,
        "browser.gatherUsageStats": False,
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


def _load_streamlit_bootstrap() -> Any:
    try:
        from streamlit.web import bootstrap
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency failure path
        raise SystemExit(
            "Streamlit UI dependencies are not installed. "
            "Install them with `pip install -e '.[ui]'` or use a packaged desktop build."
        ) from exc
    return bootstrap


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

    if open_browser:
        scheduler = browser_scheduler or _schedule_browser_open
        scheduler(host, port, browser_timeout_seconds)

    bootstrap.load_config_options(flag_options=flags)
    bootstrap.run(str(APP_PATH), False, [], flags)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    launch_desktop_ui(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
        browser_timeout_seconds=args.browser_timeout_seconds,
    )


if __name__ == "__main__":
    main()
