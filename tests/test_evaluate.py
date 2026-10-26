"""Tests for ranking metrics, RRF candidates, and offline evaluator wiring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pytest

torch = pytest.importorskip("torch")


def test_rrf_is_deterministic_and_combines_overlapping_lists() -> None:
    from ara.dl.evaluate import reciprocal_rank_fusion

    ranking = reciprocal_rank_fusion(["b", "a", "c"], ["a", "b", "d"])

    assert ranking == ["a", "b", "c", "d"]


def test_ranking_metrics_compute_recall_mrr_and_ndcg() -> None:
    from ara.dl.evaluate import TestQuery, evaluate_rankings

    queries = [
        TestQuery("q1", "query one", frozenset({"a", "b"})),
        TestQuery("q2", "query two", frozenset({"z"})),
    ]
    metrics = evaluate_rankings(
        queries,
        {"q1": ["x", "a", "b"], "q2": ["z"]},
        system_name="fixture",
        cutoff=2,
    )

    assert metrics.recall_at_10 == pytest.approx(0.75)
    assert metrics.mrr == pytest.approx(0.75)
    ideal_discount = 1 / 1.5849625
    query_one_ndcg = ideal_discount / (1 + ideal_discount)
    assert metrics.ndcg_at_10 == pytest.approx((query_one_ndcg + 1) / 2)
    assert metrics.query_count == 2


class TinyTokenizer:
    def __call__(
        self,
        queries: list[str],
        passages: list[str],
        *,
        padding: bool,
        truncation: bool,
        max_length: int,
        return_tensors: Literal["pt"],
    ) -> dict[str, torch.Tensor]:
        assert padding and truncation and max_length >= 16 and return_tensors == "pt"
        ids = [[1 if "Gold" in passage else 0, 0] for passage in passages]
        return {
            "input_ids": torch.tensor(ids),
            "attention_mask": torch.ones((len(ids), 2), dtype=torch.long),
        }


class TinyDenseEncoder:
    def encode(self, texts: list[str]) -> torch.Tensor:
        embeddings = []
        for text in texts:
            if "heart question" in text or "Gold" in text:
                embeddings.append([1.0, 0.0])
            else:
                embeddings.append([0.0, 1.0])
        return torch.tensor(embeddings)


def _scorer(scale: float) -> torch.nn.Module:
    from ara.dl.model import CrossEncoderOutput

    class Scorer(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.scale = torch.nn.Parameter(torch.tensor(scale))

        def forward(
            self,
            *,
            input_ids: torch.Tensor,
            attention_mask: torch.Tensor,
        ) -> CrossEncoderOutput:
            logits = input_ids[:, 0].float() * self.scale
            return CrossEncoderOutput(relevance_logits=logits)

    return Scorer()


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_evaluator_scores_only_test_records_and_writes_artifacts(tmp_path: Path) -> None:
    from ara.config import Settings
    from ara.dl.evaluate import evaluate_models

    _write_jsonl(
        tmp_path / "corpus_test.jsonl",
        [
            {"document_id": "d1", "title": "Other", "text": "Beetles follow seasonal daylight."},
            {
                "document_id": "d2",
                "title": "Gold evidence",
                "text": "Gold evidence: cardiac health outcomes changed.",
            },
        ],
    )
    _write_jsonl(
        tmp_path / "queries_test.jsonl",
        [
            {
                "query_id": "test:q1",
                "query": "heart question cardiac health",
                "split": "test",
                "positives": [
                    {
                        "document_id": "d2",
                        "relevance": 1,
                        "verdict": "SUPPORT",
                        "evidence_sentences": [0],
                    }
                ],
            }
        ],
    )
    settings = Settings(
        _env_file=None,
        dl_public_data_dir=tmp_path,
        dl_use_synthetic_pairs=False,
        dl_eval_candidate_k=2,
        dl_eval_batch_size=2,
        dl_max_length=32,
        dl_dense_embeddings_cache_path=tmp_path / "cache.pt",
        dl_eval_metrics_path=tmp_path / "evaluation.json",
        dl_error_analysis_path=tmp_path / "errors.json",
    )

    result = evaluate_models(
        settings,
        generic_model=_scorer(-1.0),
        trained_model=_scorer(1.0),
        tokenizer=TinyTokenizer(),
        dense_encoder=TinyDenseEncoder(),
        include_random_negative_ablation=False,
    )

    metrics = {row.system: row for row in result.metrics}
    assert metrics["Generic MS MARCO cross-encoder"].mrr == 0.5
    assert metrics["Fine-tuned cross-encoder"].mrr == 1.0
    assert metrics["BM25+dense RRF (no reranker)"].mrr == 1.0
    assert result.candidate_recall_at_20 == 1.0
    assert result.error_case_count == 0
    assert result.metrics_path.is_file()
    assert result.table_path.is_file()
    assert result.error_analysis_path.is_file()
    assert (tmp_path / "cache.pt").is_file()
