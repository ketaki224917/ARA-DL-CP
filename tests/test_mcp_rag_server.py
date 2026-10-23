"""MCP-client tests for local RAG search and chunk lookup tools."""

from __future__ import annotations

import asyncio

from mcp import Client
from mcp.server import MCPServer
from mcp.types import CallToolResult

from ara.config import Settings
from ara.mcp_servers.rag_server import RAGService, create_rag_server
from ara.rag.bm25 import BM25Index
from ara.rag.chunking import DocumentChunk
from ara.rag.vectorstore import InMemoryVectorStore


class FakeEmbedder:
    """Deterministic query embedder for MCP protocol tests."""

    def __enter__(self) -> FakeEmbedder:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0]


def make_server() -> MCPServer:
    hybrid_chunk = DocumentChunk(
        chunk_id="chunk:hybrid",
        text="Hybrid retrieval combines dense vectors and BM25 using reciprocal rank fusion.",
        source="retrieval.md",
        page=None,
        char_start=0,
        char_end=78,
    )
    lexical_chunk = DocumentChunk(
        chunk_id="chunk:lexical",
        text="BM25 is a lexical ranking method based on token overlap.",
        source="bm25.md",
        page=None,
        char_start=0,
        char_end=56,
    )
    store = InMemoryVectorStore()
    store.upsert([hybrid_chunk, lexical_chunk], [[1.0, 0.0], [0.0, 1.0]])
    settings = Settings(_env_file=None)
    service = RAGService(
        settings=settings,
        vector_store=store,
        lexical_index=BM25Index([hybrid_chunk, lexical_chunk]),
        embedder_factory=lambda _: FakeEmbedder(),
    )
    return create_rag_server(service)


def call_tool(server: MCPServer, name: str, arguments: dict[str, object]) -> CallToolResult:
    async def invoke() -> CallToolResult:
        async with Client(server) as client:
            return await client.call_tool(name, arguments)

    return asyncio.run(invoke())


def test_search_knowledge_base_returns_structured_cited_hits() -> None:
    result = call_tool(
        make_server(),
        "search_knowledge_base",
        {"query": "hybrid retrieval", "top_k": 1, "candidate_k": 2},
    )

    assert result.is_error is False
    assert result.structured_content is not None
    hits = result.structured_content["results"]
    assert hits[0]["chunk_id"] == "chunk:hybrid"
    assert hits[0]["source"] == "retrieval.md"
    assert hits[0]["dense_rank"] == 1


def test_search_tool_returns_safe_validation_error_for_blank_query() -> None:
    result = call_tool(
        make_server(),
        "search_knowledge_base",
        {"query": "  ", "top_k": 1, "candidate_k": 1},
    )

    assert result.is_error is True
    assert "invalid_argument" in result.content[0].text


def test_get_chunk_returns_text_provenance_and_not_found_error() -> None:
    server = make_server()
    found = call_tool(server, "get_chunk", {"chunk_id": "chunk:hybrid"})
    missing = call_tool(server, "get_chunk", {"chunk_id": "chunk:missing"})

    assert found.is_error is False
    assert found.structured_content is not None
    assert found.structured_content["source"] == "retrieval.md"
    assert found.structured_content["text"].startswith("Hybrid retrieval")
    assert missing.is_error is True
    assert "not_found" in missing.content[0].text


def test_search_tool_rejects_boolean_limits() -> None:
    result = call_tool(
        make_server(),
        "search_knowledge_base",
        {"query": "hybrid retrieval", "top_k": True, "candidate_k": 2},
    )

    assert result.is_error is True
