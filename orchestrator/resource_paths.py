from __future__ import annotations

import sys
from pathlib import Path

PROJECT_STATUS_RESOURCE = ("docs", "project_status.json")
SAMPLE_DATA_FILENAMES = (
    "quarterly_metrics.csv",
    "quarterly_metrics.json",
    "quarterly_metrics_baseline.csv",
)


def resolve_resource_root(
    *,
    anchor_file: str | Path | None = None,
    frozen: bool | None = None,
    meipass: str | Path | None = None,
) -> Path:
    resolved_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    resolved_meipass = getattr(sys, "_MEIPASS", None) if meipass is None else meipass

    if resolved_frozen and resolved_meipass is not None:
        return Path(resolved_meipass)

    resolved_anchor = Path(anchor_file) if anchor_file is not None else Path(__file__)
    return resolved_anchor.resolve().parents[1]


def resolve_resource_path(
    *parts: str,
    anchor_file: str | Path | None = None,
    frozen: bool | None = None,
    meipass: str | Path | None = None,
) -> Path:
    return resolve_resource_root(
        anchor_file=anchor_file,
        frozen=frozen,
        meipass=meipass,
    ).joinpath(*parts)


def project_status_path(
    *,
    anchor_file: str | Path | None = None,
    frozen: bool | None = None,
    meipass: str | Path | None = None,
) -> Path:
    return resolve_resource_path(
        *PROJECT_STATUS_RESOURCE,
        anchor_file=anchor_file,
        frozen=frozen,
        meipass=meipass,
    )


def sample_data_path(
    filename: str,
    *,
    anchor_file: str | Path | None = None,
    frozen: bool | None = None,
    meipass: str | Path | None = None,
) -> Path:
    return resolve_resource_path(
        "docs",
        "sample_data",
        filename,
        anchor_file=anchor_file,
        frozen=frozen,
        meipass=meipass,
    )


def required_ui_resources(
    *,
    anchor_file: str | Path | None = None,
    frozen: bool | None = None,
    meipass: str | Path | None = None,
) -> tuple[tuple[str, Path], ...]:
    return (
        ("docs/project_status.json", project_status_path(
            anchor_file=anchor_file,
            frozen=frozen,
            meipass=meipass,
        )),
        *(
            (
                f"docs/sample_data/{filename}",
                sample_data_path(
                    filename,
                    anchor_file=anchor_file,
                    frozen=frozen,
                    meipass=meipass,
                ),
            )
            for filename in SAMPLE_DATA_FILENAMES
        ),
    )
