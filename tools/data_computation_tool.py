from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from tools.registry import ToolExecutionResult


class DataComputationTool:
    name = "data_computation"
    purpose = "Compute bounded numeric trend and aggregate metrics for local CSV and JSON datasets."

    def __init__(self, *, max_files: int = 2, max_rows: int = 200, max_fields: int = 12) -> None:
        self.max_files = max_files
        self.max_rows = max_rows
        self.max_fields = max_fields

    def supports(self, *, task_type: str, question: str, context: dict[str, Any]) -> bool:
        candidate_paths: list[Path] = context.get("candidate_paths", [])
        return task_type in {"analysis", "comparison"} and any(
            path.suffix.lower() in {".csv", ".json"} for path in candidate_paths
        )

    def run(self, *, task_type: str, question: str, context: dict[str, Any]) -> ToolExecutionResult:
        candidate_paths: list[Path] = context.get("candidate_paths", [])
        selected_paths = [
            path for path in candidate_paths if path.suffix.lower() in {".csv", ".json"}
        ][: self.max_files]
        dataset_metrics = [self._summarize_dataset(path) for path in selected_paths]
        return ToolExecutionResult(
            context_updates={"dataset_metrics": dataset_metrics},
            input_summary=f"{len(selected_paths)} structured data file(s)",
            output_summary=f"Computed metrics for {len(dataset_metrics)} dataset(s)",
            metadata={
                "paths": [str(path) for path in selected_paths],
                "max_rows": self.max_rows,
                "max_fields": self.max_fields,
            },
        )

    def _summarize_dataset(self, path: Path) -> dict[str, Any]:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            return self._summarize_csv(path)
        if suffix == ".json":
            return self._summarize_json(path)
        raise ValueError(f"Unsupported structured dataset type: {path.suffix}")

    def _summarize_csv(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = (reader.fieldnames or [])[: self.max_fields]
            rows: list[dict[str, Any]] = []
            for index, row in enumerate(reader):
                if index >= self.max_rows:
                    break
                rows.append({field: row.get(field) for field in fieldnames})
        return self._build_dataset_summary(path=path, fmt="csv", rows=rows, field_names=fieldnames)

    def _summarize_json(self, path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            object_rows = [row for row in payload[: self.max_rows] if isinstance(row, dict)]
            field_names = self._ordered_field_names(object_rows)[: self.max_fields]
            rows = [{field: row.get(field) for field in field_names} for row in object_rows]
            return self._build_dataset_summary(
                path=path,
                fmt="json",
                rows=rows,
                field_names=field_names,
                top_level_type="array",
            )
        if isinstance(payload, dict):
            field_names = list(payload.keys())[: self.max_fields]
            return self._build_dataset_summary(
                path=path,
                fmt="json",
                rows=[{field: payload.get(field) for field in field_names}],
                field_names=field_names,
                top_level_type="object",
            )
        return {
            "path": str(path),
            "name": path.name,
            "format": "json",
            "top_level_type": self._json_type(payload),
            "row_count": 1,
            "label_field": None,
            "numeric_fields": [],
        }

    def _build_dataset_summary(
        self,
        *,
        path: Path,
        fmt: str,
        rows: list[dict[str, Any]],
        field_names: list[str],
        top_level_type: str | None = None,
    ) -> dict[str, Any]:
        label_field = self._select_label_field(rows, field_names)
        numeric_fields: list[dict[str, Any]] = []
        for field in field_names:
            values = self._coerce_numeric_values(row.get(field) for row in rows)
            if values:
                labels = [self._normalize_label(row.get(label_field)) for row in rows] if label_field else []
                numeric_fields.append(self._build_numeric_field_summary(field, values, labels))
        summary = {
            "path": str(path),
            "name": path.name,
            "format": fmt,
            "row_count": len(rows),
            "label_field": label_field,
            "numeric_fields": numeric_fields,
        }
        if top_level_type is not None:
            summary["top_level_type"] = top_level_type
        return summary

    def _select_label_field(self, rows: list[dict[str, Any]], field_names: list[str]) -> str | None:
        for field in field_names:
            values = [row.get(field) for row in rows]
            if not values:
                continue
            if self._coerce_numeric_values(values):
                continue
            if any(self._normalize_label(value) is not None for value in values):
                return field
        return None

    def _ordered_field_names(self, rows: list[dict[str, Any]]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row.keys():
                if key in seen:
                    continue
                seen.add(key)
                ordered.append(key)
        return ordered

    def _coerce_numeric_values(self, raw_values: Iterable[Any]) -> list[float]:
        values: list[float] = []
        for raw_value in raw_values:
            if raw_value is None:
                continue
            if isinstance(raw_value, bool):
                return []
            if isinstance(raw_value, (int, float)):
                values.append(float(raw_value))
                continue
            if isinstance(raw_value, str):
                stripped = raw_value.strip()
                if not stripped:
                    continue
                try:
                    values.append(float(stripped))
                except ValueError:
                    return []
                continue
            return []
        return values

    def _build_numeric_field_summary(
        self,
        field_name: str,
        values: list[float],
        labels: list[str | None],
    ) -> dict[str, Any]:
        first_value = values[0]
        last_value = values[-1]
        absolute_change = round(last_value - first_value, 4)
        percent_change = None
        if first_value != 0:
            percent_change = round((absolute_change / first_value) * 100, 4)
        summary = {
            "name": field_name,
            "first": first_value,
            "last": last_value,
            "absolute_change": absolute_change,
            "percent_change": percent_change,
            "min": min(values),
            "max": max(values),
            "avg": round(sum(values) / len(values), 4),
            "trend": self._trend_name(first_value, last_value),
        }
        if labels and len(labels) == len(values):
            summary["first_label"] = labels[0]
            summary["last_label"] = labels[-1]
        return summary

    @staticmethod
    def _normalize_label(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _trend_name(first_value: float, last_value: float) -> str:
        if last_value > first_value:
            return "up"
        if last_value < first_value:
            return "down"
        return "flat"

    @staticmethod
    def _json_type(payload: Any) -> str:
        if isinstance(payload, dict):
            return "object"
        if isinstance(payload, list):
            return "array"
        if payload is None:
            return "null"
        if isinstance(payload, bool):
            return "boolean"
        if isinstance(payload, (int, float)):
            return "number"
        if isinstance(payload, str):
            return "string"
        return type(payload).__name__
