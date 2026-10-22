"""Optional, lazy cross-encoder reranking for hybrid retrieval candidates."""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from ara.rag.chunking import DocumentChunk
from ara.rag.retriever import HybridSearchResult

logger = logging.getLogger(__name__)
DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"


class RerankerError(RuntimeError):
    """Raised when a reranker cannot load or score candidates."""


class CrossEncoderModel(Protocol):
    """Small part of the CrossEncoder API used by this adapter."""

    def predict(
        self,
        sentences: Sequence[tuple[str, str]],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> Sequence[float]:
        """Return one relevance score per text pair."""


@dataclass(frozen=True)
class RerankedResult:
    """A hybrid candidate with its cross-encoder score and original rank."""

    chunk: DocumentChunk
    score: float
    retrieval_score: float
    retrieval_rank: int
    dense_rank: int | None
    bm25_rank: int | None


class CrossEncoderReranker:
    """Rerank a bounded candidate list with an optional local CrossEncoder model.

    The optional package and model weights are loaded only on the first non-empty
    call to :meth:`rerank`. Tests and alternate runtimes can inject a compatible
    `model` instance without importing Sentence Transformers.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_RERANKER_MODEL,
        *,
        device: str | None = None,
        batch_size: int = 16,
        model: CrossEncoderModel | None = None,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name must not be empty")
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self._model = model

    def rerank(
        self,
        query: str,
        candidates: Sequence[HybridSearchResult],
        *,
        top_k: int | None = None,
    ) -> list[RerankedResult]:
        """Score query/chunk pairs, then sort by score and deterministic tie breaks."""
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k is not None and top_k < 1:
            raise ValueError("top_k must be at least 1")
        if len({candidate.chunk.chunk_id for candidate in candidates}) != len(candidates):
            raise ValueError("candidate chunk IDs must be unique")
        if not candidates:
            return []

        pairs = [(query, candidate.chunk.text) for candidate in candidates]
        try:
            raw_scores = self._get_model().predict(
                pairs,
                batch_size=self.batch_size,
                show_progress_bar=False,
            )
        except Exception as exc:
            if isinstance(exc, RerankerError):
                raise
            raise RerankerError(f"Cross-encoder scoring failed: {exc}") from exc
        scores = _validate_scores(raw_scores, expected_count=len(candidates))

        ranked = [
            RerankedResult(
                chunk=candidate.chunk,
                score=score,
                retrieval_score=candidate.score,
                retrieval_rank=rank,
                dense_rank=candidate.dense_rank,
                bm25_rank=candidate.bm25_rank,
            )
            for rank, (candidate, score) in enumerate(zip(candidates, scores, strict=True), start=1)
        ]
        ranked.sort(
            key=lambda result: (
                -result.score,
                -result.retrieval_score,
                result.chunk.chunk_id,
            )
        )
        logger.debug("Reranked %d candidates with %s", len(ranked), self.model_name)
        return ranked[:top_k] if top_k is not None else ranked

    def _get_model(self) -> CrossEncoderModel:
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RerankerError(
                    "Cross-encoder reranking requires the optional 'rerank' extra; "
                    "install it with `uv sync --extra rerank`."
                ) from exc
            try:
                self._model = CrossEncoder(self.model_name, device=self.device)
            except Exception as exc:
                raise RerankerError(
                    f"Could not load cross-encoder model {self.model_name!r}: {exc}"
                ) from exc
        return self._model


def _validate_scores(raw_scores: Sequence[float], *, expected_count: int) -> list[float]:
    """Convert model outputs to finite Python floats and verify one per candidate."""
    try:
        values = list(raw_scores)
        scores = [float(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise RerankerError(
            "Cross-encoder scores must be a one-dimensional numeric sequence."
        ) from exc
    if len(scores) != expected_count:
        raise RerankerError(
            f"Cross-encoder returned {len(scores)} scores for {expected_count} candidates."
        )
    if not all(math.isfinite(score) for score in scores):
        raise RerankerError("Cross-encoder scores must be finite.")
    return scores
