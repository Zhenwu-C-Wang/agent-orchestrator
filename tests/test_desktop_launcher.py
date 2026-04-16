from __future__ import annotations

import desktop_launcher


class _FakeBootstrap:
    def __init__(self) -> None:
        self.load_calls: list[dict[str, object]] = []
        self.run_calls: list[tuple[str, bool, list[str], dict[str, object]]] = []

    def load_config_options(self, *, flag_options: dict[str, object]) -> None:
        self.load_calls.append(flag_options)

    def run(
        self,
        main_script_path: str,
        is_hello: bool,
        args: list[str],
        flag_options: dict[str, object],
        *,
        stop_immediately_for_testing: bool = False,
    ) -> None:
        self.run_calls.append((main_script_path, is_hello, args, flag_options))


def test_build_launch_url() -> None:
    assert desktop_launcher.build_launch_url("127.0.0.1", 9000) == "http://127.0.0.1:9000"


def test_build_flag_options() -> None:
    assert desktop_launcher.build_flag_options("127.0.0.1", 8600) == {
        "server.headless": True,
        "server.address": "127.0.0.1",
        "server.port": 8600,
        "browser.gatherUsageStats": False,
    }


def test_launch_desktop_ui_invokes_streamlit_bootstrap() -> None:
    fake_bootstrap = _FakeBootstrap()
    scheduled_calls: list[tuple[str, int, float]] = []

    def _fake_scheduler(host: str, port: int, timeout_seconds: float) -> None:
        scheduled_calls.append((host, port, timeout_seconds))

    desktop_launcher.launch_desktop_ui(
        host="127.0.0.1",
        port=8601,
        browser_timeout_seconds=9.0,
        bootstrap_module=fake_bootstrap,
        browser_scheduler=_fake_scheduler,
    )

    assert scheduled_calls == [("127.0.0.1", 8601, 9.0)]
    assert fake_bootstrap.load_calls == [
        {
            "server.headless": True,
            "server.address": "127.0.0.1",
            "server.port": 8601,
            "browser.gatherUsageStats": False,
        }
    ]
    assert len(fake_bootstrap.run_calls) == 1
    main_script_path, is_hello, args, flag_options = fake_bootstrap.run_calls[0]
    assert main_script_path == str(desktop_launcher.APP_PATH)
    assert is_hello is False
    assert args == []
    assert flag_options["server.port"] == 8601


def test_launch_desktop_ui_skips_browser_when_disabled() -> None:
    fake_bootstrap = _FakeBootstrap()
    scheduled_calls: list[tuple[str, int, float]] = []

    def _fake_scheduler(host: str, port: int, timeout_seconds: float) -> None:
        scheduled_calls.append((host, port, timeout_seconds))

    desktop_launcher.launch_desktop_ui(
        open_browser=False,
        bootstrap_module=fake_bootstrap,
        browser_scheduler=_fake_scheduler,
    )

    assert scheduled_calls == []
    assert len(fake_bootstrap.run_calls) == 1
