"""MCP tools for hybrid retrieval and fetching indexed evidence chunks."""

from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, TypeVar

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr

from ara.mcp_servers.common import (
    ToolNotFoundError,
    error_payload,
    get_server_logger,
    log_tool_call,
    require_int,
    require_text,
)
from ara.rag.bm25 import BM25Index
from ara.rag.chunking import DocumentChunk
from ara.rag.retriever import HybridRetriever, QueryEmbedder
from ara.rag.vectorstore import ChromaVectorStore, VectorStore

if TYPE_CHECKING:
    from ara.config import Settings

_MAX_QUERY_LENGTH = 2_000
_MAX_CHUNK_ID_LENGTH = 128
_MAX_TOP_K = 50
_MAX_CANDIDATE_K = 200
_T = TypeVar("_T")


class SearchHit(BaseModel):
    """A retrieved chunk with citations and ranking provenance."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    text: str
    source: str
    page: int | None
    score: float
    dense_rank: int | None
    bm25_rank: int | None
    dense_score: float | None
    bm25_score: float | None


class SearchResponse(BaseModel):
    """Structured output from hybrid retrieval."""

    model_config = ConfigDict(extra="forbid")

    results: list[SearchHit]


class ChunkDetails(BaseModel):
    """A stored chunk and its source provenance."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    text: str
    source: str
    page: int | None
    char_start: int
    char_end: int


class RAGService:
    """Retrieval service with optional dependencies for isolated MCP tests."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        vector_store: VectorStore | None = None,
        lexical_index: BM25Index | None = None,
        embedder_factory: (
            Callable[[Settings], AbstractContextManager[QueryEmbedder]] | None
        ) = None,
    ) -> None:
        self._settings = settings
        self._vector_store = vector_store
        self._lexical_index = lexical_index
        self._embedder_factory = embedder_factory

    def search(
        self,
        query: str,
        *,
        top_k: int = 8,
        candidate_k: int = 32,
    ) -> SearchResponse:
        """Run bounded hybrid retrieval and return citation-ready results."""
        normalized_query = require_text(query, "query", max_length=_MAX_QUERY_LENGTH)
        result_limit = require_int(top_k, "top_k", maximum=_MAX_TOP_K)
        candidate_limit = require_int(
            candidate_k,
            "candidate_k",
            minimum=result_limit,
            maximum=_MAX_CANDIDATE_K,
        )
        settings = self._resolve_settings()
        vector_store = self._resolve_vector_store(settings)
        lexical_index = self._resolve_lexical_index(settings)
        with self._new_embedder(settings) as embedder:
            results = HybridRetriever(vector_store, lexical_index, embedder).search(
                normalized_query,
                top_k=result_limit,
                candidate_k=candidate_limit,
            )
        return SearchResponse(
            results=[
                SearchHit(
                    chunk_id=result.chunk.chunk_id,
                    text=result.chunk.text,
                    source=result.chunk.source,
                    page=result.chunk.page,
                    score=result.score,
                    dense_rank=result.dense_rank,
                    bm25_rank=result.bm25_rank,
                    dense_score=result.dense_score,
                    bm25_score=result.bm25_score,
                )
                for result in results
            ]
        )

    def get_chunk(self, chunk_id: str) -> ChunkDetails:
        """Fetch a single indexed chunk by its stable ID."""
        normalized_id = require_text(
            chunk_id,
            "chunk_id",
            max_length=_MAX_CHUNK_ID_LENGTH,
        )
        chunk = self._resolve_vector_store(self._resolve_settings()).get([normalized_id])
        if not chunk:
            raise ToolNotFoundError("No indexed chunk has that ID.")
        return _chunk_details(chunk[0])

    def _resolve_settings(self) -> Settings:
        if self._settings is None:
            from ara.config import load_settings

            self._settings = load_settings()
        return self._settings

    def _resolve_vector_store(self, settings: Settings) -> VectorStore:
        if self._vector_store is None:
            self._vector_store = ChromaVectorStore(settings.vector_store_dir)
        return self._vector_store

    def _resolve_lexical_index(self, settings: Settings) -> BM25Index:
        if self._lexical_index is None:
            self._lexical_index = BM25Index.load(settings.bm25_index_path)
        return self._lexical_index

    def _new_embedder(self, settings: Settings) -> AbstractContextManager[QueryEmbedder]:
        if self._embedder_factory is not None:
            return self._embedder_factory(settings)
        from ara.rag.embeddings import OllamaEmbeddings

        return OllamaEmbeddings(settings)


def create_rag_server(service: RAGService | None = None) -> MCPServer:
    """Build an MCP server exposing hybrid search and stable-ID chunk lookup."""
    rag_service = service if service is not None else RAGService()
    server = MCPServer(
        name="ARA RAG",
        instructions="Retrieve evidence from ARA's indexed local document corpus.",
    )

    @server.tool()
    def search_knowledge_base(
        query: StrictStr,
        top_k: StrictInt = 8,
        candidate_k: StrictInt = 32,
    ) -> SearchResponse:
        """Search local documents with dense and BM25 retrieval fused by RRF."""
        return _invoke_tool(
            "search_knowledge_base",
            lambda: rag_service.search(query, top_k=top_k, candidate_k=candidate_k),
        )

    @server.tool()
    def get_chunk(chunk_id: StrictStr) -> ChunkDetails:
        """Return the complete text and provenance for one indexed chunk ID."""
        return _invoke_tool("get_chunk", lambda: rag_service.get_chunk(chunk_id))

    return server


def _invoke_tool(tool_name: str, operation: Callable[[], _T]) -> _T:
    """Log a tool operation and translate failures to safe MCP tool errors."""
    logger = get_server_logger("rag")
    try:
        with log_tool_call(logger, server_name="rag", tool_name=tool_name):
            return operation()
    except Exception as exc:
        payload = json.dumps(error_payload(exc), ensure_ascii=False, separators=(",", ":"))
        raise ToolError(payload) from exc


def _chunk_details(chunk: DocumentChunk) -> ChunkDetails:
    """Convert a chunk record into the structured MCP response model."""
    return ChunkDetails(
        chunk_id=chunk.chunk_id,
        text=chunk.text,
        source=chunk.source,
        page=chunk.page,
        char_start=chunk.char_start,
        char_end=chunk.char_end,
    )


def main() -> None:
    """Run the RAG MCP server over stdio."""
    create_rag_server().run()


if __name__ == "__main__":
    main()
