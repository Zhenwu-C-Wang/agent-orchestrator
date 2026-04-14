from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from schemas.acceptance_schema import AcceptanceRecord, AcceptanceReport


class AcceptanceLogger:
    """Persists one JSON acceptance record per acceptance run."""

    def __init__(self, directory: str | Path, metadata: dict[str, Any] | None = None) -> None:
        self.directory = Path(directory)
        self.metadata = dict(metadata or {})

    def record_report(self, report: AcceptanceReport) -> Path:
        record = AcceptanceRecord(
            run_id=self._new_run_id(),
            status="passed" if report.failed_cases == 0 else "failed",
            created_at=self._timestamp_iso(),
            metadata=self.metadata,
            report=report,
        )
        return self._write_record(record)

    def _write_record(self, record: AcceptanceRecord) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        runner_slug = record.report.runner
        status_slug = record.status
        target = self.directory / f"{record.run_id}-{runner_slug}-{status_slug}.json"
        target.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return target

    def _new_run_id(self) -> str:
        return f"{self._timestamp_compact()}-{uuid4().hex[:8]}"

    @staticmethod
    def _timestamp_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _timestamp_compact() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


class AcceptanceStore:
    """Reads persisted acceptance artifacts for status inspection."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def list_records(
        self,
        *,
        limit: int | None = None,
        status: str | None = None,
    ) -> list[AcceptanceRecord]:
        records: list[AcceptanceRecord] = []
        for path in self._paths():
            record = self._load_path(path)
            if record is None:
                continue
            if status is not None and record.status != status:
                continue
            records.append(record)

        records.sort(key=lambda record: (record.created_at, record.run_id), reverse=True)
        if limit is not None:
            return records[:limit]
        return records

    def get_record(self, run_id: str) -> AcceptanceRecord | None:
        direct_matches = sorted(self.directory.glob(f"{run_id}-*.json"))
        for path in direct_matches:
            record = self._load_path(path)
            if record is not None:
                return record

        for record in self.list_records():
            if record.run_id == run_id:
                return record
        return None

    def latest_record(self, *, status: str | None = None) -> AcceptanceRecord | None:
        records = self.list_records(limit=1, status=status)
        return records[0] if records else None

    def summarize_record(self, record: AcceptanceRecord) -> dict[str, Any]:
        warning_count = sum(len(case.warnings) for case in record.report.case_results)
        duration_ms = sum(case.duration_ms for case in record.report.case_results)
        return {
            "run_id": record.run_id,
            "status": record.status,
            "created_at": record.created_at,
            "runner": record.report.runner,
            "model": record.report.model,
            "review_enabled": record.report.enable_review,
            "total_cases": record.report.total_cases,
            "passed_cases": record.report.passed_cases,
            "failed_cases": record.report.failed_cases,
            "warning_count": warning_count,
            "duration_ms": duration_ms,
        }

    def _paths(self) -> list[Path]:
        if not self.directory.exists():
            return []
        return sorted(self.directory.glob("*.json"))

    @staticmethod
    def _load_path(path: Path) -> AcceptanceRecord | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return AcceptanceRecord.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError):
            return None
