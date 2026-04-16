from __future__ import annotations

import os

import desktop_launcher
from orchestrator.runtime_paths import UI_MODE_DESKTOP, UI_MODE_ENV_VAR


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
        "global.developmentMode": False,
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
            "global.developmentMode": False,
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


def test_launch_desktop_ui_sets_desktop_mode_env(monkeypatch) -> None:
    fake_bootstrap = _FakeBootstrap()
    monkeypatch.delenv(UI_MODE_ENV_VAR, raising=False)

    desktop_launcher.launch_desktop_ui(
        open_browser=False,
        bootstrap_module=fake_bootstrap,
    )

    assert os.environ[UI_MODE_ENV_VAR] == UI_MODE_DESKTOP


def test_parse_args_supports_smoke_test() -> None:
    args = desktop_launcher.parse_args(["--smoke-test", "--diagnose-startup"])

    assert args.smoke_test is True
    assert args.diagnose_startup is True


def test_format_missing_dependency_message_mentions_module_name() -> None:
    exc = ModuleNotFoundError("No module named 'streamlit.web'")
    exc.name = "streamlit.web"

    message = desktop_launcher._format_missing_dependency_message(exc)

    assert "streamlit.web" in message
    assert "could not start" in message


def test_verify_required_app_modules_reports_missing_bundle_module() -> None:
    present_modules = set(desktop_launcher.REQUIRED_APP_MODULES) - {"tools.cache"}

    def _fake_module_loader(module_name: str) -> object:
        if module_name in present_modules:
            return object()
        exc = ModuleNotFoundError(f"No module named '{module_name}'")
        exc.name = module_name
        raise exc

    try:
        desktop_launcher._verify_required_app_modules(module_loader=_fake_module_loader)
    except SystemExit as exc:
        message = str(exc)
    else:  # pragma: no cover - defensive assertion path
        raise AssertionError("Expected SystemExit for a missing packaged module.")

    assert "tools.cache" in message
    assert "packaged app modules are missing" in message


def test_verify_desktop_packaging_ready_checks_bootstrap_and_modules(monkeypatch, tmp_path) -> None:
    recorded_calls: list[str] = []
    monkeypatch.setattr(desktop_launcher, "APP_PATH", tmp_path / "app.py")
    desktop_launcher.APP_PATH.write_text("# smoke test", encoding="utf-8")

    def _fake_bootstrap_loader() -> object:
        recorded_calls.append("bootstrap")
        return object()

    def _fake_module_loader(module_name: str) -> object:
        recorded_calls.append(module_name)
        return object()

    desktop_launcher.verify_desktop_packaging_ready(
        bootstrap_loader=_fake_bootstrap_loader,
        module_loader=_fake_module_loader,
    )

    assert recorded_calls[0] == "bootstrap"
    assert recorded_calls[1:] == list(desktop_launcher.REQUIRED_APP_MODULES)


def test_main_smoke_test_skips_ui_launch(monkeypatch) -> None:
    verify_calls: list[str] = []
    launch_calls: list[str] = []

    def _fake_verify() -> None:
        verify_calls.append("verified")

    def _fake_launch(*args, **kwargs) -> None:
        launch_calls.append("launched")

    monkeypatch.setattr(desktop_launcher, "verify_desktop_packaging_ready", _fake_verify)
    monkeypatch.setattr(desktop_launcher, "launch_desktop_ui", _fake_launch)

    desktop_launcher.main(["--smoke-test"])

    assert verify_calls == ["verified"]
    assert launch_calls == []
