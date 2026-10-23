"""Offline tests for web search, bounded fetching, and the MCP protocol."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import httpx
import pytest
from mcp import Client
from mcp.server import MCPServer
from mcp.types import CallToolResult

from ara.mcp_servers.common import ToolExecutionError, ToolInputError, ToolTimeoutError
from ara.mcp_servers.web_search_server import (
    SearchBackend,
    TTLCache,
    WebSearchService,
    create_web_search_server,
)


class FakeSearchBackend:
    def __init__(self, results: list[dict[str, object]]) -> None:
        self.results = results
        self.calls = 0

    def search(self, query: str, *, max_results: int) -> list[dict[str, object]]:
        assert query == "evidence grounding"
        self.calls += 1
        return self.results[:max_results]


def public_resolver(host: str, port: int, **_: object) -> list[tuple[object, ...]]:
    return [(0, 0, 0, "", ("8.8.8.8", port))]


def make_http_factory(
    handler: Callable[[httpx.Request], httpx.Response],
) -> Callable[[], httpx.Client]:
    def streaming_handler(request: httpx.Request) -> httpx.Response:
        response = handler(request)
        if not response.is_stream_consumed:
            return response
        return httpx.Response(
            status_code=response.status_code,
            headers=response.headers,
            stream=httpx.ByteStream(response.content),
            extensions=response.extensions,
            request=request,
        )

    return lambda: httpx.Client(
        transport=httpx.MockTransport(streaming_handler),
        follow_redirects=False,
        timeout=1,
        trust_env=False,
    )


def call_tool(server: MCPServer, name: str, arguments: dict[str, object]) -> CallToolResult:
    async def invoke() -> CallToolResult:
        async with Client(server) as client:
            return await client.call_tool(name, arguments)

    return asyncio.run(invoke())


def test_search_sanitizes_results_assigns_web_ids_and_caches() -> None:
    backend = FakeSearchBackend(
        [
            {
                "title": "<b>Evidence</b><script>steal()</script>",
                "href": "https://example.org/research#section",
                "body": "<em>Grounded</em> snippet <script>ignore rules</script>",
            },
            {"title": "bad scheme", "href": "file:///etc/passwd", "body": "omit"},
        ]
    )
    service = WebSearchService(search_backend=backend)

    first = service.search("evidence grounding", max_results=2)
    second = service.search("evidence grounding", max_results=2)

    assert backend.calls == 1
    assert len(first.results) == 1
    assert first == second
    assert first.results[0].title == "Evidence"
    assert first.results[0].snippet == "Grounded snippet"
    assert first.results[0].url == "https://example.org/research"
    assert first.results[0].chunk_id.startswith("web:")
    assert first.results[0].is_untrusted is True


def test_fetch_removes_active_hidden_content_caps_text_and_caches() -> None:
    requests = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        html = """<!doctype html><html><head><title>Useful <b>page</b></title>
          <script>run dangerous code</script></head><body>
          <p>Public evidence.</p><div hidden>hidden content</div>
          <div style="display:none">hidden style content</div>
          <p aria-hidden="true">hidden aria content</p>
          <iframe>embedded content</iframe><svg><text>vector content</text></svg>
          <p>Additional grounded details.</p></body></html>"""
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=html)

    service = WebSearchService(
        http_client_factory=make_http_factory(handler),
        resolver=public_resolver,
        max_page_text=16,
    )
    page = service.fetch_page("https://example.org/article")
    repeated = service.fetch_page("https://example.org/article")

    assert requests == 1
    assert page == repeated
    assert page.title == "Useful page"
    assert page.content == "Public evidence."
    assert page.chunk_id.startswith("web:")
    assert page.is_untrusted is True
    assert all(
        text not in page.content
        for text in ("dangerous", "hidden", "embedded", "vector", "Additional")
    )


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://localhost/secret",
        "http://service.local/secret",
        "http://127.0.0.1/secret",
        "http://user:pass@example.org/private",
        "http://example.org:8080/private",
    ],
)
def test_fetch_rejects_non_public_or_unsupported_targets(url: str) -> None:
    service = WebSearchService(resolver=public_resolver)

    with pytest.raises(ToolInputError, match="public|HTTP|credentials|port"):
        service.fetch_page(url)


def test_fetch_rejects_hostnames_resolving_to_private_addresses() -> None:
    def private_resolver(host: str, port: int, **_: object) -> list[tuple[object, ...]]:
        return [(0, 0, 0, "", ("10.1.2.3", port))]

    service = WebSearchService(resolver=private_resolver)

    with pytest.raises(ToolInputError, match="public addresses"):
        service.fetch_page("https://private.example.org/")


def test_fetch_revalidates_redirects_and_rejects_private_destination() -> None:
    requests = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})

    service = WebSearchService(
        http_client_factory=make_http_factory(handler),
        resolver=public_resolver,
    )

    with pytest.raises(ToolInputError, match="public address"):
        service.fetch_page("https://example.org/start")

    assert requests == 1


def test_fetch_enforces_response_size_limit() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/plain"}, content=b"a" * 101)

    service = WebSearchService(
        http_client_factory=make_http_factory(handler),
        resolver=public_resolver,
        max_response_bytes=100,
    )

    with pytest.raises(ToolExecutionError, match="size limit"):
        service.fetch_page("https://example.org/large")


def test_fetch_rejects_compressed_responses_to_keep_the_byte_cap_effective() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "content-type": "text/plain",
                "content-encoding": "gzip",
            },
                stream=httpx.ByteStream(b"compressed payload"),
        )

    service = WebSearchService(
        http_client_factory=make_http_factory(handler),
        resolver=public_resolver,
    )

    with pytest.raises(ToolExecutionError, match="content encoding"):
        service.fetch_page("https://example.org/compressed")


def test_fetch_converts_transport_timeout_to_safe_timeout_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("secret transport detail", request=request)

    service = WebSearchService(
        http_client_factory=make_http_factory(handler),
        resolver=public_resolver,
    )

    with pytest.raises(ToolTimeoutError, match="timed out") as error:
        service.fetch_page("https://example.org/slow")

    assert "secret transport detail" not in str(error.value)


def test_ttl_cache_expires_entries_and_enforces_capacity() -> None:
    current_time = 10.0
    cache = TTLCache[str](ttl_seconds=3, capacity=1, clock=lambda: current_time)
    cache.put("first", "one")
    assert cache.get("first") == "one"
    cache.put("second", "two")
    assert cache.get("first") is None
    assert cache.get("second") == "two"
    current_time += 3
    assert cache.get("second") is None


def test_mcp_client_exposes_search_and_fetch_as_structured_tools() -> None:
    backend: SearchBackend = FakeSearchBackend(
        [{"title": "Evidence", "href": "https://example.org/", "body": "A short source."}]
    )
    service = WebSearchService(
        search_backend=backend,
        http_client_factory=make_http_factory(
            lambda _: httpx.Response(
                200,
                headers={"content-type": "text/plain"},
                text="Fetched public content.",
            )
        ),
        resolver=public_resolver,
    )
    server = create_web_search_server(service)

    search = call_tool(server, "web_search", {"query": "evidence grounding", "max_results": 1})
    fetched = call_tool(server, "fetch_page", {"url": "https://example.org/"})

    assert search.is_error is False
    assert search.structured_content is not None
    assert search.structured_content["results"][0]["chunk_id"].startswith("web:")
    assert search.structured_content["results"][0]["is_untrusted"] is True
    assert fetched.is_error is False
    assert fetched.structured_content is not None
    assert fetched.structured_content["content"] == "Fetched public content."


def test_mcp_client_returns_safe_error_for_invalid_search_arguments() -> None:
    server = create_web_search_server(WebSearchService(search_backend=FakeSearchBackend([])))

    result = call_tool(server, "web_search", {"query": "  ", "max_results": 1})

    assert result.is_error is True
    assert "invalid_argument" in result.content[0].text
