"""Persisted BM25 lexical retrieval over stable document chunks."""

from __future__ import annotations

import json
import logging
import math
import os
import re
import tempfile
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ara.rag.chunking import DocumentChunk

logger = logging.getLogger(__name__)
_TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)
_FORMAT_VERSION = 1


class BM25IndexError(RuntimeError):
    """Raised when a persisted BM25 index cannot be read or written."""


@dataclass(frozen=True)
class BM25SearchResult:
    """A retrieved chunk and its BM25 relevance score."""

    chunk: DocumentChunk
    score: float


class BM25Index:
    """In-memory BM25 index with explicit, portable JSON persistence."""

    def __init__(
        self,
        chunks: Sequence[DocumentChunk] = (),
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if not math.isfinite(k1) or k1 <= 0:
            raise ValueError("k1 must be a finite positive number")
        if not math.isfinite(b) or not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1")
        if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
            raise ValueError("chunk IDs must be unique")

        self.k1 = float(k1)
        self.b = float(b)
        self._chunks = list(chunks)
        self._tokens = [_tokenize(chunk.text) for chunk in chunks]
        self._frequencies = [Counter(tokens) for tokens in self._tokens]
        self._postings: dict[str, dict[int, int]] = defaultdict(dict)
        for doc_index, frequencies in enumerate(self._frequencies):
            for token, frequency in frequencies.items():
                self._postings[token][doc_index] = frequency
        self._average_length = (
            sum(map(len, self._tokens)) / len(self._tokens) if self._tokens else 0.0
        )

    def __len__(self) -> int:
        """Return the number of indexed chunks."""
        return len(self._chunks)

    @property
    def chunk_ids(self) -> tuple[str, ...]:
        """Return the indexed chunk IDs in index order."""
        return tuple(chunk.chunk_id for chunk in self._chunks)

    def search(
        self,
        query: str,
        *,
        top_k: int = 8,
        where: Mapping[str, Any] | None = None,
    ) -> list[BM25SearchResult]:
        """Return BM25-ranked chunks that contain at least one query term."""
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        query_tokens = _tokenize(query)
        if not query_tokens or not self._chunks:
            return []

        scores: dict[int, float] = defaultdict(float)
        document_count = len(self._chunks)
        for token in query_tokens:
            posting = self._postings.get(token)
            if not posting:
                continue
            document_frequency = len(posting)
            inverse_frequency = math.log(
                1.0 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            for doc_index, frequency in posting.items():
                document_length = len(self._tokens[doc_index])
                length_ratio = (
                    document_length / self._average_length if self._average_length else 0.0
                )
                denominator = frequency + self.k1 * (1.0 - self.b + self.b * length_ratio)
                scores[doc_index] += (
                    inverse_frequency * frequency * (self.k1 + 1.0) / denominator
                )

        matches = [
            BM25SearchResult(chunk=self._chunks[index], score=score)
            for index, score in scores.items()
            if score > 0 and (not where or _metadata_matches(self._chunks[index], where))
        ]
        matches.sort(key=lambda result: (-result.score, result.chunk.chunk_id))
        return matches[:top_k]

    def save(self, path: Path | str) -> None:
        """Write chunks and ranking parameters through an atomic same-directory rename."""
        destination = Path(path)
        temporary_path: Path | None = None
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=destination.parent,
                prefix=f"{destination.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary_path = Path(stream.name)
                json.dump(
                    {
                        "format_version": _FORMAT_VERSION,
                        "k1": self.k1,
                        "b": self.b,
                        "chunks": [_chunk_record(chunk) for chunk in self._chunks],
                    },
                    stream,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            temporary_path.replace(destination)
        except (OSError, TypeError, ValueError) as exc:
            raise BM25IndexError(f"Could not save BM25 index to {destination}: {exc}") from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        logger.info("Saved BM25 index with %d chunks to %s", len(self), destination)

    @classmethod
    def load(cls, path: Path | str) -> BM25Index:
        """Load and validate an index file, rebuilding its token statistics."""
        source = Path(path)
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("format_version") != _FORMAT_VERSION:
                raise ValueError("unsupported or malformed format version")
            raw_chunks = payload.get("chunks")
            if not isinstance(raw_chunks, list):
                raise ValueError("chunks must be a list")
            chunks = [_chunk_from_record(record) for record in raw_chunks]
            index = cls(chunks, k1=payload["k1"], b=payload["b"])
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise BM25IndexError(f"Could not load BM25 index from {source}: {exc}") from exc
        logger.info("Loaded BM25 index with %d chunks from %s", len(index), source)
        return index


def _tokenize(text: str) -> list[str]:
    """Split text into normalized Unicode word tokens."""
    return [token.casefold() for token in _TOKEN_PATTERN.findall(text)]


def _metadata_matches(chunk: DocumentChunk, conditions: Mapping[str, Any]) -> bool:
    """Apply exact-match filters to chunk provenance fields."""
    metadata: dict[str, str | int] = {
        "source": chunk.source,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
    }
    if chunk.page is not None:
        metadata["page"] = chunk.page
    return all(metadata.get(key) == value for key, value in conditions.items())


def _chunk_record(chunk: DocumentChunk) -> dict[str, str | int | None]:
    return {
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "source": chunk.source,
        "page": chunk.page,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
    }


def _chunk_from_record(record: Any) -> DocumentChunk:
    if not isinstance(record, dict):
        raise ValueError("each chunk record must be an object")
    for field in ("chunk_id", "text", "source"):
        if not isinstance(record.get(field), str):
            raise ValueError(f"chunk field {field!r} must be text")
    for field in ("char_start", "char_end"):
        if type(record.get(field)) is not int or record[field] < 0:
            raise ValueError(f"chunk field {field!r} must be a non-negative integer")
    page = record.get("page")
    if page is not None and (type(page) is not int or page < 1):
        raise ValueError("chunk field 'page' must be a positive integer or null")
    if record["char_end"] < record["char_start"]:
        raise ValueError("chunk end offset must be greater than or equal to its start")
    return DocumentChunk(
        chunk_id=record["chunk_id"],
        text=record["text"],
        source=record["source"],
        page=page,
        char_start=record["char_start"],
        char_end=record["char_end"],
    )
