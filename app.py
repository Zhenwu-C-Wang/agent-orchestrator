from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import streamlit as st

from orchestrator.bootstrap import build_supervisor, format_markdown, format_pretty
from orchestrator.inspection import (
    build_acceptance_overview,
    build_acceptance_case_detail,
    build_cache_overview,
    build_cache_entry_detail,
    build_plan_guidance,
    build_result_overview,
)
from orchestrator.planner import TaskPlanner
from orchestrator.project_status import load_project_status
from schemas.result_schema import WorkflowResult
from tools.acceptance import AcceptanceStore
from tools.audit import AuditStore
from tools.cache import StructuredResultCache

REPO_ROOT = Path(__file__).resolve().parent
SAMPLE_DATA_DIR = REPO_ROOT / "docs" / "sample_data"
SAMPLE_CSV_PATH = str(SAMPLE_DATA_DIR / "quarterly_metrics.csv")
SAMPLE_JSON_PATH = str(SAMPLE_DATA_DIR / "quarterly_metrics.json")
SAMPLE_BASELINE_CSV_PATH = str(SAMPLE_DATA_DIR / "quarterly_metrics_baseline.csv")
DEFAULT_QUESTION = "How should I bootstrap a supervisor-worker agent system?"
DEFAULT_AUDIT_DIR = "artifacts/runs"
DEFAULT_ACCEPTANCE_REPORT_DIR = "artifacts/acceptance"
STARTER_TASKS: dict[str, dict[str, object]] = {
    "Research quickstart": {
        "description": "Start with a simple question and watch the research workflow run end to end.",
        "question": DEFAULT_QUESTION,
        "context_files": [],
        "context_urls": [],
        "expected_workflow": "research_then_write",
        "recommended_runner": "fake",
        "next_step": "Try the CSV analysis quickstart next to see tool usage.",
    },
    "CSV analysis quickstart": {
        "description": "Use the built-in sample CSV so you can see file grounding and tool-backed analysis immediately.",
        "question": "Summarize the most important changes in this data.",
        "context_files": [SAMPLE_CSV_PATH],
        "context_urls": [],
        "expected_workflow": "analysis_then_write",
        "recommended_runner": "fake",
        "next_step": "Try the comparison quickstart next if you want to compare two datasets.",
    },
    "JSON analysis quickstart": {
        "description": "Use the built-in JSON snapshot to exercise the structured JSON analysis path.",
        "question": "Summarize the most important changes in this JSON snapshot.",
        "context_files": [SAMPLE_JSON_PATH],
        "context_urls": [],
        "expected_workflow": "analysis_then_write",
        "recommended_runner": "fake",
        "next_step": "Try the advisory data quickstart to see research plus analysis combined.",
    },
    "Comparison quickstart": {
        "description": "Compare two built-in datasets so the comparison workflow is visible without extra setup.",
        "question": "Compare these datasets and summarize the most important differences.",
        "context_files": [SAMPLE_CSV_PATH, SAMPLE_BASELINE_CSV_PATH],
        "context_urls": [],
        "expected_workflow": "comparison_then_write",
        "recommended_runner": "fake",
        "next_step": "Try the advisory comparison quickstart to see the broader recommendation path.",
    },
    "Advisory data quickstart": {
        "description": "Ask for a recommendation so the app combines research with tool-backed analysis.",
        "question": "Analyze this dataset and recommend what we should prioritize next.",
        "context_files": [SAMPLE_CSV_PATH],
        "context_urls": [],
        "expected_workflow": "research_then_analysis_then_write",
        "recommended_runner": "fake",
        "next_step": "If you want a broader comparison decision, try the advisory comparison quickstart.",
    },
    "Advisory comparison quickstart": {
        "description": "Ask for a recommendation across two built-in datasets to trigger the hybrid comparison route.",
        "question": "Compare these datasets and recommend which one we should prioritize next.",
        "context_files": [SAMPLE_CSV_PATH, SAMPLE_BASELINE_CSV_PATH],
        "context_urls": [],
        "expected_workflow": "research_then_comparison_then_write",
        "recommended_runner": "fake",
        "next_step": "After this, you can switch to Custom task and try your own files.",
    },
    "Custom task": {
        "description": "Use your own prompt, files, or URLs once you are comfortable with the starter flows.",
        "question": DEFAULT_QUESTION,
        "context_files": [],
        "context_urls": [],
        "expected_workflow": "depends on your input",
        "recommended_runner": "fake",
        "next_step": "Attach your own files or URLs below when you are ready.",
    },
}


