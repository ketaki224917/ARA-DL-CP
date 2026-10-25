"""Build split-safe query/passage pairs and CPU-compatible PyTorch data loaders."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

import torch
from torch.utils.data import DataLoader, Dataset

from ara.config import load_settings
from ara.dl.data_gen import SyntheticTrainingPair
from ara.rag.bm25 import BM25Index
from ara.rag.chunking import DocumentChunk

logger = logging.getLogger(__name__)
_TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)


class PairTokenizer(Protocol):
    """Tokenizer interface for query/passage cross-encoder batches."""

    def __call__(
        self,
        queries: Sequence[str],
        passages: Sequence[str],
        *,
        padding: bool,
        truncation: bool,
        max_length: int,
        return_tensors: Literal["pt"],
    ) -> Mapping[str, torch.Tensor]:
        """Tokenize paired text into model input tensors."""


@dataclass(frozen=True)
class PairExample:
    """One labeled query and candidate passage with split/source provenance."""

    query_id: str
    query: str
    document_id: str
    passage: str
    relevance_label: float
    split: Literal["train", "validation", "test"]
    source: Literal["scifact", "sample_corpus"]
    credibility_label: float | None = None


@dataclass(frozen=True)
class PairBuildResult:
    """Generated examples and counters for positive and mined-negative construction."""

    examples: tuple[PairExample, ...]
    query_count: int
    positive_pair_count: int
    mined_negative_count: int
    synthetic_pair_count: int
    queries_without_negatives: int


@dataclass(frozen=True)
class PairBatch:
    """Tokenized batch and labels returned by `PairCollator`."""

    model_inputs: dict[str, torch.Tensor]
    relevance_labels: torch.Tensor
    credibility_labels: torch.Tensor
    credibility_mask: torch.Tensor
    query_ids: list[str]
    document_ids: list[str]


class PairDataset(Dataset[PairExample]):
    """Indexable PyTorch dataset of validated in-memory query/passage pairs."""

    def __init__(self, examples: Sequence[PairExample]) -> None:
        self.examples = tuple(examples)

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, index: int) -> PairExample:
        return self.examples[index]


class PairCollator:
    """Tokenize paired text and preserve masked optional credibility labels."""

    def __init__(self, tokenizer: PairTokenizer, *, max_length: int) -> None:
        if max_length < 16:
            raise ValueError("max_length must be at least 16")
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __call__(self, examples: Sequence[PairExample]) -> PairBatch:
        if not examples:
            raise ValueError("cannot collate an empty batch")
        encoded = self.tokenizer(
            [example.query for example in examples],
            [example.passage for example in examples],
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        credibility_mask = [example.credibility_label is not None for example in examples]
        return PairBatch(
            model_inputs=dict(encoded),
            relevance_labels=torch.tensor(
                [example.relevance_label for example in examples], dtype=torch.float32
            ),
            credibility_labels=torch.tensor(
                [example.credibility_label or 0.0 for example in examples],
                dtype=torch.float32,
            ),
            credibility_mask=torch.tensor(credibility_mask, dtype=torch.bool),
            query_ids=[example.query_id for example in examples],
            document_ids=[example.document_id for example in examples],
        )


def build_pair_examples(
    data_dir: Path | str,
    split: Literal["train", "validation", "test"],
    *,
    max_negatives_per_query: int = 1,
    candidate_k: int = 32,
    negative_pool_size: int = 1,
    seed: int = 42,
    include_synthetic_train: bool = False,
    synthetic_path: Path | str | None = None,
) -> PairBuildResult:
    """Build public positive pairs and deterministic in-split BM25 negatives.

    Unjudged SciFact abstracts are used as mined training candidates, not treated as
    benchmark relevance judgments. Their negative labels are therefore explicitly
    identified as mined examples in the returned source field/counters.
    """
    if max_negatives_per_query < 0:
        raise ValueError("max_negatives_per_query cannot be negative")
    if candidate_k < 1 or negative_pool_size < 1:
        raise ValueError("candidate_k and negative_pool_size must be positive")
    if include_synthetic_train and split != "train":
        raise ValueError("P5.1 sample-corpus pairs may only be added to the train split")

    root = Path(data_dir)
    documents = _load_jsonl(root / f"corpus_{split}.jsonl")
    queries = _load_jsonl(root / f"queries_{split}.jsonl")
    corpus: dict[str, str] = {}
    chunks: list[DocumentChunk] = []
    for raw in documents:
        document_id = _required_text(raw, "document_id")
        text = _required_text(raw, "text")
        if document_id in corpus:
            raise ValueError(f"Duplicate document ID {document_id!r} in split {split!r}.")
        corpus[document_id] = text
        chunks.append(
            DocumentChunk(
                chunk_id=f"scifact:{document_id}",
                text=text,
                source=f"scifact:{document_id}",
                page=None,
                char_start=0,
                char_end=len(text),
            )
        )
    if not chunks:
        raise ValueError(f"SciFact split {split!r} has no corpus documents.")
    lexical_index = BM25Index(chunks)
    examples: list[PairExample] = []
    positive_count = 0
    negative_count = 0
    no_negative_count = 0

    for raw in queries:
        query_id = _required_text(raw, "query_id")
        query = _required_text(raw, "query")
        if raw.get("split") != split:
            raise ValueError(f"Query {query_id!r} is stored in the wrong split file.")
        positives = raw.get("positives")
        if not isinstance(positives, list) or not positives:
            raise ValueError(f"Query {query_id!r} has no annotated positive documents.")
        positive_ids: set[str] = set()
        positive_texts: list[str] = []
        for positive in positives:
            if not isinstance(positive, dict):
                raise ValueError(f"Query {query_id!r} has a malformed positive record.")
            document_id = _required_text(positive, "document_id")
            document = corpus.get(document_id)
            if document is None:
                raise ValueError(
                    f"Query {query_id!r} positive document {document_id!r} is outside split."
                )
            positive_ids.add(document_id)
            positive_texts.append(document)
            examples.append(
                PairExample(
                    query_id=query_id,
                    query=query,
                    document_id=document_id,
                    passage=document,
                    relevance_label=1.0,
                    split=split,
                    source="scifact",
                )
            )
            positive_count += 1

        if max_negatives_per_query == 0:
            continue
        eligible = [
            result
            for result in lexical_index.search(query, top_k=candidate_k)
            if result.chunk.chunk_id.removeprefix("scifact:") not in positive_ids
            and all(
                _jaccard(result.chunk.text, positive_text) < 0.8
                for positive_text in positive_texts
            )
        ]
        if not eligible:
            no_negative_count += 1
            continue
        rng = random.Random(_stable_seed(seed, query_id))
        pool = eligible[:negative_pool_size]
        for negative in _sample_without_replacement(rng, pool, max_negatives_per_query):
            document_id = negative.chunk.chunk_id.removeprefix("scifact:")
            examples.append(
                PairExample(
                    query_id=query_id,
                    query=query,
                    document_id=document_id,
                    passage=negative.chunk.text,
                    relevance_label=0.0,
                    split=split,
                    source="scifact",
                )
            )
            negative_count += 1

    synthetic_count = 0
    if include_synthetic_train:
        configured_path = (
            Path(synthetic_path) if synthetic_path is not None else load_settings().dl_data_path
        )
        synthetic_examples = _load_synthetic_pairs(configured_path)
        examples.extend(synthetic_examples)
        synthetic_count = len(synthetic_examples) // 2

    return PairBuildResult(
        examples=tuple(examples),
        query_count=len(queries),
        positive_pair_count=positive_count,
        mined_negative_count=negative_count,
        synthetic_pair_count=synthetic_count,
        queries_without_negatives=no_negative_count,
    )


def make_pair_dataloader(
    examples: Sequence[PairExample],
    tokenizer: PairTokenizer,
    *,
    batch_size: int,
    max_length: int,
    shuffle: bool,
    seed: int = 42,
) -> DataLoader[PairBatch]:
    """Create a reproducible zero-worker DataLoader suitable for Windows CPU runs."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        PairDataset(examples),
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0,
        generator=generator,
        collate_fn=PairCollator(tokenizer, max_length=max_length),
    )


