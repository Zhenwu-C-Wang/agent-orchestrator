from pathlib import Path

from orchestrator.resource_paths import (
    project_status_path,
    required_ui_resources,
    resolve_resource_root,
    sample_data_path,
)


def test_resolve_resource_root_uses_repo_layout_from_anchor_file(tmp_path: Path) -> None:
    anchor = tmp_path / "orchestrator" / "resource_paths.py"
    anchor.parent.mkdir(parents=True)
    anchor.write_text("# anchor", encoding="utf-8")

    assert resolve_resource_root(anchor_file=anchor) == tmp_path


def test_resolve_resource_root_prefers_meipass_for_frozen_bundle(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    assert resolve_resource_root(frozen=True, meipass=bundle_root) == bundle_root


def test_required_ui_resources_point_to_expected_docs_files(tmp_path: Path) -> None:
    anchor = tmp_path / "orchestrator" / "resource_paths.py"
    anchor.parent.mkdir(parents=True)
    anchor.write_text("# anchor", encoding="utf-8")

    resources = dict(required_ui_resources(anchor_file=anchor))

    assert project_status_path(anchor_file=anchor) == tmp_path / "docs" / "project_status.json"
    assert sample_data_path("quarterly_metrics.csv", anchor_file=anchor) == (
        tmp_path / "docs" / "sample_data" / "quarterly_metrics.csv"
    )
    assert set(resources) == {
        "docs/project_status.json",
        "docs/sample_data/quarterly_metrics.csv",
        "docs/sample_data/quarterly_metrics.json",
        "docs/sample_data/quarterly_metrics_baseline.csv",
    }
