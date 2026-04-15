from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.registry import ToolExecutionResult


class JSONAnalysisTool:
    name = "json_analysis"
    purpose = "Inspect local JSON files and compute lightweight structural metrics."

    def __init__(
        self,
        *,
        max_files: int = 2,
        max_rows: int = 50,
        max_keys: int = 20,
        max_key_paths: int = 24,
        max_depth: int = 4,
    ) -> None:
        self.max_files = max_files
        self.max_rows = max_rows
        self.max_keys = max_keys
        self.max_key_paths = max_key_paths
        self.max_depth = max_depth

    def supports(self, *, task_type: str, question: str, context: dict[str, Any]) -> bool:
        candidate_paths: list[Path] = context.get("candidate_paths", [])
        return task_type == "analysis" and any(path.suffix.lower() == ".json" for path in candidate_paths)

    def run(self, *, task_type: str, question: str, context: dict[str, Any]) -> ToolExecutionResult:
        candidate_paths: list[Path] = context.get("candidate_paths", [])
        json_paths = [path for path in candidate_paths if path.suffix.lower() == ".json"][: self.max_files]
        json_summaries = [self._summarize_json(path) for path in json_paths]
        return ToolExecutionResult(
            context_updates={"json_summaries": json_summaries},
            input_summary=f"{len(json_paths)} JSON file(s)",
            output_summary=f"Summarized {len(json_summaries)} JSON file(s)",
            metadata={
                "paths": [str(path) for path in json_paths],
                "max_rows": self.max_rows,
                "max_key_paths": self.max_key_paths,
            },
        )

    def _summarize_json(self, path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        top_level_type = self._json_type(payload)
        top_level_keys = list(payload.keys())[: self.max_keys] if isinstance(payload, dict) else []
        field_names: list[str] = []
        numeric_fields: list[dict[str, Any]] = []

        if isinstance(payload, list):
            sample_rows = payload[: self.max_rows]
            object_rows = [row for row in sample_rows if isinstance(row, dict)]
            if object_rows and len(object_rows) == len(sample_rows):
                field_names = self._ordered_field_names(object_rows)
                numeric_fields = self._summarize_numeric_fields_for_rows(object_rows, field_names)
        elif isinstance(payload, dict):
            field_names = top_level_keys
            numeric_fields = self._summarize_numeric_fields_for_mapping(payload, field_names)

        return {
            "path": str(path),
            "name": path.name,
            "top_level_type": top_level_type,
            "entry_count": self._entry_count(payload),
            "top_level_keys": top_level_keys,
            "field_names": field_names,
            "key_paths": self._collect_key_paths(payload),
            "numeric_fields": numeric_fields,
        }

    def _ordered_field_names(self, rows: list[dict[str, Any]]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row.keys():
                if key in seen:
                    continue
                seen.add(key)
                ordered.append(key)
                if len(ordered) >= self.max_keys:
                    return ordered
        return ordered

    def _summarize_numeric_fields_for_rows(
        self,
        rows: list[dict[str, Any]],
        field_names: list[str],
    ) -> list[dict[str, Any]]:
        numeric_fields: list[dict[str, Any]] = []
        for field in field_names:
            values = self._coerce_numeric_values(row.get(field) for row in rows)
            if values:
                numeric_fields.append(self._build_numeric_summary(field, values))
        return numeric_fields

    def _summarize_numeric_fields_for_mapping(
        self,
        payload: dict[str, Any],
        field_names: list[str],
    ) -> list[dict[str, Any]]:
        numeric_fields: list[dict[str, Any]] = []
        for field in field_names:
            values = self._coerce_numeric_values([payload.get(field)])
            if values:
                numeric_fields.append(self._build_numeric_summary(field, values))
        return numeric_fields

    def _coerce_numeric_values(self, raw_values: Any) -> list[float]:
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

    @staticmethod
    def _build_numeric_summary(name: str, values: list[float]) -> dict[str, Any]:
        return {
            "name": name,
            "min": min(values),
            "max": max(values),
            "avg": round(sum(values) / len(values), 4),
        }

    def _collect_key_paths(self, payload: Any) -> list[str]:
        paths: list[str] = []
        self._append_key_paths(payload, prefix="$", depth=0, paths=paths)
        return paths

    def _append_key_paths(
        self,
        payload: Any,
        *,
        prefix: str,
        depth: int,
        paths: list[str],
    ) -> None:
        if len(paths) >= self.max_key_paths or depth >= self.max_depth:
            return
        if isinstance(payload, dict):
            for key, value in list(payload.items())[: self.max_keys]:
                child_prefix = f"{prefix}.{key}"
                paths.append(child_prefix)
                if len(paths) >= self.max_key_paths:
                    return
                self._append_key_paths(value, prefix=child_prefix, depth=depth + 1, paths=paths)
        elif isinstance(payload, list) and payload:
            child_prefix = f"{prefix}[]"
            paths.append(child_prefix)
            if len(paths) >= self.max_key_paths:
                return
            self._append_key_paths(payload[0], prefix=child_prefix, depth=depth + 1, paths=paths)

    @staticmethod
    def _entry_count(payload: Any) -> int:
        if isinstance(payload, (list, dict)):
            return len(payload)
        return 1

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
