"""MCP-client tests for the typed custom-model scoring stub."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp import Client
from mcp.server import MCPServer
from mcp.types import CallToolResult

from ara.config import Settings
from ara.mcp_servers.dl_model_server import DLModelService, create_dl_model_server
from ara.rag.chunking import DocumentChunk
from ara.rag.vectorstore import InMemoryVectorStore


def call_tool(
    server: MCPServer,
    arguments: dict[str, object],
    *,
    name: str = "score_chunks",
) -> CallToolResult:
    async def invoke() -> CallToolResult:
        async with Client(server) as client:
            return await client.call_tool(name, arguments)

    return asyncio.run(invoke())


def test_score_chunks_exposes_typed_not_ready_response(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, dl_export_path=tmp_path / "missing.pt")
    result = call_tool(
        create_dl_model_server(DLModelService(settings=settings)),
        {"query": "evidence grounding", "chunk_ids": ["chunk:one", "chunk:two"]},
    )

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["status"] == "not_ready"
    assert result.structured_content["scores"] == []
    assert "train and export" in result.structured_content["message"]


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


def test_score_chunks_returns_ordered_probabilities_from_injected_scorer(
    tmp_path: Path,
) -> None:
    torch = pytest.importorskip("torch")

    class FakeTokenizer:
        def __call__(self, queries, passages, **kwargs):
            assert queries == ["query text", "query text"]
            assert passages == ["second passage", "first passage"]
            assert kwargs["truncation"] is True
            return {"input_ids": torch.tensor([[1], [2]])}

    class FakeScorer:
        def to(self, device):
            return self

        def eval(self):
            return self

        def __call__(self, **inputs):
            return SimpleNamespace(
                relevance_logits=torch.tensor([0.0, 2.0]),
                credibility_logits=None,
            )

    store = InMemoryVectorStore()
    chunks = [
        DocumentChunk("chunk:first", "first passage", "a.txt", None, 0, 14),
        DocumentChunk("chunk:second", "second passage", "b.txt", None, 0, 15),
    ]
    store.upsert(chunks, [[1.0], [1.0]])
    service = DLModelService(
        settings=Settings(_env_file=None, dl_export_path=tmp_path / "missing.pt"),
        vector_store=store,
        scorer=FakeScorer(),
        tokenizer=FakeTokenizer(),
    )

    result = call_tool(
        create_dl_model_server(service),
        {"query": "query text", "chunk_ids": ["chunk:second", "chunk:first"]},
    )

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["status"] == "ready"
    scores = result.structured_content["scores"]
    assert [score["chunk_id"] for score in scores] == ["chunk:second", "chunk:first"]
    assert scores[0]["relevance_score"] == pytest.approx(0.5)
    assert scores[1]["relevance_score"] == pytest.approx(0.880797, abs=1e-6)
    assert scores[0]["credibility_score"] is None


def test_score_chunks_returns_not_found_for_unknown_chunk_id(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")

    class FakeTokenizer:
        def __call__(self, queries, passages, **kwargs):
            return {"input_ids": torch.ones((len(passages), 1), dtype=torch.long)}

    class FakeScorer:
        def to(self, device):
            return self

        def eval(self):
            return self

        def __call__(self, **inputs):
            return SimpleNamespace(
                relevance_logits=torch.zeros((len(inputs["input_ids"]),)),
                credibility_logits=None,
            )

    service = DLModelService(
        settings=Settings(_env_file=None, dl_export_path=tmp_path / "missing.pt"),
        vector_store=InMemoryVectorStore(),
        scorer=FakeScorer(),
        tokenizer=FakeTokenizer(),
    )
    result = call_tool(
        create_dl_model_server(service),
        {"query": "query", "chunk_ids": ["chunk:missing"]},
    )

    assert result.is_error is True
    assert '"code":"not_found"' in result.content[0].text
