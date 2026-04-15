from __future__ import annotations

from email.message import Message


def install_http_fetch_stub(
    monkeypatch,
    *,
    body: str,
    expected_url: str = "https://example.com/report",
    content_type: str = "text/plain",
) -> str:
    class FakeResponse:
        def __init__(self) -> None:
            headers = Message()
            headers["Content-Type"] = content_type
            self.headers = headers
            self._body = body.encode("utf-8")

        def read(self, size: int = -1) -> bytes:
            if size < 0:
                return self._body
            return self._body[:size]

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    def fake_urlopen(request, timeout: float = 5.0) -> FakeResponse:
        url = getattr(request, "full_url", request)
        assert url == expected_url
        assert timeout > 0
        return FakeResponse()

    monkeypatch.setattr("tools.http_fetch_tool.urlopen", fake_urlopen)
    return expected_url
