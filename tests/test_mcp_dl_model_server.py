"""MCP-client tests for the typed custom-model scoring stub."""

from __future__ import annotations

import asyncio

from mcp import Client
from mcp.server import MCPServer
from mcp.types import CallToolResult

from ara.mcp_servers.dl_model_server import create_dl_model_server


def call_tool(server: MCPServer, arguments: dict[str, object]) -> CallToolResult:
    async def invoke() -> CallToolResult:
        async with Client(server) as client:
            return await client.call_tool("score_chunks", arguments)

    return asyncio.run(invoke())


def test_score_chunks_exposes_typed_not_ready_response() -> None:
    result = call_tool(
        create_dl_model_server(),
        {"query": "evidence grounding", "chunk_ids": ["chunk:one", "chunk:two"]},
    )

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["status"] == "not_ready"
    assert result.structured_content["scores"] == []
    assert "not trained or loaded" in result.structured_content["message"]


def test_score_chunks_rejects_empty_query_and_chunk_lists() -> None:
    server = create_dl_model_server()
    empty_query = call_tool(server, {"query": " ", "chunk_ids": ["chunk:one"]})
    empty_ids = call_tool(server, {"query": "query", "chunk_ids": []})

    assert empty_query.is_error is True
    assert "invalid_argument" in empty_query.content[0].text
    assert empty_ids.is_error is True
    assert "invalid_argument" in empty_ids.content[0].text


def test_score_chunks_rejects_duplicate_ids() -> None:
    duplicates = call_tool(
        create_dl_model_server(),
        {"query": "query", "chunk_ids": ["chunk:one", "chunk:one"]},
    )

    assert duplicates.is_error is True
    assert "duplicate" in duplicates.content[0].text