def _persist_uploaded_files(uploaded_files: list[object]) -> list[str]:
    if not uploaded_files:
        return []

    target_dir = Path(tempfile.gettempdir()) / "agent-orchestrator-streamlit"
    target_dir.mkdir(parents=True, exist_ok=True)

    persisted_paths: list[str] = []
    for uploaded_file in uploaded_files:
        data = uploaded_file.getvalue()
        digest = hashlib.sha256(data).hexdigest()[:10]
        safe_name = Path(uploaded_file.name).name
        target = target_dir / f"{digest}-{safe_name}"
        target.write_bytes(data)
        persisted_paths.append(str(target))
    return persisted_paths


def _parse_context_urls(raw_value: str) -> list[str]:
    return [line.strip() for line in raw_value.splitlines() if line.strip()]


def _merge_distinct(items: list[str], extras: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in [*items, *extras]:
        if not item or item in seen:
            continue
        seen.add(item)
        merged.append(item)
    return merged


def _render_metrics(metrics: list[object]) -> None:
    if not metrics:
        return

    columns = st.columns(len(metrics))
    for column, metric in zip(columns, metrics):
        column.metric(metric.label, metric.value)


def _render_plan_preview(
    question: str,
    enable_review: bool,
    context_files: list[str],
    context_urls: list[str],
    allow_inline_context_files: bool,
    allow_inline_context_urls: bool,
) -> None:
    planner = TaskPlanner(
        enable_review=enable_review,
        allow_question_file_paths=allow_inline_context_files,
        allow_question_urls=allow_inline_context_urls,
    )
    plan = planner.build_plan(
        question,
        context_files=context_files,
        context_urls=context_urls,
    )
    guidance = build_plan_guidance(plan, question=question)

    st.subheader("Workflow Plan")
    st.caption(plan.rationale)
    st.markdown(f"**{guidance.headline}**")
    st.caption(guidance.summary)
    _render_metrics(guidance.metrics)
    if guidance.warnings:
        st.markdown("**Attention**")
        for warning in guidance.warnings:
            st.warning(warning)
    if guidance.guidance:
        st.markdown("**Guidance**")
        for item in guidance.guidance:
            st.write(f"- {item}")
    st.markdown(f"**Selected workflow:** `{plan.workflow_name}`")
    st.dataframe(guidance.step_rows, use_container_width=True, hide_index=True)


def _render_intermediate_result(result: WorkflowResult) -> None:
    if result.research is not None:
        st.subheader("Research")
        st.write(result.research.summary)
        if result.research.key_points:
            st.markdown("**Key Points**")
            for point in result.research.key_points:
                st.write(f"- {point}")
        if result.research.caveats:
            st.markdown("**Caveats**")
            for caveat in result.research.caveats:
                st.write(f"- {caveat}")

    if result.analysis is not None:
        st.subheader("Analysis")
        st.write(result.analysis.summary)
        if result.analysis.findings:
            st.markdown("**Findings**")
            for finding in result.analysis.findings:
                st.write(f"- {finding}")
        if result.analysis.metrics:
            st.markdown("**Metrics**")
            for metric in result.analysis.metrics:
                st.write(f"- {metric}")
        if result.analysis.caveats:
            st.markdown("**Caveats**")
            for caveat in result.analysis.caveats:
                st.write(f"- {caveat}")

    if result.comparison is not None:
        st.subheader("Comparison")
        st.write(result.comparison.summary)
        if result.comparison.comparisons:
            st.markdown("**Comparisons**")
            for item in result.comparison.comparisons:
                st.write(f"- {item}")
        if result.comparison.metrics:
            st.markdown("**Metrics**")
            for metric in result.comparison.metrics:
                st.write(f"- {metric}")
        if result.comparison.caveats:
            st.markdown("**Caveats**")
            for caveat in result.comparison.caveats:
                st.write(f"- {caveat}")


def _render_result_overview(result: WorkflowResult) -> None:
    overview = build_result_overview(result)
    st.subheader("Inspection Overview")
    st.markdown(f"**{overview.headline}**")
    st.caption(overview.summary)
    _render_metrics(overview.metrics)
    if overview.highlights:
        st.markdown("**Highlights**")
        for item in overview.highlights:
            st.write(f"- {item}")
    if overview.next_actions:
        st.markdown("**Next Actions**")
        for item in overview.next_actions:
            st.write(f"- {item}")


def _render_traces(result: WorkflowResult) -> None:
    st.subheader("Traces")
    rows = []
    for trace in result.traces:
        rows.append(
            {
                "task_id": trace.task_id,
                "worker": trace.worker_name,
                "task_type": trace.task_type.value,
                "status": trace.status,
                "duration_ms": trace.duration_ms,
                "output_schema": trace.output_schema,
                "metadata": json.dumps(trace.metadata, ensure_ascii=True),
            }
        )
    st.dataframe(rows, use_container_width=True)


def _render_tool_invocations(result: WorkflowResult) -> None:
    st.subheader("Tool Invocations")
    if not result.tool_invocations:
        st.info("No tools were invoked for this workflow.")
        return

    rows = [
        {
            "tool_name": invocation.tool_name,
            "status": invocation.status,
            "purpose": invocation.purpose,
            "input_summary": invocation.input_summary,
            "output_summary": invocation.output_summary,
            "duration_ms": invocation.duration_ms,
            "error": invocation.error,
        }
        for invocation in result.tool_invocations
    ]
    st.dataframe(rows, use_container_width=True)


def _render_outputs(result: WorkflowResult) -> None:
    st.subheader("Final Output")
    st.write(result.final_answer.answer)

    if result.final_answer.supporting_points:
        st.markdown("**Supporting Points**")
        for point in result.final_answer.supporting_points:
            st.write(f"- {point}")

    if result.final_answer.limitations:
        st.markdown("**Limitations**")
        for limitation in result.final_answer.limitations:
            st.write(f"- {limitation}")


def _render_review(result: WorkflowResult) -> None:
    if result.review is not None:
        st.subheader("Review")
        st.write(result.review.verdict)
        st.write(f"Consistent: `{result.review.consistent}`")
        if result.review.issues:
            st.markdown("**Issues**")
            for issue in result.review.issues:
                st.write(f"- {issue}")


def _render_downloads(result: WorkflowResult) -> None:
    payload_json = result.model_dump_json(indent=2)
    pretty_output = format_pretty(result)
    markdown_output = format_markdown(result)

    st.subheader("Export")
    st.download_button(
        label="Download JSON",
        data=payload_json,
        file_name="workflow-result.json",
        mime="application/json",
    )
    st.download_button(
        label="Download Markdown",
        data=markdown_output,
        file_name="workflow-result.md",
        mime="text/markdown",
    )
    st.download_button(
        label="Download Text Summary",
        data=pretty_output,
        file_name="workflow-result.txt",
        mime="text/plain",
    )


def _render_project_status() -> None:
    status = load_project_status()
    st.subheader("Project Status")
    if status is None:
        st.info("No project status snapshot found.")
        return

    st.write(f"Phase: `{status.current_phase}`")
    st.write(f"Current milestone: `{status.current_milestone}`")
    st.write(f"Next milestone: `{status.next_milestone or 'n/a'}`")
    st.caption(status.summary)

    if status.completed_items:
        st.markdown("**Completed**")
        for item in status.completed_items:
            st.write(f"- {item}")

    if status.next_items:
        st.markdown("**Next**")
        for item in status.next_items:
            st.write(f"- {item}")


def _render_starter_task_guide(starter_name: str, starter_task: dict[str, object], guided_mode: bool) -> None:
    st.subheader("Start Here")
    st.caption(str(starter_task["description"]))
    if guided_mode:
        st.info(
            "Recommended first-run path: keep Guided mode on, keep Runner on `fake`, "
            "and click `Run Workflow` without changing the advanced settings."
        )

    details: list[str] = [
        f"Expected workflow: `{starter_task['expected_workflow']}`",
        f"Recommended runner: `{starter_task['recommended_runner']}`",
    ]
    starter_files = [Path(path).name for path in starter_task.get("context_files", [])]
    starter_urls = [str(url) for url in starter_task.get("context_urls", [])]
    if starter_files:
        details.append(f"Built-in sample files: `{', '.join(starter_files)}`")
    if starter_urls:
        details.append(f"Built-in URLs: `{', '.join(starter_urls)}`")
    for item in details:
        st.write(f"- {item}")

    if starter_name != "Custom task":
        st.caption(str(starter_task["next_step"]))


def _render_acceptance_reports(report_dir: str) -> None:
    st.subheader("Acceptance Reports")
    store = AcceptanceStore(report_dir)
    records = store.list_records(limit=5)
    if not records:
        st.info("No persisted acceptance reports found yet.")
        return

    rows = [store.summarize_record(record) for record in records]
    st.dataframe(rows, use_container_width=True)

    selected_run_id = st.selectbox(
        "Inspect acceptance run",
        options=[record.run_id for record in records],
        format_func=lambda run_id: next(
            (
                f"{record.run_id} | {record.status} | {record.report.runner}"
                for record in records
                if record.run_id == run_id
            ),
            run_id,
        ),
    )
    selected = store.get_record(selected_run_id)
    if selected is None:
        return

    baseline = store.previous_record(selected.run_id)
    comparison = store.compare_records(selected, baseline) if baseline is not None else None
    overview = build_acceptance_overview(selected, comparison=comparison)

    with st.expander("Selected Acceptance Detail"):
        st.markdown(f"**{overview.headline}**")
        st.caption(overview.summary)
        _render_metrics(overview.metrics)
        if overview.highlights:
            st.markdown("**Highlights**")
            for item in overview.highlights:
                st.write(f"- {item}")
        if overview.warnings:
            st.markdown("**Warnings**")
            for item in overview.warnings:
                st.warning(item)
        if overview.next_actions:
            st.markdown("**Next Actions**")
            for item in overview.next_actions:
                st.write(f"- {item}")
        if overview.changed_case_rows:
            st.markdown("**Changed Cases**")
            st.dataframe(overview.changed_case_rows, use_container_width=True, hide_index=True)

        selected_case_question = st.selectbox(
            "Inspect acceptance case",
            options=[case.question for case in selected.report.case_results],
            key="acceptance_case_select",
        )
        selected_case = next(
            case for case in selected.report.case_results if case.question == selected_case_question
        )
        selected_case_comparison = None
        if comparison is not None:
            selected_case_comparison = next(
                (
                    case
                    for case in comparison.case_comparisons
                    if case.question == selected_case_question
                ),
                None,
            )
        case_detail = build_acceptance_case_detail(
            selected_case,
            case_comparison=selected_case_comparison,
        )
        st.markdown(f"**{case_detail.headline}**")
        st.caption(case_detail.summary)
        _render_metrics(case_detail.metrics)
        if case_detail.highlights:
            st.markdown("**Case Highlights**")
            for item in case_detail.highlights:
                st.write(f"- {item}")
        if case_detail.warnings:
            st.markdown("**Case Warnings**")
            for item in case_detail.warnings:
                st.warning(item)
        if case_detail.next_actions:
            st.markdown("**Case Next Actions**")
            for item in case_detail.next_actions:
                st.write(f"- {item}")
        if case_detail.result_overview is not None:
            st.markdown(f"**{case_detail.result_overview.headline}**")
            st.caption(case_detail.result_overview.summary)
            _render_metrics(case_detail.result_overview.metrics)
        if case_detail.trace_rows:
            st.markdown("**Case Traces**")
            st.dataframe(case_detail.trace_rows, use_container_width=True, hide_index=True)
        if case_detail.tool_rows:
            st.markdown("**Case Tools**")
            st.dataframe(case_detail.tool_rows, use_container_width=True, hide_index=True)
        if case_detail.final_answer_preview:
            st.markdown("**Final Answer Preview**")
            st.write(case_detail.final_answer_preview)


def _render_recent_runs(audit_dir: str) -> None:
    st.subheader("Recent Runs")
    store = AuditStore(audit_dir)
    records = store.list_records(limit=5)
    if not records:
        st.info("No persisted runs found yet.")
        return

    rows = [store.summarize_record(record) for record in records]
    st.dataframe(rows, use_container_width=True)

    selected_run_id = st.selectbox(
        "Inspect recent run",
        options=[record.run_id for record in records],
        format_func=lambda run_id: next(
            (
                f"{record.run_id} | {record.status} | {record.question}"
                for record in records
                if record.run_id == run_id
            ),
            run_id,
        ),
    )
    selected = store.get_record(selected_run_id)
    if selected is None:
        return

    with st.expander("Selected Run Detail"):
        st.write(f"Status: `{selected.status}`")
        st.write(f"Created at: `{selected.created_at}`")
        st.write(f"Question: {selected.question}")
        if selected.result is not None:
            overview = build_result_overview(selected.result)
            st.markdown(f"**{overview.headline}**")
            st.caption(overview.summary)
            _render_metrics(overview.metrics)
            if overview.highlights:
                st.markdown("**Highlights**")
                for item in overview.highlights:
                    st.write(f"- {item}")
            if overview.next_actions:
                st.markdown("**Next Actions**")
                for item in overview.next_actions:
                    st.write(f"- {item}")
            st.write(f"Workflow: `{selected.result.workflow_plan.workflow_name}`")
            st.write(selected.result.final_answer.answer)
        if selected.error:
            st.error(selected.error)


def _render_cache_snapshot(cache_dir: str, cache_max_age_seconds: float | None) -> None:
    st.subheader("Cache Health")
    cache = StructuredResultCache(
        cache_dir,
        max_age_seconds=cache_max_age_seconds,
    )
    cache_entries = cache.list_entries(limit=20)
    recent_entries = [cache.summarize_entry(entry) for entry in cache_entries[:5]]
    overview = build_cache_overview(
        cache.summarize_cache(),
        recent_entries=recent_entries,
    )

    st.markdown(f"**{overview.headline}**")
    st.caption(overview.summary)
    _render_metrics(overview.metrics)
    if overview.highlights:
        st.markdown("**Highlights**")
        for item in overview.highlights:
            st.write(f"- {item}")
    if overview.warnings:
        st.markdown("**Warnings**")
        for item in overview.warnings:
            st.warning(item)
    if overview.next_actions:
        st.markdown("**Next Actions**")
        for item in overview.next_actions:
            st.write(f"- {item}")
    if overview.recent_entry_rows:
        st.markdown("**Recent Entries**")
        st.dataframe(overview.recent_entry_rows, use_container_width=True, hide_index=True)
        selected_cache_key = st.selectbox(
            "Inspect cache entry",
            options=[entry.cache_key for entry in cache_entries],
            format_func=lambda cache_key: next(
                (
                    f"{entry.created_at} | {entry.metadata.get('task_type') or 'n/a'} | {entry.metadata.get('response_model') or 'n/a'}"
                    for entry in cache_entries
                    if entry.cache_key == cache_key
                ),
                cache_key,
            ),
            key="cache_entry_select",
        )
        selected_entry = next(entry for entry in cache_entries if entry.cache_key == selected_cache_key)
        entry_detail = build_cache_entry_detail(
            selected_entry,
            expired=cache.is_entry_expired(selected_entry),
        )
        st.markdown(f"**{entry_detail.headline}**")
        st.caption(entry_detail.summary)
        _render_metrics(entry_detail.metrics)
        if entry_detail.highlights:
            st.markdown("**Entry Highlights**")
            for item in entry_detail.highlights:
                st.write(f"- {item}")
        if entry_detail.warnings:
            st.markdown("**Entry Warnings**")
            for item in entry_detail.warnings:
                st.warning(item)
        if entry_detail.next_actions:
            st.markdown("**Entry Next Actions**")
            for item in entry_detail.next_actions:
                st.write(f"- {item}")
        if entry_detail.metadata_rows:
            st.markdown("**Entry Metadata**")
            st.dataframe(entry_detail.metadata_rows, use_container_width=True, hide_index=True)
        if entry_detail.response_preview:
            st.markdown("**Response Preview**")
            st.write(entry_detail.response_preview)
        with st.expander("Cache Response JSON"):
            st.json(selected_entry.response)


def main() -> None:
    st.set_page_config(page_title="Agent Orchestrator", layout="wide")
    st.title("Agent Orchestrator")
    st.caption("Run the local supervisor/worker workflow and inspect planning, traces, and outputs.")

    if "last_result" not in st.session_state:
        st.session_state["last_result"] = None
    if "last_error" not in st.session_state:
        st.session_state["last_error"] = None
    if "guided_mode" not in st.session_state:
        st.session_state["guided_mode"] = True
    if "starter_task" not in st.session_state:
        st.session_state["starter_task"] = "Research quickstart"
    if "last_starter_task" not in st.session_state:
        st.session_state["last_starter_task"] = "Research quickstart"
    if "task_input" not in st.session_state:
        st.session_state["task_input"] = DEFAULT_QUESTION

    with st.sidebar:
        st.header("Try It")
        guided_mode = st.toggle(
            "Guided mode",
            value=st.session_state["guided_mode"],
            help="Hide advanced options and keep the app focused on the recommended first-run path.",
        )
        st.session_state["guided_mode"] = guided_mode
        runner_name = st.selectbox(
            "Runner",
            options=["fake", "ollama"],
            index=0,
            help="Use `fake` for the simplest first run. Switch to `ollama` only after the starter flow succeeds.",
        )
        if guided_mode:
            st.caption("For first-time testers: keep `Runner` on `fake` and start with a quickstart task.")

        with st.expander("Advanced settings", expanded=not guided_mode):
            model = st.text_input("Model", value="llama3.1", disabled=runner_name == "fake")
            base_url = st.text_input("Ollama Base URL", value="http://localhost:11434")
            enable_review = st.checkbox("Enable review stage", value=False)
            allow_inline_context_files = st.checkbox(
                "Allow file paths embedded in the question",
                value=False,
            )
            allow_inline_context_urls = st.checkbox(
                "Allow URLs embedded in the question",
                value=False,
            )
            audit_dir = st.text_input("Audit directory", value=DEFAULT_AUDIT_DIR)
            acceptance_report_dir = st.text_input(
                "Acceptance report directory",
                value=DEFAULT_ACCEPTANCE_REPORT_DIR,
            )
            cache_dir = st.text_input("Cache directory", value="")
            cache_max_age_seconds = st.number_input(
                "Cache TTL seconds",
                min_value=0.0,
                value=3600.0,
                step=60.0,
            )
            max_retries = st.number_input("Max retries", min_value=0, value=1, step=1)
            retry_backoff_seconds = st.number_input(
                "Retry backoff seconds",
                min_value=0.0,
                value=0.25,
                step=0.25,
            )

    starter_name = st.selectbox(
        "Starter Task",
        options=list(STARTER_TASKS.keys()),
        help="Pick a guided example or switch to Custom task when you want to try your own prompt.",
        key="starter_task",
    )
    starter_task = STARTER_TASKS[starter_name]
    if st.session_state["last_starter_task"] != starter_name:
        st.session_state["task_input"] = str(starter_task["question"])
        st.session_state["last_starter_task"] = starter_name

    starter_context_files = list(starter_task.get("context_files", []))
    starter_context_urls = list(starter_task.get("context_urls", []))

    top_left, top_right = st.columns([1, 1])
    with top_left:
        _render_starter_task_guide(starter_name, starter_task, guided_mode)
    with top_right:
        _render_project_status()

    question = st.text_area("Task Input", key="task_input", height=140)

    with st.expander("Attach your own files or URLs", expanded=starter_name == "Custom task"):
        uploaded_context_files = st.file_uploader(
            "Attach context files",
            accept_multiple_files=True,
            help="Upload your own files here. Built-in starter tasks already attach sample files automatically.",
        )
        context_urls_raw = st.text_area(
            "Attach context URLs",
            value="",
            help="One URL per line. Starter tasks may also include built-in sample context.",
        )

    uploaded_file_paths = _persist_uploaded_files(uploaded_context_files)
    context_files = _merge_distinct(starter_context_files, uploaded_file_paths)
    context_urls = _merge_distinct(starter_context_urls, _parse_context_urls(context_urls_raw))

    left, right = st.columns([1, 1])
    with left:
        _render_plan_preview(
            question,
            enable_review,
            context_files,
            context_urls,
            allow_inline_context_files,
            allow_inline_context_urls,
        )
    with right:
        st.subheader("Current Input")
        st.write(f"Starter task: `{starter_name}`")
        st.write(f"Runner: `{runner_name}`")
        st.write(f"Review enabled: `{enable_review}`")
        st.write(f"Context files in use: `{len(context_files)}`")
        st.write(f"Context URLs in use: `{len(context_urls)}`")
        if context_files:
            st.markdown("**Context Files In Use**")
            for path in context_files:
                st.write(f"- {Path(path).name}")
        if context_urls:
            st.markdown("**Context URLs In Use**")
            for url in context_urls:
                st.write(f"- {url}")

    settings_left, settings_right = st.columns([1, 1])
    with settings_left:
        st.subheader("Current Settings")
        st.write(f"Runner: `{runner_name}`")
        st.write(f"Model: `{model if runner_name == 'ollama' else 'n/a'}`")
        st.write(f"Review enabled: `{enable_review}`")
        st.write(f"Inline file-path discovery: `{allow_inline_context_files}`")
        st.write(f"Inline URL discovery: `{allow_inline_context_urls}`")
        st.write(f"Attached context files: `{len(context_files)}`")
        st.write(f"Attached context URLs: `{len(context_urls)}`")
        st.write(f"Audit dir: `{audit_dir or 'disabled'}`")
        st.write(f"Acceptance report dir: `{acceptance_report_dir or 'disabled'}`")
        st.write(f"Cache dir: `{cache_dir or 'disabled'}`")
    with settings_right:
        runs_tab, acceptance_tab, cache_tab = st.tabs(["Runs", "Acceptance", "Cache"])
        with runs_tab:
            if audit_dir:
                _render_recent_runs(audit_dir)
            else:
                st.subheader("Recent Runs")
                st.info("Set an audit directory to enable persisted run history.")
        with acceptance_tab:
            if acceptance_report_dir:
                _render_acceptance_reports(acceptance_report_dir)
            else:
                st.subheader("Acceptance Reports")
                st.info("Set an acceptance report directory to inspect persisted acceptance runs.")
        with cache_tab:
            if cache_dir:
                _render_cache_snapshot(cache_dir, float(cache_max_age_seconds))
            else:
                st.subheader("Cache Health")
                st.info("Set a cache directory to inspect local cache health.")

    if st.button("Run Workflow", type="primary", use_container_width=True):
        st.session_state["last_error"] = None
        st.session_state["last_result"] = None
        try:
            supervisor = build_supervisor(
                runner_name=runner_name,
                model=model,
                base_url=base_url,
                enable_review=enable_review,
                allow_inline_context_files=allow_inline_context_files,
                allow_inline_context_urls=allow_inline_context_urls,
                audit_dir=audit_dir or None,
                cache_dir=cache_dir or None,
                cache_max_age_seconds=cache_max_age_seconds if cache_dir else None,
                max_retries=int(max_retries),
                retry_backoff_seconds=float(retry_backoff_seconds),
            )
            with st.spinner("Running workflow..."):
                st.session_state["last_result"] = supervisor.run_with_context(
                    question,
                    context_files=context_files,
                    context_urls=context_urls,
                )
        except Exception as exc:  # pragma: no cover - UI error display path
            st.session_state["last_error"] = str(exc)

    last_error = st.session_state["last_error"]
    last_result = st.session_state["last_result"]

    if last_error:
        st.error(last_error)

    if last_result is not None:
        result = last_result
        st.divider()
        st.success("Workflow completed.")
        if guided_mode:
            st.info(
                "Nice, the workflow completed end to end. "
                f"Suggested next step: {starter_task['next_step']}"
            )
        overview_tab, intermediate_tab, tools_tab, traces_tab, export_tab, raw_tab = st.tabs(
            [
                "Overview",
                "Intermediates",
                "Tools",
                "Traces",
                "Export",
                "Raw JSON",
            ]
        )
        with overview_tab:
            _render_result_overview(result)
            _render_outputs(result)
        with intermediate_tab:
            _render_intermediate_result(result)
            _render_review(result)
        with tools_tab:
            _render_tool_invocations(result)
        with traces_tab:
            _render_traces(result)
        with export_tab:
            _render_downloads(result)
        with raw_tab:
            st.json(result.model_dump())

    st.divider()
    st.caption(
        "Start the UI with `streamlit run app.py`. "
        "For first-time testers, keep Guided mode on and begin with one of the starter tasks. "
        "If you want persisted run history, acceptance report inspection, or cache health snapshots, "
        "configure the corresponding directories in Advanced settings."
    )


if __name__ == "__main__":
    main()
