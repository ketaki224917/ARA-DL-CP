"""Tests for the lazy cross-encoder reranker adapter."""

from collections.abc import Sequence

import pytest

from ara.rag.chunking import DocumentChunk
from ara.rag.reranker import CrossEncoderReranker, RerankerError
from ara.rag.retriever import HybridSearchResult


def candidate(chunk_id: str, text: str, retrieval_score: float) -> HybridSearchResult:
    return HybridSearchResult(
        chunk=DocumentChunk(
            chunk_id=chunk_id,
            text=text,
            source="notes.md",
            page=None,
            char_start=0,
            char_end=len(text),
        ),
        score=retrieval_score,
        dense_rank=1,
        bm25_rank=None,
        dense_score=0.8,
        bm25_score=None,
    )


class FakeCrossEncoder:
    def __init__(self, scores: Sequence[float]) -> None:
        self.scores = scores
        self.pairs: list[tuple[str, str]] = []
        self.batch_size: int | None = None
        self.show_progress_bar: bool | None = None

    def predict(
        self,
        sentences: Sequence[tuple[str, str]],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> Sequence[float]:
        self.pairs = list(sentences)
        self.batch_size = batch_size
        self.show_progress_bar = show_progress_bar
        return self.scores


def test_rerank_sorts_scores_and_preserves_retrieval_provenance() -> None:
    model = FakeCrossEncoder([0.2, 0.9])
    reranker = CrossEncoderReranker(model=model, batch_size=4)

    results = reranker.rerank(
        "query",
        [candidate("a", "first", 0.9), candidate("b", "second", 0.7)],
    )

    assert [result.chunk.chunk_id for result in results] == ["b", "a"]
    assert results[0].score == pytest.approx(0.9)
    assert results[0].retrieval_score == pytest.approx(0.7)
    assert results[0].retrieval_rank == 2
    assert results[0].dense_rank == 1
    assert model.pairs == [("query", "first"), ("query", "second")]
    assert model.batch_size == 4
    assert model.show_progress_bar is False


def test_rerank_ties_use_retrieval_score_then_chunk_id() -> None:
    reranker = CrossEncoderReranker(model=FakeCrossEncoder([0.5, 0.5, 0.5]))

    results = reranker.rerank(
        "query",
        [candidate("z", "z", 0.8), candidate("a", "a", 0.8), candidate("b", "b", 0.9)],
        top_k=2,
    )

    assert [result.chunk.chunk_id for result in results] == ["b", "a"]


def test_empty_candidates_do_not_load_optional_model() -> None:
    reranker = CrossEncoderReranker()

    assert reranker.rerank("query", []) == []
    assert reranker._model is None


@pytest.mark.parametrize("scores", [[0.1], [float("nan"), 0.3]])
def test_malformed_model_scores_are_rejected(scores: list[float]) -> None:
    reranker = CrossEncoderReranker(model=FakeCrossEncoder(scores))

    with pytest.raises(RerankerError):
        reranker.rerank("query", [candidate("a", "one", 0.2), candidate("b", "two", 0.1)])


def test_invalid_query_limit_and_duplicate_ids_are_rejected() -> None:
    reranker = CrossEncoderReranker(model=FakeCrossEncoder([]))

    with pytest.raises(ValueError, match="empty"):
        reranker.rerank(" ", [])
    with pytest.raises(ValueError, match="top_k"):
        reranker.rerank("query", [], top_k=0)
    with pytest.raises(ValueError, match="unique"):
        reranker.rerank("query", [candidate("a", "one", 0.2), candidate("a", "two", 0.1)])
    with pytest.raises(ValueError, match="batch_size"):
        CrossEncoderReranker(batch_size=0)
