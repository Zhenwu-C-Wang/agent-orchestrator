from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from schemas.audit_schema import AuditRecord
from schemas.result_schema import WorkflowResult
from schemas.task_schema import TaskTrace


def _slugify_question(question: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", question.strip().lower()).strip("-")
    return slug[:48] or "run"


class AuditLogger:
    """Persists one JSON audit record per workflow execution."""

    def __init__(self, directory: str | Path, metadata: dict[str, Any] | None = None) -> None:
        self.directory = Path(directory)
        self.metadata = dict(metadata or {})

    def record_success(self, result: WorkflowResult) -> Path:
        record = AuditRecord(
            run_id=self._new_run_id(),
            status="completed",
            created_at=self._timestamp_iso(),
            question=result.question,
            metadata=self.metadata,
            traces=result.traces,
            result=result,
        )
        return self._write_record(record)

    def record_failure(self, *, question: str, traces: list[TaskTrace], error: str) -> Path:
        record = AuditRecord(
            run_id=self._new_run_id(),
            status="failed",
            created_at=self._timestamp_iso(),
            question=question,
            metadata=self.metadata,
            traces=traces,
            error=error,
        )
        return self._write_record(record)

    def _write_record(self, record: AuditRecord) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        filename = f"{record.run_id}-{_slugify_question(record.question)}-{record.status}.json"
        target = self.directory / filename
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


class AuditStore:
    """Reads persisted audit artifacts for status inspection."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)

    def list_records(
        self,
        *,
        limit: int | None = None,
        status: str | None = None,
    ) -> list[AuditRecord]:
        records: list[AuditRecord] = []
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

    def get_record(self, run_id: str) -> AuditRecord | None:
        direct_matches = sorted(self.directory.glob(f"{run_id}-*.json"))
        for path in direct_matches:
            record = self._load_path(path)
            if record is not None:
                return record

        for record in self.list_records():
            if record.run_id == run_id:
                return record
        return None

    def latest_record(self, *, status: str | None = None) -> AuditRecord | None:
        records = self.list_records(limit=1, status=status)
        return records[0] if records else None

    def summarize_record(self, record: AuditRecord) -> dict[str, Any]:
        cache_hits = sum(1 for trace in record.traces if trace.metadata.get("cache_hit") is True)
        return {
            "run_id": record.run_id,
            "status": record.status,
            "created_at": record.created_at,
            "question": record.question,
            "runner": record.metadata.get("runner"),
            "model": record.metadata.get("model"),
            "review_enabled": record.metadata.get("review_enabled"),
            "workflow_name": (
                record.result.workflow_plan.workflow_name
                if record.result is not None
                else None
            ),
            "trace_count": len(record.traces),
            "worker_order": [trace.worker_name for trace in record.traces],
            "cache_hits": cache_hits,
            "error": record.error,
        }

    def _paths(self) -> list[Path]:
        if not self.directory.exists():
            return []
        return sorted(self.directory.glob("*.json"))

    @staticmethod
    def _load_path(path: Path) -> AuditRecord | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return AuditRecord.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError):
            return None
