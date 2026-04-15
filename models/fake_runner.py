from __future__ import annotations

from models.model_runner import ModelRequest, StructuredModelRunner, StructuredModelT
from schemas.result_schema import AnalysisResult, FinalAnswer, ResearchResult, ReviewResult


class FakeModelRunner(StructuredModelRunner):
    """Deterministic runner used for tests and demos."""

    def __init__(self) -> None:
        self._last_invocation_metadata: dict[str, object] = {}

    def generate_structured(
        self,
        request: ModelRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredModelT:
        question = str(request.payload.get("question", "")).strip()
        self._last_invocation_metadata = {
            "runner": "fake",
            "model": None,
            "cache_enabled": False,
            "cache_hit": False,
            "cache_status": "disabled",
            "attempt_count": 1,
            "retry_count": 0,
        }

        if response_model is ResearchResult:
            payload = {
                "question": question,
                "summary": f"Research summary for: {question}",
                "key_points": [
                    "Start with a narrow workflow before adding more workers.",
                    "Keep intermediate worker outputs structured for composition.",
                    "Separate orchestration logic from model invocation details.",
                ],
                "caveats": [
                    "This research output is deterministic and not grounded in external sources.",
                    "A real local model may require stronger prompt constraints for schema stability.",
                ],
                "sources": ["internal:fake-runner"],
            }
            return response_model.model_validate(payload)

        if response_model is AnalysisResult:
            tool_context = request.payload.get("tool_context") or {}
            local_files = tool_context.get("local_files", [])
            csv_summaries = tool_context.get("csv_summaries", [])
            json_summaries = tool_context.get("json_summaries", [])
            web_pages = tool_context.get("web_pages", [])
            summary = f"Analysis summary for: {question}"
            findings = [
                "Start with a narrow analysis objective before adding more tooling.",
                "Keep derived findings structured so downstream synthesis can stay deterministic.",
                "Expose caveats whenever the analysis depends on local or incomplete context.",
            ]
            metrics = [
                "workflow_path=analysis_then_write",
                (
                    "tool_invocation_count="
                    f"{len(local_files) + len(csv_summaries) + len(json_summaries) + len(web_pages)}"
                ),
            ]
            caveats = [
                "This analysis output is deterministic and does not execute real code.",
                "Real tool-backed analysis will require stronger validation around inputs and outputs.",
            ]
            if local_files:
                inspected = ", ".join(file_info["name"] for file_info in local_files)
                summary = f"{summary} Inspected local file context from: {inspected}."
                findings.append("Local file previews were incorporated into the analysis context.")
            if csv_summaries:
                csv_names = ", ".join(summary_item["name"] for summary_item in csv_summaries)
                summary = f"{summary} Reviewed CSV structure for: {csv_names}."
                findings.append("CSV column structure and sample numeric fields were summarized.")
                for summary_item in csv_summaries:
                    metrics.append(
                        f"{summary_item['name']}:columns={len(summary_item['columns'])},"
                        f"sample_rows={summary_item['sample_row_count']}"
                    )
            if json_summaries:
                json_names = ", ".join(summary_item["name"] for summary_item in json_summaries)
                summary = f"{summary} Reviewed JSON structure for: {json_names}."
                findings.append("JSON structure and sample numeric fields were summarized.")
                for summary_item in json_summaries:
                    metrics.append(
                        f"{summary_item['name']}:top_level_type={summary_item['top_level_type']},"
                        f"fields={len(summary_item['field_names'])},"
                        f"numeric_fields={len(summary_item['numeric_fields'])}"
                    )
            if web_pages:
                urls = ", ".join(page["url"] for page in web_pages)
                summary = f"{summary} Fetched HTTP context from: {urls}."
                findings.append("HTTP content previews were incorporated into the analysis context.")
                for page in web_pages:
                    metrics.append(
                        f"{page['url']}:content_type={page['content_type']},"
                        f"preview_chars={page['preview_char_count']}"
                    )
            payload = {
                "question": question,
                "summary": summary,
                "findings": findings,
                "metrics": metrics,
                "caveats": caveats,
            }
            return response_model.model_validate(payload)

        if response_model is FinalAnswer:
            research = request.payload.get("research")
            analysis = request.payload.get("analysis")
            if research is not None:
                summary = research["summary"]
                supporting_points = list(research["key_points"])
                limitations = list(research["caveats"])
                recommendation = (
                    "Recommended next step: keep the first release synchronous, "
                    "schema-first, and easy to inspect."
                )
            elif analysis is not None:
                summary = analysis["summary"]
                supporting_points = list(analysis["findings"])
                limitations = list(analysis["caveats"])
                recommendation = (
                    "Recommended next step: connect a guarded tool path so analysis "
                    "requests can inspect local data directly."
                )
            else:
                raise ValueError("Fake writer payload requires research or analysis.")
            limitations.append("The fake runner proves the orchestration contract, not model quality.")
            payload = {
                "question": question,
                "answer": f"{summary} {recommendation}",
                "supporting_points": supporting_points,
                "limitations": limitations,
            }
            return response_model.model_validate(payload)

        if response_model is ReviewResult:
            research = request.payload.get("research")
            analysis = request.payload.get("analysis")
            final_answer = request.payload["final_answer"]
            checked_points = list(final_answer["supporting_points"])
            if research is not None:
                checked_points = list(research["key_points"]) + checked_points
            if analysis is not None:
                checked_points = list(analysis["findings"]) + checked_points
            payload = {
                "question": question,
                "consistent": True,
                "verdict": "The final answer remains aligned with the intermediate worker output.",
                "issues": [],
                "checked_points": checked_points,
            }
            return response_model.model_validate(payload)

        raise ValueError(f"Unsupported response model for fake runner: {response_model.__name__}")

    def get_last_invocation_metadata(self) -> dict[str, object]:
        return dict(self._last_invocation_metadata)
