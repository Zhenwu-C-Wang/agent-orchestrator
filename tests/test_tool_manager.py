from pathlib import Path

from tests.http_fixtures import install_http_fetch_stub
from tools.csv_analysis_tool import CSVAnalysisTool
from tools.http_fetch_tool import HttpFetchTool
from tools.local_file_tool import LocalFileContextTool
from tools.registry import ToolManager, find_http_urls, find_local_file_paths


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
        question=f"Analyze `{csv_path}` and tell me what stands out.",
    )

    assert len(invocations) == 2
    assert [invocation.tool_name for invocation in invocations] == [
        "local_file_context",
        "csv_analysis",
    ]
    assert context["local_files"][0]["name"] == "inventory.csv"
    assert context["csv_summaries"][0]["columns"] == ["item", "count", "price"]
    assert context["csv_summaries"][0]["numeric_columns"][0]["name"] == "count"


def test_tool_manager_runs_http_fetch_tool(monkeypatch) -> None:
    url = install_http_fetch_stub(monkeypatch, body="server metrics are stable")
    manager = ToolManager(
        tools=[
            HttpFetchTool(),
        ]
    )

    context, invocations = manager.run_for_task(
        task_type="analysis",
        question=f"Analyze {url} and tell me what stands out.",
    )

    assert len(invocations) == 1
    assert invocations[0].tool_name == "http_fetch"
    assert context["web_pages"][0]["url"] == url
    assert "server metrics are stable" in context["web_pages"][0]["preview"]
