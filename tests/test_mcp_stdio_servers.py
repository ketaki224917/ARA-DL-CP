"""End-to-end stdio startup verification for all three ARA MCP servers."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import StdioServerParameters

from ara.mcp_client.client import MCPClient

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_all_ara_servers_start_over_stdio_and_expose_expected_tools() -> None:
    async def exercise() -> None:
        server_modules = {
            "rag": "ara.mcp_servers.rag_server",
            "web-search": "ara.mcp_servers.web_search_server",
            "dl-model": "ara.mcp_servers.dl_model_server",
        }
        async with MCPClient(timeout_seconds=30, retries=0) as client:
            for name, module in server_modules.items():
                await client.connect(
                    name,
                    StdioServerParameters(
                        command=sys.executable,
                        args=["-m", module],
                        cwd=str(_PROJECT_ROOT),
                    ),
                )

            rag_tools = await client.list_tools("rag")
            web_tools = await client.list_tools("web-search")
            dl_tools = await client.list_tools("dl-model")
            assert {tool.name for tool in rag_tools} == {"search_knowledge_base", "get_chunk"}
            assert {tool.name for tool in web_tools} == {"web_search", "fetch_page"}
            assert {tool.name for tool in dl_tools} == {"score_chunks"}

            not_ready = await client.call_tool(
                "dl-model",
                "score_chunks",
                {"query": "evidence", "chunk_ids": ["chunk:one"]},
            )
            assert not_ready.is_error is False
            assert not_ready.structured_content is not None
            assert not_ready.structured_content["status"] == "not_ready"

    asyncio.run(exercise())
