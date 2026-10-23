"""Idempotent orchestration for document loading and retrieval-index updates."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from ara.rag.bm25 import BM25Index, BM25IndexError
from ara.rag.chunking import chunk_documents
from ara.rag.vectorstore import VectorStore

if TYPE_CHECKING:
    from ara.config import Settings
    from ara.rag.types import LoadedDocument

logger = logging.getLogger(__name__)
_MANIFEST_VERSION = 2


class DocumentEmbeddings(Protocol):
    """Batch embedding interface used by the ingestion pipeline."""

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per input string."""

    def close(self) -> None:
        """Close any resources owned by the embedding client."""


@dataclass(frozen=True)
class IngestionSummary:
    """Counts and state for one corpus index operation."""

    source_count: int
    document_count: int
    chunk_count: int
    added_count: int
    updated_count: int
    removed_count: int
    skipped: bool


def ingest_corpus(
    source_dir: Path | str | None = None,
    *,
    settings: Settings | None = None,
    document_loader: Callable[[Path], Sequence[LoadedDocument]] | None = None,
    embeddings: DocumentEmbeddings | None = None,
    vector_store: VectorStore | None = None,
) -> IngestionSummary:
    """Load a corpus and reconcile dense, lexical, and manifest indexes.

    Stable chunk IDs make repeated upserts idempotent. A manifest plus ID checks
    allow a fully unchanged corpus to skip embedding and storage work. Removed or
    changed chunk IDs are deleted from the dense collection after current vectors
    have been written.
    """
    if settings is None:
        from ara.config import load_settings

        resolved = load_settings()
    else:
        resolved = settings
    source = Path(resolved.ingest_source_dir if source_dir is None else source_dir)

    if document_loader is None:
        from ara.rag.ingest import load_directory

        document_loader = load_directory
    documents = list(document_loader(source))
    if not documents:
        raise ValueError(f"No supported source documents were found in {source}.")

    chunks = chunk_documents(
        documents,
        chunk_size=resolved.retrieval_chunk_size,
        overlap=resolved.retrieval_chunk_overlap,
    )
    if not chunks:
        raise ValueError(f"No non-empty text chunks were produced from {source}.")

    source_hashes = _source_hashes(documents)
    active_ids = {chunk.chunk_id for chunk in chunks}
    expected_manifest = _make_manifest(
        source_hashes=source_hashes,
        chunk_ids=active_ids,
        chunk_size=resolved.retrieval_chunk_size,
        chunk_overlap=resolved.retrieval_chunk_overlap,
        embedding_model=resolved.embedding_model,
    )
    store = vector_store if vector_store is not None else _make_vector_store(resolved)
    current_ids = set(store.ids())
    current_bm25 = _load_existing_bm25(resolved.bm25_index_path)
    current_manifest = _read_manifest(resolved.ingest_manifest_path)
    if (
        current_manifest == expected_manifest
        and current_ids == active_ids
        and current_bm25 is not None
        and set(current_bm25.chunk_ids) == active_ids
    ):
        logger.info("Ingestion skipped; %d chunks are already current", len(chunks))
        return IngestionSummary(
            source_count=len({document.source for document in documents}),
            document_count=len(documents),
            chunk_count=len(chunks),
            added_count=0,
            updated_count=0,
            removed_count=0,
            skipped=True,
        )

    owns_embeddings = embeddings is None
    embedder = embeddings if embeddings is not None else _make_embeddings(resolved)
    stored_ids = set(current_ids)
    embedding_model_changed = (
        current_manifest is not None
        and current_manifest.get("embedding_model") != resolved.embedding_model
    )
    try:
        vectors = embedder.embed_documents([chunk.text for chunk in chunks])
        if embedding_model_changed:
            store.delete(sorted(current_ids))
        store.upsert(chunks, vectors)
        stale_ids = sorted(stored_ids - active_ids)
        if not embedding_model_changed:
            stale_ids = sorted(current_ids - active_ids)
        store.delete(stale_ids)
        BM25Index(chunks).save(resolved.bm25_index_path)
        _write_manifest(resolved.ingest_manifest_path, expected_manifest)
    finally:
        if owns_embeddings:
            embedder.close()

    logger.info(
        "Indexed %d documents into %d chunks; added=%d removed=%d",
        len(documents),
        len(chunks),
        len(active_ids - stored_ids),
        len(stale_ids),
    )
    return IngestionSummary(
        source_count=len({document.source for document in documents}),
        document_count=len(documents),
        chunk_count=len(chunks),
        added_count=len(active_ids - stored_ids),
        updated_count=len(active_ids & stored_ids) if embedding_model_changed else 0,
        removed_count=len(stale_ids),
        skipped=False,
    )


def _make_embeddings(settings: Settings) -> DocumentEmbeddings:
    from ara.rag.embeddings import OllamaEmbeddings

    return OllamaEmbeddings(settings)


def _make_vector_store(settings: Settings) -> VectorStore:
    from ara.rag.vectorstore import ChromaVectorStore

    return ChromaVectorStore(settings.vector_store_dir)


def _source_hashes(documents: Sequence[LoadedDocument]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for document in documents:
        page_label = str(document.page) if document.page is not None else "document"
        key = f"{document.source}#{page_label}"
        hashes[key] = hashlib.sha256(document.text.encode("utf-8")).hexdigest()
    return dict(sorted(hashes.items()))


def _make_manifest(
    *,
    source_hashes: dict[str, str],
    chunk_ids: set[str],
    chunk_size: int,
    chunk_overlap: int,
    embedding_model: str,
) -> dict[str, Any]:
    return {
        "format_version": _MANIFEST_VERSION,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "embedding_model": embedding_model,
        "sources": source_hashes,
        "chunk_ids": sorted(chunk_ids),
    }


def _load_existing_bm25(path: Path) -> BM25Index | None:
    if not path.is_file():
        return None
    try:
        return BM25Index.load(path)
    except BM25IndexError as exc:
        logger.warning("Rebuilding invalid BM25 index %s: %s", path, exc)
        return None


def _read_manifest(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    temporary_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f"{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(path)
    except (OSError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Could not save ingestion manifest to {path}: {exc}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
