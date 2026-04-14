from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

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
