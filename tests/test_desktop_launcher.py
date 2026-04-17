from __future__ import annotations

import json
import os
from pathlib import Path

import desktop_launcher
from orchestrator.runtime_paths import UIRuntimePaths, UI_MODE_DESKTOP, UI_MODE_ENV_VAR


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
    args = desktop_launcher.parse_args(
        ["--smoke-test", "--diagnose-startup", "--write-diagnostics", "/tmp/diag.json"]
    )

    assert args.smoke_test is True
    assert args.diagnose_startup is True
    assert args.write_diagnostics == "/tmp/diag.json"


def test_default_startup_diagnostics_path_uses_desktop_support_root(monkeypatch) -> None:
    monkeypatch.setattr(
        desktop_launcher,
        "resolve_ui_runtime_paths",
        lambda mode=None: UIRuntimePaths(
            mode=UI_MODE_DESKTOP,
            root_dir="/tmp/agent-orchestrator-support",
            audit_dir="/tmp/agent-orchestrator-support/runs",
            acceptance_dir="/tmp/agent-orchestrator-support/acceptance",
            startup_diagnostics_path="/tmp/agent-orchestrator-support/startup-diagnostics.json",
            cache_dir="/tmp/agent-orchestrator-cache",
        ),
    )

    assert desktop_launcher.default_startup_diagnostics_path() == Path(
        "/tmp/agent-orchestrator-support/startup-diagnostics.json"
    )


def test_write_startup_diagnostics_persists_json(tmp_path: Path) -> None:
    target = tmp_path / "startup-diagnostics.json"
    payload = {"status": "ok"}

    written = desktop_launcher.write_startup_diagnostics(
        target_path=target,
        diagnostics=payload,
    )

    assert written == target
    assert json.loads(target.read_text(encoding="utf-8")) == payload


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


def test_verify_required_ui_resources_reports_missing_bundled_resource(tmp_path: Path) -> None:
    present = tmp_path / "docs" / "project_status.json"
    present.parent.mkdir(parents=True)
    present.write_text("{}", encoding="utf-8")
    missing = tmp_path / "docs" / "sample_data" / "quarterly_metrics.csv"

    try:
        desktop_launcher._verify_required_ui_resources(
            resources=(
                ("docs/project_status.json", present),
                ("docs/sample_data/quarterly_metrics.csv", missing),
            )
        )
    except SystemExit as exc:
        message = str(exc)
    else:  # pragma: no cover - defensive assertion path
        raise AssertionError("Expected SystemExit for a missing packaged resource.")

    assert "quarterly_metrics.csv" in message
    assert "bundled UI resources are missing" in message


def test_verify_desktop_packaging_ready_checks_bootstrap_and_modules(monkeypatch, tmp_path) -> None:
    recorded_calls: list[str] = []
    monkeypatch.setattr(desktop_launcher, "APP_PATH", tmp_path / "app.py")
    desktop_launcher.APP_PATH.write_text("# smoke test", encoding="utf-8")
    resources = (
        ("docs/project_status.json", tmp_path / "docs" / "project_status.json"),
        ("docs/sample_data/quarterly_metrics.csv", tmp_path / "docs" / "sample_data" / "quarterly_metrics.csv"),
    )
    for _, resource_path in resources:
        resource_path.parent.mkdir(parents=True, exist_ok=True)
        resource_path.write_text("ok", encoding="utf-8")

    def _fake_bootstrap_loader() -> object:
        recorded_calls.append("bootstrap")
        return object()

    def _fake_module_loader(module_name: str) -> object:
        recorded_calls.append(module_name)
        return object()

    desktop_launcher.verify_desktop_packaging_ready(
        bootstrap_loader=_fake_bootstrap_loader,
        module_loader=_fake_module_loader,
        resources=resources,
    )

    assert recorded_calls[0] == "bootstrap"
    assert recorded_calls[1:] == list(desktop_launcher.REQUIRED_APP_MODULES)


def test_launch_desktop_ui_verifies_resources_in_frozen_mode(monkeypatch) -> None:
    fake_bootstrap = _FakeBootstrap()
    verify_calls: list[str] = []
    monkeypatch.setattr(desktop_launcher.sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        desktop_launcher,
        "_verify_required_ui_resources",
        lambda resources=None: verify_calls.append("checked"),
    )

    desktop_launcher.launch_desktop_ui(
        open_browser=False,
        bootstrap_module=fake_bootstrap,
    )

    assert verify_calls == ["checked"]
    assert len(fake_bootstrap.run_calls) == 1


def test_main_smoke_test_writes_requested_diagnostics_file(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "diagnostics.json"
    monkeypatch.setattr(desktop_launcher, "verify_desktop_packaging_ready", lambda: None)
    monkeypatch.setattr(desktop_launcher, "build_startup_diagnostics", lambda: {"mode": "smoke-test"})

    desktop_launcher.main(["--smoke-test", "--write-diagnostics", str(target)])

    assert json.loads(target.read_text(encoding="utf-8")) == {"mode": "smoke-test"}


def test_main_persists_failure_diagnostics_for_frozen_bundle(monkeypatch, tmp_path: Path) -> None:
    diagnostics_path = tmp_path / "startup-diagnostics.json"
    handled_messages: list[str] = []

    monkeypatch.setattr(desktop_launcher, "verify_desktop_packaging_ready", lambda: (_ for _ in ()).throw(SystemExit("boom")))
    monkeypatch.setattr(desktop_launcher, "build_startup_diagnostics", lambda: {"mode": "frozen"})
    monkeypatch.setattr(desktop_launcher, "default_startup_diagnostics_path", lambda: diagnostics_path)
    monkeypatch.setattr(desktop_launcher, "_handle_launch_failure", handled_messages.append)
    monkeypatch.setattr(desktop_launcher.sys, "frozen", True, raising=False)

    try:
        desktop_launcher.main(["--smoke-test"])
    except SystemExit as exc:
        message = str(exc)
    else:  # pragma: no cover - defensive assertion path
        raise AssertionError("Expected SystemExit for smoke-test failure.")

    payload = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "frozen"
    assert payload["startup_error"] == "boom"
    assert str(diagnostics_path) in message
    assert handled_messages and str(diagnostics_path) in handled_messages[0]


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
