from pathlib import Path

from orchestrator.project_status import default_status_path, load_project_status


def test_load_project_status_from_default_file() -> None:
    status = load_project_status()

    assert status is not None
    assert status.current_phase == "Phase 1 (Practical V1)"
    assert status.current_milestone.startswith("M3:")
    assert status.next_milestone == "Phase 2: Dynamic Workflows"
    assert "tool registry" in " ".join(status.next_items).lower()


def test_load_project_status_returns_none_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing-status.json"

    assert load_project_status(missing) is None


def test_default_status_path_points_to_docs_snapshot() -> None:
    path = default_status_path()

    assert path.name == "project_status.json"
    assert path.parent.name == "docs"
