from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from schemas.acceptance_schema import (
    AcceptanceCaseComparison,
    AcceptanceComparison,
    AcceptanceCaseResult,
    AcceptanceRecord,
    AcceptanceReport,
)


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

    def previous_record(self, run_id: str, *, status: str | None = None) -> AcceptanceRecord | None:
        records = self.list_records(status=status)
        for index, record in enumerate(records):
            if record.run_id == run_id:
                next_index = index + 1
                if next_index < len(records):
                    return records[next_index]
                return None
        return None

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

    def compare_records(
        self,
        current: AcceptanceRecord,
        baseline: AcceptanceRecord,
    ) -> AcceptanceComparison:
        current_cases = self._cases_by_question(current.report.case_results)
        baseline_cases = self._cases_by_question(baseline.report.case_results)
        questions = self._ordered_questions(
            current.report.case_results,
            baseline.report.case_results,
        )

        case_comparisons: list[AcceptanceCaseComparison] = []
        for question in questions:
            current_case = current_cases.get(question)
            baseline_case = baseline_cases.get(question)
            case_comparisons.append(self._compare_case(question, current_case, baseline_case))

        current_warning_count = sum(len(case.warnings) for case in current.report.case_results)
        baseline_warning_count = sum(len(case.warnings) for case in baseline.report.case_results)
        regression_count = sum(1 for case in case_comparisons if case.regression)
        improvement_count = sum(1 for case in case_comparisons if case.improvement)

        return AcceptanceComparison(
            current_run_id=current.run_id,
            baseline_run_id=baseline.run_id,
            current_status=current.status,
            baseline_status=baseline.status,
            current_created_at=current.created_at,
            baseline_created_at=baseline.created_at,
            current_passed_cases=current.report.passed_cases,
            baseline_passed_cases=baseline.report.passed_cases,
            passed_cases_delta=current.report.passed_cases - baseline.report.passed_cases,
            current_failed_cases=current.report.failed_cases,
            baseline_failed_cases=baseline.report.failed_cases,
            failed_cases_delta=current.report.failed_cases - baseline.report.failed_cases,
            current_warning_count=current_warning_count,
            baseline_warning_count=baseline_warning_count,
            warning_count_delta=current_warning_count - baseline_warning_count,
            regression_count=regression_count,
            improvement_count=improvement_count,
            case_comparisons=case_comparisons,
        )

    def _paths(self) -> list[Path]:
        if not self.directory.exists():
            return []
        return sorted(self.directory.glob("*.json"))

    @staticmethod
    def _cases_by_question(case_results: list[AcceptanceCaseResult]) -> dict[str, AcceptanceCaseResult]:
        return {case.question: case for case in case_results}

    @staticmethod
    def _ordered_questions(
        current_cases: list[AcceptanceCaseResult],
        baseline_cases: list[AcceptanceCaseResult],
    ) -> list[str]:
        questions = [case.question for case in current_cases]
        seen = set(questions)
        for case in baseline_cases:
            if case.question not in seen:
                questions.append(case.question)
                seen.add(case.question)
        return questions

    @staticmethod
    def _compare_case(
        question: str,
        current_case: AcceptanceCaseResult | None,
        baseline_case: AcceptanceCaseResult | None,
    ) -> AcceptanceCaseComparison:
        current_present = current_case is not None
        baseline_present = baseline_case is not None
        current_passed = current_case.passed if current_case is not None else None
        baseline_passed = baseline_case.passed if baseline_case is not None else None
        current_error_count = len(current_case.errors) if current_case is not None else 0
        baseline_error_count = len(baseline_case.errors) if baseline_case is not None else 0
        current_warning_count = len(current_case.warnings) if current_case is not None else 0
        baseline_warning_count = len(baseline_case.warnings) if baseline_case is not None else 0
        duration_ms_delta = None
        if current_case is not None and baseline_case is not None:
            duration_ms_delta = current_case.duration_ms - baseline_case.duration_ms

        regression = False
        improvement = False
        if baseline_present and baseline_passed is True and current_passed is False:
            regression = True
        elif baseline_present and baseline_passed is False and current_passed is True:
            improvement = True
        elif baseline_present and not current_present:
            regression = True
        elif current_present and not baseline_present:
            improvement = True

        changed = (
            current_present != baseline_present
            or current_passed != baseline_passed
            or current_error_count != baseline_error_count
            or current_warning_count != baseline_warning_count
        )

        return AcceptanceCaseComparison(
            question=question,
            current_present=current_present,
            baseline_present=baseline_present,
            current_passed=current_passed,
            baseline_passed=baseline_passed,
            changed=changed,
            regression=regression,
            improvement=improvement,
            current_error_count=current_error_count,
            baseline_error_count=baseline_error_count,
            current_warning_count=current_warning_count,
            baseline_warning_count=baseline_warning_count,
            duration_ms_delta=duration_ms_delta,
        )

    @staticmethod
    def _load_path(path: Path) -> AcceptanceRecord | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return AcceptanceRecord.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError):
            return None
