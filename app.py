from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import streamlit as st

from orchestrator.bootstrap import build_supervisor, format_markdown, format_pretty
from orchestrator.planner import TaskPlanner
from orchestrator.project_status import load_project_status
from schemas.result_schema import WorkflowResult
from tools.audit import AuditStore

DEFAULT_QUESTION = "How should I bootstrap a supervisor-worker agent system?"


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


def _render_plan_preview(
    question: str,
    enable_review: bool,
    context_files: list[str],
    context_urls: list[str],
) -> None:
    planner = TaskPlanner(enable_review=enable_review)
    plan = planner.build_plan(
        question,
        context_files=context_files,
        context_urls=context_urls,
    )

    st.subheader("Workflow Plan")
    st.caption(plan.rationale)
    st.markdown(f"**Selected workflow:** `{plan.workflow_name}`")
    if context_files:
        st.write(f"Context files: `{len(context_files)}` attached")
    if context_urls:
        st.write(f"Context URLs: `{len(context_urls)}` attached")
    for index, step in enumerate(plan.steps, start=1):
        st.write(f"{index}. `{step.worker_name}` -> `{step.output_schema}`")


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
        return

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
            st.write(f"Workflow: `{selected.result.workflow_plan.workflow_name}`")
            st.write(f"Tool invocations: `{len(selected.result.tool_invocations)}`")
            st.write(selected.result.final_answer.answer)
        if selected.error:
            st.error(selected.error)


def main() -> None:
    st.set_page_config(page_title="Agent Orchestrator", layout="wide")
    st.title("Agent Orchestrator")
    st.caption("Run the local supervisor/worker workflow and inspect planning, traces, and outputs.")

    if "last_result" not in st.session_state:
        st.session_state["last_result"] = None
    if "last_error" not in st.session_state:
        st.session_state["last_error"] = None

    with st.sidebar:
        st.header("Run Settings")
        runner_name = st.selectbox("Runner", options=["fake", "ollama"], index=0)
        model = st.text_input("Model", value="llama3.1", disabled=runner_name == "fake")
        base_url = st.text_input("Ollama Base URL", value="http://localhost:11434")
        enable_review = st.checkbox("Enable review stage", value=False)
        uploaded_context_files = st.file_uploader(
            "Attach context files",
            accept_multiple_files=True,
        )
        context_urls_raw = st.text_area(
            "Attach context URLs",
            value="",
            help="One URL per line.",
        )
        audit_dir = st.text_input("Audit directory", value="artifacts/runs")
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

    question = st.text_area("Task Input", value=DEFAULT_QUESTION, height=140)
    context_files = _persist_uploaded_files(uploaded_context_files)
    context_urls = _parse_context_urls(context_urls_raw)

    left, right = st.columns([1, 1])
    with left:
        _render_plan_preview(question, enable_review, context_files, context_urls)
    with right:
        _render_project_status()

    settings_left, settings_right = st.columns([1, 1])
    with settings_left:
        st.subheader("Current Settings")
        st.write(f"Runner: `{runner_name}`")
        st.write(f"Model: `{model if runner_name == 'ollama' else 'n/a'}`")
        st.write(f"Review enabled: `{enable_review}`")
        st.write(f"Attached context files: `{len(context_files)}`")
        st.write(f"Attached context URLs: `{len(context_urls)}`")
        st.write(f"Audit dir: `{audit_dir or 'disabled'}`")
        st.write(f"Cache dir: `{cache_dir or 'disabled'}`")
    with settings_right:
        if audit_dir:
            _render_recent_runs(audit_dir)
        else:
            st.subheader("Recent Runs")
            st.info("Set an audit directory to enable persisted run history.")

    if st.button("Run Workflow", type="primary", use_container_width=True):
        st.session_state["last_error"] = None
        st.session_state["last_result"] = None
        try:
            supervisor = build_supervisor(
                runner_name=runner_name,
                model=model,
                base_url=base_url,
                enable_review=enable_review,
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
        _render_intermediate_result(result)
        _render_outputs(result)
        _render_tool_invocations(result)
        _render_traces(result)
        _render_downloads(result)

        with st.expander("Raw JSON"):
            st.json(result.model_dump())

    st.divider()
    st.caption(
        "Start the UI with `streamlit run app.py`. "
        "If you want persisted run history, provide an audit directory in the sidebar."
    )


if __name__ == "__main__":
    main()
