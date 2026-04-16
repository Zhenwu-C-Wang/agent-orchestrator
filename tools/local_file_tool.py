from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.registry import ToolExecutionResult


class LocalFileContextTool:
    name = "local_file_context"
    purpose = "Load local file previews to ground file-backed analysis and comparison requests."

    def __init__(self, *, max_files: int = 2, max_chars: int = 4000) -> None:
        self.max_files = max_files
        self.max_chars = max_chars

    def supports(self, *, task_type: str, question: str, context: dict[str, Any]) -> bool:
        return task_type in {"analysis", "comparison"} and bool(context.get("candidate_paths"))

    def run(self, *, task_type: str, question: str, context: dict[str, Any]) -> ToolExecutionResult:
        candidate_paths: list[Path] = context.get("candidate_paths", [])
        selected_paths = candidate_paths[: self.max_files]
        local_files = [self._describe_file(path) for path in selected_paths]
        return ToolExecutionResult(
            context_updates={"local_files": local_files},
            input_summary=f"{len(selected_paths)} local file(s)",
            output_summary=f"Loaded {len(local_files)} local file preview(s)",
            metadata={"paths": [str(path) for path in selected_paths]},
        )

    def _describe_file(self, path: Path) -> dict[str, Any]:
        preview = path.read_text(encoding="utf-8", errors="replace")[: self.max_chars]
        preview_lines = preview.splitlines()
        return {
            "path": str(path),
            "name": path.name,
            "suffix": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "preview": preview,
            "preview_line_count": len(preview_lines),
        }
