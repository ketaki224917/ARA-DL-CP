"""Hybrid dense and lexical retrieval with reciprocal-rank fusion."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from ara.rag.bm25 import BM25Index, BM25SearchResult
from ara.rag.chunking import DocumentChunk
from ara.rag.vectorstore import VectorSearchResult, VectorStore

DEFAULT_RRF_K = 60


class QueryEmbedder(Protocol):
    """Interface needed to embed one retrieval query."""

    def embed_query(self, text: str) -> Sequence[float]:
        """Return the dense vector for a query string."""


@dataclass(frozen=True)
class HybridSearchResult:
    """A chunk ranked by RRF, with each retriever's rank and score retained."""

    chunk: DocumentChunk
    score: float
    dense_rank: int | None
    bm25_rank: int | None
    dense_score: float | None
    bm25_score: float | None


class HybridRetriever:
    """Fuse dense and BM25 results while preserving chunk IDs and source ranks."""

    def __init__(
        self,
        dense_store: VectorStore,
        lexical_index: BM25Index,
        embedder: QueryEmbedder,
        *,
        rrf_k: int = DEFAULT_RRF_K,
        dense_weight: float = 1.0,
        bm25_weight: float = 1.0,
    ) -> None:
        if rrf_k < 1:
            raise ValueError("rrf_k must be at least 1")
        if not math.isfinite(dense_weight) or dense_weight <= 0:
            raise ValueError("dense_weight must be finite and positive")
        if not math.isfinite(bm25_weight) or bm25_weight <= 0:
            raise ValueError("bm25_weight must be finite and positive")
        self.dense_store = dense_store
        self.lexical_index = lexical_index
        self.embedder = embedder
        self.rrf_k = rrf_k
        self.dense_weight = float(dense_weight)
        self.bm25_weight = float(bm25_weight)

    def search(
        self,
        query: str,
        *,
        top_k: int = 8,
        candidate_k: int = 32,
        where: Mapping[str, Any] | None = None,
    ) -> list[HybridSearchResult]:
        """Retrieve candidates from both indexes and fuse their one-based ranks."""
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        if candidate_k < top_k:
            raise ValueError("candidate_k must be greater than or equal to top_k")

        query_embedding = self.embedder.embed_query(query)
        dense_results = self.dense_store.search(
            query_embedding,
            top_k=candidate_k,
            where=where,
        )
        lexical_results = self.lexical_index.search(
            query,
            top_k=candidate_k,
            where=where,
        )
        return fuse_ranked_results(
            dense_results,
            lexical_results,
            top_k=top_k,
            rrf_k=self.rrf_k,
            dense_weight=self.dense_weight,
            bm25_weight=self.bm25_weight,
        )


def fuse_ranked_results(
    dense_results: Sequence[VectorSearchResult],
    lexical_results: Sequence[BM25SearchResult],
    *,
    top_k: int = 8,
    rrf_k: int = DEFAULT_RRF_K,
    dense_weight: float = 1.0,
    bm25_weight: float = 1.0,
) -> list[HybridSearchResult]:
    """Fuse ordered result lists using weighted reciprocal-rank fusion.

    A chunk appearing in both lists is counted once, with a contribution from each
    one-based rank. The chunk object from the dense result is preferred when both
    indexes return the same stable ID.
    """
    _validate_fusion_settings(top_k, rrf_k, dense_weight, bm25_weight)
    fused: dict[str, dict[str, Any]] = {}
    for rank, dense_result in enumerate(dense_results, start=1):
        record = fused.setdefault(
            dense_result.chunk.chunk_id,
            {
                "chunk": dense_result.chunk,
                "score": 0.0,
                "dense_rank": None,
                "bm25_rank": None,
                "dense_score": None,
                "bm25_score": None,
            },
        )
        record["chunk"] = dense_result.chunk
        record["score"] += dense_weight / (rrf_k + rank)
        record["dense_rank"] = rank
        record["dense_score"] = dense_result.score

    for rank, lexical_result in enumerate(lexical_results, start=1):
        record = fused.setdefault(
            lexical_result.chunk.chunk_id,
            {
                "chunk": lexical_result.chunk,
                "score": 0.0,
                "dense_rank": None,
                "bm25_rank": None,
                "dense_score": None,
                "bm25_score": None,
            },
        )
        record["score"] += bm25_weight / (rrf_k + rank)
        record["bm25_rank"] = rank
        record["bm25_score"] = lexical_result.score

    results = [HybridSearchResult(**record) for record in fused.values()]
    results.sort(key=lambda result: (-result.score, result.chunk.chunk_id))
    return results[:top_k]


def _validate_fusion_settings(
    top_k: int,
    rrf_k: int,
    dense_weight: float,
    bm25_weight: float,
) -> None:
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    if rrf_k < 1:
        raise ValueError("rrf_k must be at least 1")
    if not math.isfinite(dense_weight) or dense_weight <= 0:
        raise ValueError("dense_weight must be finite and positive")
    if not math.isfinite(bm25_weight) or bm25_weight <= 0:
        raise ValueError("bm25_weight must be finite and positive")
