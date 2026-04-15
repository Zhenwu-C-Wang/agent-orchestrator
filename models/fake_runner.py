from __future__ import annotations

from models.model_runner import ModelRequest, StructuredModelRunner, StructuredModelT
from schemas.result_schema import AnalysisResult, ComparisonResult, FinalAnswer, ResearchResult, ReviewResult


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
            research = request.payload.get("research")
            tool_context = request.payload.get("tool_context") or {}
            local_files = tool_context.get("local_files", [])
            csv_summaries = tool_context.get("csv_summaries", [])
            json_summaries = tool_context.get("json_summaries", [])
            dataset_metrics = tool_context.get("dataset_metrics", [])
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
                    f"{len(local_files) + len(csv_summaries) + len(json_summaries) + len(dataset_metrics) + len(web_pages)}"
                ),
            ]
            caveats = [
                "This analysis output is deterministic and does not execute real code.",
                "Real tool-backed analysis will require stronger validation around inputs and outputs.",
            ]
            if research is not None:
                summary = f"{summary} Incorporated prior research context."
                findings.append("Prior research context was incorporated before tool-backed analysis.")
                metrics.append(f"research_key_point_count={len(research['key_points'])}")
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
            if dataset_metrics:
                dataset_names = ", ".join(summary_item["name"] for summary_item in dataset_metrics)
                summary = f"{summary} Computed bounded dataset metrics for: {dataset_names}."
                findings.append("Numeric deltas and aggregate stats were computed from structured datasets.")
                for summary_item in dataset_metrics:
                    for numeric_field in summary_item["numeric_fields"][:3]:
                        metric = (
                            f"{summary_item['name']}:{numeric_field['name']}:"
                            f"first={numeric_field['first']},"
                            f"last={numeric_field['last']},"
                            f"change={numeric_field['absolute_change']},"
                            f"trend={numeric_field['trend']}"
                        )
                        if numeric_field.get("percent_change") is not None:
                            metric = f"{metric},pct={numeric_field['percent_change']}"
                        metrics.append(metric)
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

        if response_model is ComparisonResult:
            research = request.payload.get("research")
            tool_context = request.payload.get("tool_context") or {}
            local_files = tool_context.get("local_files", [])
            csv_summaries = tool_context.get("csv_summaries", [])
            json_summaries = tool_context.get("json_summaries", [])
            dataset_metrics = tool_context.get("dataset_metrics", [])
            web_pages = tool_context.get("web_pages", [])
            summary = f"Comparison summary for: {question}"
            comparisons = [
                "Start with explicit contexts so the comparison stays bounded and auditable.",
                "Surface both differences and caveats so downstream synthesis can stay grounded.",
                "Prefer a structured comparison brief before turning differences into a recommendation.",
            ]
            metrics = [
                "workflow_path=comparison_then_write",
                (
                    "tool_invocation_count="
                    f"{len(local_files) + len(csv_summaries) + len(json_summaries) + len(dataset_metrics) + len(web_pages)}"
                ),
            ]
            caveats = [
                "This comparison output is deterministic and does not execute real code.",
                "Real comparison workflows will need tighter normalization for mismatched schemas or labels.",
            ]
            if research is not None:
                summary = f"{summary} Incorporated prior research context."
                comparisons.append("Prior research context was incorporated before structured comparison.")
                metrics.append(f"research_key_point_count={len(research['key_points'])}")
                metrics[0] = "workflow_path=research_then_comparison_then_write"
            if len(local_files) >= 2:
                inspected = ", ".join(file_info["name"] for file_info in local_files)
                summary = f"{summary} Compared local file context from: {inspected}."
                comparisons.append("Local file previews were compared before synthesis.")
            if len(csv_summaries) >= 2:
                csv_names = ", ".join(summary_item["name"] for summary_item in csv_summaries[:2])
                summary = f"{summary} Reviewed CSV structure for: {csv_names}."
                comparisons.append("CSV column structure and sample numeric fields were compared.")
                left = csv_summaries[0]
                right = csv_summaries[1]
                metrics.append(
                    f"csv_column_overlap={len(set(left['columns']) & set(right['columns']))}"
                )
            if len(json_summaries) >= 2:
                json_names = ", ".join(summary_item["name"] for summary_item in json_summaries[:2])
                summary = f"{summary} Reviewed JSON structure for: {json_names}."
                comparisons.append("JSON field structure and numeric field coverage were compared.")
                left = json_summaries[0]
                right = json_summaries[1]
                metrics.append(
                    f"json_field_overlap={len(set(left['field_names']) & set(right['field_names']))}"
                )
            if len(dataset_metrics) >= 2:
                left_dataset = dataset_metrics[0]
                right_dataset = dataset_metrics[1]
                dataset_names = f"{left_dataset['name']} vs {right_dataset['name']}"
                summary = f"{summary} Computed bounded dataset comparisons for: {dataset_names}."
                shared_numeric_fields = {
                    field["name"]: field for field in left_dataset["numeric_fields"]
                }
                shared_numeric_fields = [
                    (
                        field_name,
                        shared_numeric_fields[field_name],
                        next(
                            field
                            for field in right_dataset["numeric_fields"]
                            if field["name"] == field_name
                        ),
                    )
                    for field_name in shared_numeric_fields
                    if any(field["name"] == field_name for field in right_dataset["numeric_fields"])
                ]
                for field_name, left_field, right_field in shared_numeric_fields[:3]:
                    last_delta = round(left_field["last"] - right_field["last"], 4)
                    avg_delta = round(left_field["avg"] - right_field["avg"], 4)
                    higher_name = left_dataset["name"] if last_delta >= 0 else right_dataset["name"]
                    comparisons.append(
                        f"{field_name} ends higher in {higher_name} when comparing {left_dataset['name']} and {right_dataset['name']}."
                    )
                    metrics.append(
                        f"{field_name}:last_delta={last_delta},avg_delta={avg_delta}"
                    )
            if len(web_pages) >= 2:
                urls = ", ".join(page["url"] for page in web_pages[:2])
                summary = f"{summary} Compared HTTP context from: {urls}."
                comparisons.append("HTTP content previews were compared before synthesis.")
                left_page = web_pages[0]
                right_page = web_pages[1]
                metrics.append(
                    f"http_preview_char_delta={left_page['preview_char_count'] - right_page['preview_char_count']}"
                )
            payload = {
                "question": question,
                "summary": summary,
                "comparisons": comparisons,
                "metrics": metrics,
                "caveats": caveats,
            }
            return response_model.model_validate(payload)

        if response_model is FinalAnswer:
            research = request.payload.get("research")
            analysis = request.payload.get("analysis")
            comparison = request.payload.get("comparison")
            if research is not None and analysis is not None:
                supporting_points = list(dict.fromkeys(
                    list(research["key_points"]) + list(analysis["findings"])
                ))
                limitations = list(dict.fromkeys(
                    list(research["caveats"]) + list(analysis["caveats"])
                ))
                recommendation = (
                    "Recommended next step: combine broader research framing with the explicit "
                    "analysis evidence before deciding what to do next."
                )
                answer = (
                    f"{research['summary']} {analysis['summary']} {recommendation}"
                )
            elif research is not None and comparison is not None:
                supporting_points = list(dict.fromkeys(
                    list(research["key_points"]) + list(comparison["comparisons"])
                ))
                limitations = list(dict.fromkeys(
                    list(research["caveats"]) + list(comparison["caveats"])
                ))
                recommendation = (
                    "Recommended next step: use the compared contexts plus the broader framing "
                    "to decide which source, region, or option should lead."
                )
                answer = (
                    f"{research['summary']} {comparison['summary']} {recommendation}"
                )
            elif research is not None:
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
                answer = f"{summary} {recommendation}"
            elif comparison is not None:
                summary = comparison["summary"]
                supporting_points = list(comparison["comparisons"])
                limitations = list(comparison["caveats"])
                recommendation = (
                    "Recommended next step: turn the bounded comparison into an explicit "
                    "decision or prioritization ask when you need a stronger recommendation."
                )
                answer = f"{summary} {recommendation}"
            else:
                raise ValueError("Fake writer payload requires research, analysis, or comparison.")
            limitations.append("The fake runner proves the orchestration contract, not model quality.")
            payload = {
                "question": question,
                "answer": (
                    answer
                    if (
                        (research is not None and analysis is not None)
                        or (research is not None and comparison is not None)
                    )
                    else f"{summary} {recommendation}"
                ),
                "supporting_points": supporting_points,
                "limitations": limitations,
            }
            return response_model.model_validate(payload)

        if response_model is ReviewResult:
            research = request.payload.get("research")
            analysis = request.payload.get("analysis")
            comparison = request.payload.get("comparison")
            final_answer = request.payload["final_answer"]
            checked_points = list(final_answer["supporting_points"])
            if research is not None:
                checked_points = list(research["key_points"]) + checked_points
            if analysis is not None:
                checked_points = list(analysis["findings"]) + checked_points
            if comparison is not None:
                checked_points = list(comparison["comparisons"]) + checked_points
            payload = {
                "question": question,
                "consistent": True,
                "verdict": "The final answer remains aligned with the intermediate worker output.",
                "issues": [],
                "checked_points": list(dict.fromkeys(checked_points)),
            }
            return response_model.model_validate(payload)

        raise ValueError(f"Unsupported response model for fake runner: {response_model.__name__}")

    def get_last_invocation_metadata(self) -> dict[str, object]:
        return dict(self._last_invocation_metadata)
