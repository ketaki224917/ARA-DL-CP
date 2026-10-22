"""Tests for hybrid dense and lexical retrieval with reciprocal-rank fusion."""

from typing import Any

import pytest

from ara.rag.bm25 import BM25Index, BM25SearchResult
from ara.rag.chunking import DocumentChunk
from ara.rag.retriever import HybridRetriever, fuse_ranked_results
from ara.rag.vectorstore import InMemoryVectorStore, VectorSearchResult


def chunk(chunk_id: str, text: str) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        text=text,
        source="notes.md",
        page=None,
        char_start=0,
        char_end=len(text),
    )


class FakeDenseStore:
    def __init__(self, results: list[VectorSearchResult]) -> None:
        self.results = results
        self.calls: list[dict[str, Any]] = []

    def search(self, embedding, *, top_k=8, where=None):
        self.calls.append({"embedding": embedding, "top_k": top_k, "where": where})
        return self.results[:top_k]


class FakeEmbedder:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return [0.3, 0.7]


class FakeLexicalIndex:
    def __init__(self, results: list[BM25SearchResult]) -> None:
        self.results = results
        self.calls: list[dict[str, Any]] = []

    def search(self, query: str, *, top_k: int = 8, where=None):
        self.calls.append({"query": query, "top_k": top_k, "where": where})
        return self.results[:top_k]


def test_fusion_rewards_chunks_found_by_both_retrievers() -> None:
    chunks = {key: chunk(key, f"text {key}") for key in ("a", "b", "c")}
    dense = [
        VectorSearchResult(chunks["a"], 0.95),
        VectorSearchResult(chunks["b"], 0.80),
    ]
    lexical = [
        BM25SearchResult(chunks["b"], 3.2),
        BM25SearchResult(chunks["c"], 2.7),
    ]

    matches = fuse_ranked_results(dense, lexical, top_k=3, rrf_k=10)

    assert [match.chunk.chunk_id for match in matches] == ["b", "a", "c"]
    assert matches[0].dense_rank == 2
    assert matches[0].bm25_rank == 1
    assert matches[0].dense_score == pytest.approx(0.80)
    assert matches[0].bm25_score == pytest.approx(3.2)
    assert matches[0].score == pytest.approx(1 / 12 + 1 / 11)


def test_hybrid_retriever_embeds_query_and_passes_filters_and_limits() -> None:
    first, second = chunk("a", "alpha"), chunk("b", "beta")
    dense = FakeDenseStore([VectorSearchResult(first, 0.8)])
    lexical = FakeLexicalIndex([BM25SearchResult(second, 2.0)])
    embedder = FakeEmbedder()
    retriever = HybridRetriever(dense, lexical, embedder)

    results = retriever.search(
        "local question",
        top_k=2,
        candidate_k=5,
        where={"source": "notes.md"},
    )

    assert embedder.queries == ["local question"]
    assert dense.calls == [{"embedding": [0.3, 0.7], "top_k": 5, "where": {"source": "notes.md"}}]
    assert lexical.calls == [
        {"query": "local question", "top_k": 5, "where": {"source": "notes.md"}}
    ]
    assert {result.chunk.chunk_id for result in results} == {"a", "b"}


def test_hybrid_retriever_supports_real_bm25_and_empty_dense_store() -> None:
    indexed_chunk = chunk("lexical", "Retrieval uses local lexical search.")
    retriever = HybridRetriever(InMemoryVectorStore(), BM25Index([indexed_chunk]), FakeEmbedder())

    results = retriever.search("lexical search")

    assert [result.chunk.chunk_id for result in results] == ["lexical"]
    assert results[0].dense_rank is None
    assert results[0].bm25_rank == 1


def test_search_rejects_invalid_limits_and_empty_query() -> None:
    retriever = HybridRetriever(FakeDenseStore([]), FakeLexicalIndex([]), FakeEmbedder())

    with pytest.raises(ValueError, match="empty"):
        retriever.search("  ")
    with pytest.raises(ValueError, match="candidate_k"):
        retriever.search("query", top_k=4, candidate_k=3)
    with pytest.raises(ValueError, match="top_k"):
        fuse_ranked_results([], [], top_k=0)


def test_weights_and_rrf_parameter_must_be_positive() -> None:
    with pytest.raises(ValueError, match="rrf_k"):
        HybridRetriever(FakeDenseStore([]), FakeLexicalIndex([]), FakeEmbedder(), rrf_k=0)
    with pytest.raises(ValueError, match="dense_weight"):
        HybridRetriever(FakeDenseStore([]), FakeLexicalIndex([]), FakeEmbedder(), dense_weight=0)
    with pytest.raises(ValueError, match="bm25_weight"):
        fuse_ranked_results([], [], bm25_weight=float("inf"))