def _load_synthetic_pairs(path: Path) -> list[PairExample]:
    if not path.is_file():
        raise FileNotFoundError(f"P5.1 synthetic pair file does not exist: {path}")
    examples: list[PairExample] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            pair = SyntheticTrainingPair.model_validate_json(line)
        except ValueError as exc:
            raise ValueError(f"Invalid synthetic pair at {path}:{line_number}: {exc}") from exc
        query_id = f"synthetic:{hashlib.sha256(pair.query.encode()).hexdigest()[:16]}"
        examples.extend(
            [
                PairExample(
                    query_id=query_id,
                    query=pair.query,
                    document_id=pair.positive_chunk_id,
                    passage=pair.positive_text,
                    relevance_label=1.0,
                    split="train",
                    source="sample_corpus",
                ),
                PairExample(
                    query_id=query_id,
                    query=pair.query,
                    document_id=pair.negative_chunk_id,
                    passage=pair.negative_text,
                    relevance_label=0.0,
                    split="train",
                    source="sample_corpus",
                ),
            ]
        )
    if not examples:
        raise ValueError(f"P5.1 synthetic pair file is empty: {path}")
    logger.info("Added %d P5.1 sample-corpus query/passage pairs to training", len(examples))
    return examples


def _sample_without_replacement(
    rng: random.Random,
    values: Sequence[Any],
    count: int,
) -> list[Any]:
    return rng.sample(values, k=min(count, len(values)))


def _stable_seed(seed: int, query_id: str) -> int:
    digest = hashlib.sha256(f"{seed}:{query_id}".encode()).hexdigest()
    return int(digest[:16], 16)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Dataset split file does not exist: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"Expected a JSON object at {path}:{line_number}.")
        records.append(value)
    return records


def _required_text(
    value: Mapping[str, Any],
    key: str,
    *,
    allow_empty: bool = False,
) -> str:
    result = value.get(key)
    if not isinstance(result, str) or (not allow_empty and not result.strip()):
        raise ValueError(f"Dataset field {key!r} must be a non-empty string.")
    return result


def _jaccard(left: str, right: str) -> float:
    left_tokens = {token.casefold() for token in _TOKEN_PATTERN.findall(left) if len(token) > 1}
    right_tokens = {token.casefold() for token in _TOKEN_PATTERN.findall(right) if len(token) > 1}
    union = left_tokens | right_tokens
    return len(left_tokens & right_tokens) / len(union) if union else 1.0
