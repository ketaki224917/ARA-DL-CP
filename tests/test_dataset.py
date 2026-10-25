"""Tests for split-safe reranker pair construction and batching."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pytest
import torch

from ara.dl.dataset import (
    PairBatch,
    PairCollator,
    PairExample,
    build_pair_examples,
    make_pair_dataloader,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _make_split(root: Path, split: str = "train") -> None:
    _write_jsonl(
        root / f"corpus_{split}.jsonl",
        [
            {
                "document_id": "positive",
                "title": "Cardiac risk",
                "text": "Elevated blood pressure increases risk of cardiac disease in adults.",
            },
            {
                "document_id": "negative-a",
                "title": "Cardiac pressure effects",
                "text": (
                    "Cardiac pressure effects were examined among kidney patients after treatment."
                ),
            },
            {
                "document_id": "negative-b",
                "title": "Cellular biology",
                "text": "Mitochondria produce cellular energy through aerobic respiration.",
            },
        ],
    )
    _write_jsonl(
        root / f"queries_{split}.jsonl",
        [
            {
                "query_id": f"scifact:{split}-1",
                "query": "Does high blood pressure increase cardiac risk?",
                "split": split,
                "positives": [{"document_id": "positive", "relevance": 1}],
            }
        ],
    )


class FakePairTokenizer:
    """Small tokenizer stand-in that keeps the collator independent of model downloads."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], list[str], int]] = []

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
        assert padding and truncation and return_tensors == "pt"
        self.calls.append((queries, passages, max_length))
        return {
            "input_ids": torch.tensor([[1, 2, 3] for _ in queries]),
            "attention_mask": torch.ones((len(queries), 3), dtype=torch.long),
        }


def test_builds_positive_and_deterministic_in_split_negatives(tmp_path: Path) -> None:
    _make_split(tmp_path)

    first = build_pair_examples(tmp_path, "train", seed=19, candidate_k=3)
    second = build_pair_examples(tmp_path, "train", seed=19, candidate_k=3)

    assert first == second
    assert first.query_count == 1
    assert first.positive_pair_count == 1
    assert first.mined_negative_count == 1
    assert first.queries_without_negatives == 0
    assert {item.relevance_label for item in first.examples} == {0.0, 1.0}
    assert all(item.split == "train" for item in first.examples)
    assert all(
        item.document_id != "positive" for item in first.examples if not item.relevance_label
    )


def test_rejects_positive_document_outside_split(tmp_path: Path) -> None:
    _make_split(tmp_path)
    query_file = tmp_path / "queries_train.jsonl"
    _write_jsonl(
        query_file,
        [
            {
                "query_id": "scifact:outside",
                "query": "Does high blood pressure increase cardiac risk?",
                "split": "train",
                "positives": [{"document_id": "validation-only", "relevance": 1}],
            }
        ],
    )

    with pytest.raises(ValueError, match="outside split"):
        build_pair_examples(tmp_path, "train")


def test_synthetic_pairs_are_training_only(tmp_path: Path) -> None:
    _make_split(tmp_path)
    synthetic = tmp_path / "synthetic.jsonl"
    synthetic.write_text(
        json.dumps(
            {
                "query": "What increases cardiac risk?",
                "positive_chunk_id": "chunk:positive",
                "positive_text": "Blood pressure is associated with cardiac risk.",
                "positive_source": "report-a",
                "negative_chunk_id": "chunk:negative",
                "negative_text": "Beetles respond to daylight changes.",
                "negative_source": "report-b",
                "negative_mining_method": "bm25",
                "negative_search_rank": 1,
                "query_origin": "extractive",
                "seed": 19,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="only be added to the train split"):
        build_pair_examples(
            tmp_path,
            "validation",
            include_synthetic_train=True,
            synthetic_path=synthetic,
        )

    result = build_pair_examples(
        tmp_path,
        "train",
        include_synthetic_train=True,
        synthetic_path=synthetic,
    )
    synthetic_examples = [item for item in result.examples if item.source == "sample_corpus"]
    assert result.synthetic_pair_count == 1
    assert len(synthetic_examples) == 2
    assert {item.split for item in synthetic_examples} == {"train"}


def test_collator_and_dataloader_preserve_masks_and_labels() -> None:
    tokenizer = FakePairTokenizer()
    examples = [
        PairExample("q1", "query one", "d1", "passage one", 1.0, "train", "scifact"),
        PairExample(
            "q2", "query two", "d2", "passage two", 0.0, "train", "scifact", 0.0
        ),
    ]
    collator = PairCollator(tokenizer, max_length=64)
    batch = collator(examples)

    assert isinstance(batch, PairBatch)
    assert batch.relevance_labels.tolist() == [1.0, 0.0]
    assert batch.credibility_labels.tolist() == [0.0, 0.0]
    assert batch.credibility_mask.tolist() == [False, True]
    assert batch.query_ids == ["q1", "q2"]
    assert batch.document_ids == ["d1", "d2"]
    assert tokenizer.calls[0][2] == 64

    loader = make_pair_dataloader(
        examples, tokenizer, batch_size=2, max_length=64, shuffle=True, seed=9
    )
    loaded_batch = next(iter(loader))
    assert loaded_batch.relevance_labels.shape == (2,)
    assert loaded_batch.model_inputs["input_ids"].shape == (2, 3)
