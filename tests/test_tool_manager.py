from pathlib import Path

import pytest

from tools.csv_analysis_tool import CSVAnalysisTool
from tools.data_computation_tool import DataComputationTool
from tools.errors import ConfigurationError, ToolExecutionError
from tools.http_fetch_tool import HttpFetchTool
from tools.json_analysis_tool import JSONAnalysisTool
from tools.local_file_tool import LocalFileContextTool
from tools.registry import ToolManager, find_http_urls, find_local_file_paths

from .http_fixtures import install_http_fetch_stub


def test_find_local_file_paths_resolves_backticked_files(tmp_path: Path) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("hello", encoding="utf-8")

    paths = find_local_file_paths(f"Please inspect `{notes}` and summarize it.")

    assert paths == [notes.resolve()]


def test_find_http_urls_resolves_urls_from_question() -> None:
    urls = find_http_urls("Inspect https://example.com/report and summarize it.")

    assert urls == ["https://example.com/report"]


def test_tool_manager_runs_local_file_and_csv_tools(tmp_path: Path) -> None:
    csv_path = tmp_path / "inventory.csv"
    csv_path.write_text("item,count,price\nA,3,1.5\nB,4,2.0\n", encoding="utf-8")

    manager = ToolManager(
        tools=[
            LocalFileContextTool(),
            CSVAnalysisTool(),
        ]
    )

    context, invocations = manager.run_for_task(
        task_type="analysis",
        question="Analyze this dataset and tell me what stands out.",
        explicit_paths=[csv_path],
    )

    assert len(invocations) == 2
    assert [invocation.tool_name for invocation in invocations] == [
        "local_file_context",
        "csv_analysis",
    ]
    assert context["local_files"][0]["name"] == "inventory.csv"
    assert context["csv_summaries"][0]["columns"] == ["item", "count", "price"]
    assert context["csv_summaries"][0]["numeric_columns"][0]["name"] == "count"


def test_tool_manager_ignores_inline_paths_by_default(tmp_path: Path) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("hello", encoding="utf-8")

    manager = ToolManager(
        tools=[
            LocalFileContextTool(),
        ]
    )

    context, invocations = manager.run_for_task(
        task_type="analysis",
        question=f"Analyze `{notes}` and tell me what stands out.",
    )

    assert context == {}
    assert invocations == []


def test_tool_manager_runs_http_fetch_tool(monkeypatch) -> None:
    url = install_http_fetch_stub(monkeypatch, body="server metrics are stable")
    manager = ToolManager(
        tools=[
            HttpFetchTool(),
        ]
    )

    context, invocations = manager.run_for_task(
        task_type="analysis",
        question="Analyze this page and tell me what stands out.",
        explicit_urls=[url],
    )

    assert len(invocations) == 1
    assert invocations[0].tool_name == "http_fetch"
    assert context["web_pages"][0]["url"] == url
    assert "server metrics are stable" in context["web_pages"][0]["preview"]


def test_tool_manager_runs_json_analysis_tool(tmp_path: Path) -> None:
    json_path = tmp_path / "metrics.json"
    json_path.write_text(
        (
            '[{"quarter":"2024-Q1","revenue":120,"active_users":400,"churn_rate":0.08},'
            '{"quarter":"2024-Q2","revenue":135,"active_users":430,"churn_rate":0.07}]'
        ),
        encoding="utf-8",
    )

    manager = ToolManager(
        tools=[
            LocalFileContextTool(),
            JSONAnalysisTool(),
        ]
    )

    context, invocations = manager.run_for_task(
        task_type="analysis",
        question="Analyze this JSON snapshot and tell me what stands out.",
        explicit_paths=[json_path],
    )

    assert [invocation.tool_name for invocation in invocations] == [
        "local_file_context",
        "json_analysis",
    ]
    assert context["json_summaries"][0]["top_level_type"] == "array"
    assert context["json_summaries"][0]["field_names"] == [
        "quarter",
        "revenue",
        "active_users",
        "churn_rate",
    ]
    assert [field["name"] for field in context["json_summaries"][0]["numeric_fields"]] == [
        "revenue",
        "active_users",
        "churn_rate",
    ]


def test_data_computation_tool_summarizes_csv_trends(tmp_path: Path) -> None:
    csv_path = tmp_path / "metrics.csv"
    csv_path.write_text(
        "quarter,revenue,active_users,churn_rate\n2024-Q1,120,400,0.08\n2024-Q2,135,430,0.07\n2024-Q3,150,470,0.06\n",
        encoding="utf-8",
    )

    manager = ToolManager(
        tools=[DataComputationTool()],
    )

    context, invocations = manager.run_for_task(
        task_type="analysis",
        question="Analyze this dataset and compute the biggest changes.",
        explicit_paths=[csv_path],
    )

    assert [invocation.tool_name for invocation in invocations] == ["data_computation"]
    revenue = context["dataset_metrics"][0]["numeric_fields"][0]
    assert context["dataset_metrics"][0]["label_field"] == "quarter"
    assert revenue["name"] == "revenue"
    assert revenue["absolute_change"] == 30.0
    assert revenue["percent_change"] == 25.0
    assert revenue["trend"] == "up"


def test_data_computation_tool_summarizes_json_trends(tmp_path: Path) -> None:
    json_path = tmp_path / "metrics.json"
    json_path.write_text(
        (
            '[{"quarter":"2024-Q1","revenue":120,"active_users":400,"churn_rate":0.08},'
            '{"quarter":"2024-Q2","revenue":135,"active_users":430,"churn_rate":0.07}]'
        ),
        encoding="utf-8",
    )

    manager = ToolManager(
        tools=[DataComputationTool()],
    )

    context, invocations = manager.run_for_task(
        task_type="analysis",
        question="Analyze this JSON snapshot and compute the biggest changes.",
        explicit_paths=[json_path],
    )

    assert [invocation.tool_name for invocation in invocations] == ["data_computation"]
    revenue = context["dataset_metrics"][0]["numeric_fields"][0]
    assert context["dataset_metrics"][0]["format"] == "json"
    assert context["dataset_metrics"][0]["top_level_type"] == "array"
    assert revenue["first"] == 120.0
    assert revenue["last"] == 135.0
    assert revenue["absolute_change"] == 15.0
    assert revenue["trend"] == "up"


def test_tool_manager_allows_inline_urls_when_enabled(monkeypatch) -> None:
    url = install_http_fetch_stub(monkeypatch, body="server metrics are stable")
    manager = ToolManager(
        tools=[HttpFetchTool()],
        allow_question_urls=True,
    )

    context, invocations = manager.run_for_task(
        task_type="analysis",
        question=f"Analyze {url} and tell me what stands out.",
    )

    assert len(invocations) == 1
    assert invocations[0].tool_name == "http_fetch"
    assert context["web_pages"][0]["url"] == url


def test_tool_manager_rejects_invalid_explicit_context_file() -> None:
    manager = ToolManager(
        tools=[LocalFileContextTool()],
    )

    with pytest.raises(ConfigurationError, match="Invalid context file"):
        manager.run_for_task(
            task_type="analysis",
            question="Analyze this dataset.",
            explicit_paths=["missing.csv"],
        )


def test_tool_manager_raises_when_tool_execution_fails() -> None:
    manager = ToolManager(
        tools=[HttpFetchTool()],
    )

    with pytest.raises(ToolExecutionError, match="http_fetch failed"):
        manager.run_for_task(
            task_type="analysis",
            question="Analyze this page and tell me what stands out.",
            explicit_urls=["http://127.0.0.1:1/context"],
        )
