from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from tools.registry import ToolExecutionResult


class CSVAnalysisTool:
    name = "csv_analysis"
    purpose = "Inspect local CSV files and compute lightweight structural metrics."

    def __init__(self, *, max_files: int = 2, max_rows: int = 50) -> None:
        self.max_files = max_files
        self.max_rows = max_rows

    def supports(self, *, task_type: str, question: str, context: dict[str, Any]) -> bool:
        candidate_paths: list[Path] = context.get("candidate_paths", [])
        return task_type == "analysis" and any(path.suffix.lower() == ".csv" for path in candidate_paths)

    def run(self, *, task_type: str, question: str, context: dict[str, Any]) -> ToolExecutionResult:
        candidate_paths: list[Path] = context.get("candidate_paths", [])
        csv_paths = [path for path in candidate_paths if path.suffix.lower() == ".csv"][: self.max_files]
        csv_summaries = [self._summarize_csv(path) for path in csv_paths]
        return ToolExecutionResult(
            context_updates={"csv_summaries": csv_summaries},
            input_summary=f"{len(csv_paths)} CSV file(s)",
            output_summary=f"Summarized {len(csv_summaries)} CSV file(s)",
            metadata={
                "paths": [str(path) for path in csv_paths],
                "max_rows": self.max_rows,
            },
        )

    def _summarize_csv(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            sample_rows = []
            for index, row in enumerate(reader):
                if index >= self.max_rows:
                    break
                sample_rows.append(row)

        numeric_columns: list[dict[str, Any]] = []
        for field in fieldnames:
            values: list[float] = []
            for row in sample_rows:
                raw_value = (row.get(field) or "").strip()
                if raw_value == "":
                    continue
                try:
                    values.append(float(raw_value))
                except ValueError:
                    values = []
                    break
            if values:
                numeric_columns.append(
                    {
                        "name": field,
                        "min": min(values),
                        "max": max(values),
                        "avg": round(sum(values) / len(values), 4),
                    }
                )

        return {
            "path": str(path),
            "name": path.name,
            "columns": fieldnames,
            "sample_row_count": len(sample_rows),
            "numeric_columns": numeric_columns,
        }
