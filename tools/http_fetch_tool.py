from __future__ import annotations

from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tools.registry import ToolExecutionResult


class HttpFetchTool:
    name = "http_fetch"
    purpose = "Fetch text-based HTTP content to ground URL-backed analysis and comparison requests."

    def __init__(self, *, timeout_seconds: float = 5.0, max_urls: int = 2, max_chars: int = 4000) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_urls = max_urls
        self.max_chars = max_chars

    def supports(self, *, task_type: str, question: str, context: dict[str, Any]) -> bool:
        return task_type in {"analysis", "comparison"} and bool(context.get("candidate_urls"))

    def run(self, *, task_type: str, question: str, context: dict[str, Any]) -> ToolExecutionResult:
        candidate_urls: list[str] = context.get("candidate_urls", [])
        selected_urls = candidate_urls[: self.max_urls]
        web_pages = [self._fetch_url(url) for url in selected_urls]
        return ToolExecutionResult(
            context_updates={"web_pages": web_pages},
            input_summary=f"{len(selected_urls)} URL(s)",
            output_summary=f"Fetched {len(web_pages)} web page(s)",
            metadata={"urls": selected_urls},
        )

    def _fetch_url(self, url: str) -> dict[str, Any]:
        request = Request(
            url,
            headers={
                "User-Agent": "agent-orchestrator/0.1",
                "Accept": "text/plain,text/html,application/json;q=0.9,*/*;q=0.1",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                content_type = response.headers.get_content_type()
                raw = response.read(self.max_chars)
        except HTTPError as exc:
            raise RuntimeError(f"HTTP fetch failed for {url}: {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"HTTP fetch failed for {url}: {exc.reason}") from exc

        preview = raw.decode("utf-8", errors="replace")
        return {
            "url": url,
            "content_type": content_type,
            "preview": preview,
            "preview_char_count": len(preview),
        }
