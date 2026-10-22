"""Deterministic, offset-preserving recursive text chunking."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ara.rag.types import LoadedDocument

DEFAULT_SEPARATORS = ("\n\n", "\n", ". ", " ")


@dataclass(frozen=True)
class DocumentChunk:
    """One indexed passage with stable ID and source offsets."""

    chunk_id: str
    text: str
    source: str
    page: int | None
    char_start: int
    char_end: int


def chunk_documents(
    documents: Iterable[LoadedDocument],
    *,
    chunk_size: int = 900,
    overlap: int = 120,
    separators: Sequence[str] = DEFAULT_SEPARATORS,
) -> list[DocumentChunk]:
    """Chunk documents deterministically while retaining source and character offsets."""
    _validate_settings(chunk_size, overlap)
    return [
        chunk
        for document in documents
        for chunk in chunk_document(
            document,
            chunk_size=chunk_size,
            overlap=overlap,
            separators=separators,
        )
    ]


def chunk_document(
    document: LoadedDocument,
    *,
    chunk_size: int = 900,
    overlap: int = 120,
    separators: Sequence[str] = DEFAULT_SEPARATORS,
) -> list[DocumentChunk]:
    """Split one document, preferring paragraph, line, sentence, then word boundaries."""
    _validate_settings(chunk_size, overlap)
    text = document.text
    chunks: list[DocumentChunk] = []
    start = 0
    while start < len(text):
        limit = min(start + chunk_size, len(text))
        end = limit if limit == len(text) else _recursive_boundary(text, start, limit, separators)
        content_start = start
        content_end = end
        while content_start < content_end and text[content_start].isspace():
            content_start += 1
        while content_end > content_start and text[content_end - 1].isspace():
            content_end -= 1
        content = text[content_start:content_end]
        if content:
            chunk_id = _chunk_id(
                document.source,
                document.page,
                content_start,
                content_end,
                content,
            )
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    text=content,
                    source=document.source,
                    page=document.page,
                    char_start=content_start,
                    char_end=content_end,
                )
            )
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def _recursive_boundary(
    text: str,
    start: int,
    limit: int,
    separators: Sequence[str],
) -> int:
    """Select the last preferred separator in the latter half of the chunk window."""
    if not separators:
        return limit
    separator = separators[0]
    search_from = start + max(1, (limit - start) // 2)
    position = text.rfind(separator, search_from, limit)
    if position >= 0:
        return position + len(separator)
    return _recursive_boundary(text, start, limit, separators[1:])


def _chunk_id(source: str, page: int | None, start: int, end: int, text: str) -> str:
    """Build a stable chunk identifier from source coordinates and passage text."""
    identity = f"{source}\0{page or 0}\0{start}\0{end}\0{text}".encode("utf-8")
    return f"chunk:{hashlib.sha256(identity).hexdigest()[:20]}"


def _validate_settings(chunk_size: int, overlap: int) -> None:
    """Reject unusable chunk size and overlap values."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

