"""Vector-store protocol, in-memory implementation, and persistent Chroma adapter."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ara.rag.chunking import DocumentChunk


class VectorStoreError(RuntimeError):
    """Raised when a vector-store operation receives invalid data or fails."""


@dataclass(frozen=True)
class VectorSearchResult:
    """A stored chunk and its similarity score, ordered highest score first."""

    chunk: DocumentChunk
    score: float


class VectorStore(Protocol):
    """Storage contract shared by retrieval backends."""

    def upsert(
        self,
        chunks: Sequence[DocumentChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        """Insert or replace chunk records and their vector representations."""

    def search(
        self,
        embedding: Sequence[float],
        *,
        top_k: int = 8,
        where: Mapping[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Return the most similar stored chunks."""

    def get(self, chunk_ids: Sequence[str]) -> list[DocumentChunk]:
        """Fetch stored chunks by stable IDs, preserving requested order."""

    def ids(self) -> list[str]:
        """Return all stored chunk IDs in deterministic order."""

    def delete(self, chunk_ids: Sequence[str]) -> None:
        """Remove the supplied IDs if they exist."""


class InMemoryVectorStore:
    """Simple cosine-similarity store useful for small corpora and unit tests."""

    def __init__(self) -> None:
        self._records: dict[str, tuple[DocumentChunk, list[float]]] = {}

    def upsert(
        self,
        chunks: Sequence[DocumentChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        """Insert or replace chunks after validating vector counts and dimensions."""
        if len(chunks) != len(embeddings):
            raise VectorStoreError("Chunk and embedding counts must match.")
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            vector = _validate_embedding(embedding)
            self._records[chunk.chunk_id] = (chunk, vector)

    def search(
        self,
        embedding: Sequence[float],
        *,
        top_k: int = 8,
        where: Mapping[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Return cosine-ranked chunks with deterministic tie breaking."""
        query = _validate_embedding(embedding)
        _validate_top_k(top_k)
        matches: list[VectorSearchResult] = []
        for chunk, vector in self._records.values():
            if where and not _metadata_matches(chunk, where):
                continue
            if len(vector) != len(query):
                raise VectorStoreError("Query and stored embedding dimensions do not match.")
            matches.append(VectorSearchResult(chunk=chunk, score=_cosine_similarity(query, vector)))
        matches.sort(key=lambda item: (-item.score, item.chunk.chunk_id))
        return matches[:top_k]

    def get(self, chunk_ids: Sequence[str]) -> list[DocumentChunk]:
        """Return only existing chunks, in the order requested by the caller."""
        return [
            self._records[chunk_id][0]
            for chunk_id in dict.fromkeys(chunk_ids)
            if chunk_id in self._records
        ]

    def ids(self) -> list[str]:
        """Return all stored chunk IDs in sorted order."""
        return sorted(self._records)

    def delete(self, chunk_ids: Sequence[str]) -> None:
        """Remove stored chunks and vectors by ID."""
        for chunk_id in chunk_ids:
            self._records.pop(chunk_id, None)


class ChromaVectorStore:
    """Persistent Chroma adapter using cosine distance and caller-provided embeddings."""

    def __init__(
        self,
        persist_path: Path | str,
        *,
        collection_name: str = "ara_chunks",
        collection: Any | None = None,
    ) -> None:
        if collection is not None:
            self._collection = collection
            return
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(persist_path))
            self._collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            raise VectorStoreError(f"Could not initialize Chroma collection: {exc}") from exc

    def upsert(
        self,
        chunks: Sequence[DocumentChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        """Insert or replace chunk text, metadata, and precomputed embeddings."""
        if len(chunks) != len(embeddings):
            raise VectorStoreError("Chunk and embedding counts must match.")
        if not chunks:
            return
        vectors = [_validate_embedding(embedding) for embedding in embeddings]
        dimensions = {len(vector) for vector in vectors}
        if len(dimensions) > 1:
            raise VectorStoreError("All embeddings in a batch must have the same dimension.")
        try:
            self._collection.upsert(
                ids=[chunk.chunk_id for chunk in chunks],
                embeddings=vectors,
                documents=[chunk.text for chunk in chunks],
                metadatas=[_chunk_metadata(chunk) for chunk in chunks],
            )
        except Exception as exc:
            raise VectorStoreError(f"Chroma upsert failed: {exc}") from exc

    def search(
        self,
        embedding: Sequence[float],
        *,
        top_k: int = 8,
        where: Mapping[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """Query Chroma and convert cosine distances to higher-is-better scores."""
        query = _validate_embedding(embedding)
        _validate_top_k(top_k)
        request: dict[str, Any] = {
            "query_embeddings": [query],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            request["where"] = dict(where)
        try:
            result = self._collection.query(**request)
        except Exception as exc:
            raise VectorStoreError(f"Chroma query failed: {exc}") from exc
        try:
            ids = result["ids"][0]
            documents = result["documents"][0]
            metadatas = result["metadatas"][0]
            distances = result["distances"][0]
        except (KeyError, IndexError, TypeError) as exc:
            raise VectorStoreError("Chroma returned a malformed query response.") from exc
        if not (len(ids) == len(documents) == len(metadatas) == len(distances)):
            raise VectorStoreError("Chroma returned mismatched result fields.")
        matches: list[VectorSearchResult] = []
        for chunk_id, text, metadata, distance in zip(
            ids, documents, metadatas, distances, strict=True
        ):
            if text is None or metadata is None:
                raise VectorStoreError("Chroma result is missing text or metadata.")
            chunk = _chunk_from_record(str(chunk_id), str(text), metadata)
            matches.append(VectorSearchResult(chunk=chunk, score=1.0 - float(distance)))
        return matches

    def get(self, chunk_ids: Sequence[str]) -> list[DocumentChunk]:
        """Fetch chunks by ID and preserve the requested ID order."""
        requested = list(dict.fromkeys(chunk_ids))
        if not requested:
            return []
        try:
            result = self._collection.get(ids=requested, include=["documents", "metadatas"])
            ids = result["ids"]
            documents = result["documents"]
            metadatas = result["metadatas"]
        except (KeyError, TypeError) as exc:
            raise VectorStoreError("Chroma returned a malformed get response.") from exc
        if not (len(ids) == len(documents) == len(metadatas)):
            raise VectorStoreError("Chroma returned mismatched get fields.")
        records: dict[str, DocumentChunk] = {}
        for chunk_id, text, metadata in zip(ids, documents, metadatas, strict=True):
            if text is None or metadata is None:
                continue
            key = str(chunk_id)
            records[key] = _chunk_from_record(key, str(text), metadata)
        return [records[chunk_id] for chunk_id in requested if chunk_id in records]

    def ids(self) -> list[str]:
        """Return all stored chunk IDs in sorted order."""
        try:
            result = self._collection.get(include=["metadatas"])
            ids = result["ids"]
        except (KeyError, TypeError) as exc:
            raise VectorStoreError("Chroma returned a malformed ID response.") from exc
        if not isinstance(ids, list):
            raise VectorStoreError("Chroma returned malformed chunk IDs.")
        return sorted(str(chunk_id) for chunk_id in ids)

    def delete(self, chunk_ids: Sequence[str]) -> None:
        """Delete stored chunks by ID, ignoring duplicate and empty requests."""
        ids = list(dict.fromkeys(chunk_ids))
        if not ids:
            return
        try:
            self._collection.delete(ids=ids)
        except Exception as exc:
            raise VectorStoreError(f"Chroma delete failed: {exc}") from exc


class QdrantVectorStore:
    """Reserved Qdrant adapter slot; implement against the shared protocol when selected."""

    def __init__(self, *_: object, **__: object) -> None:
        raise NotImplementedError("Qdrant adapter is not implemented; use ChromaVectorStore.")


def _chunk_metadata(chunk: DocumentChunk) -> dict[str, str | int]:
    """Convert chunk provenance to Chroma-compatible scalar metadata."""
    metadata: dict[str, str | int] = {
        "source": chunk.source,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
    }
    if chunk.page is not None:
        metadata["page"] = chunk.page
    return metadata


def _chunk_from_record(chunk_id: str, text: str, metadata: Mapping[str, Any]) -> DocumentChunk:
    """Build a chunk from storage fields, failing on incomplete provenance."""
    try:
        return DocumentChunk(
            chunk_id=chunk_id,
            text=text,
            source=str(metadata["source"]),
            page=int(metadata["page"]) if metadata.get("page") is not None else None,
            char_start=int(metadata["char_start"]),
            char_end=int(metadata["char_end"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise VectorStoreError(
            f"Stored chunk {chunk_id!r} has invalid provenance metadata."
        ) from exc


def _metadata_matches(chunk: DocumentChunk, conditions: Mapping[str, Any]) -> bool:
    """Apply exact-match metadata conditions in the in-memory adapter."""
    chunk_metadata = _chunk_metadata(chunk)
    return all(chunk_metadata.get(key) == value for key, value in conditions.items())


def _validate_embedding(embedding: Sequence[float]) -> list[float]:
    """Normalize a vector and reject empty, non-numeric, or non-finite values."""
    if not embedding:
        raise VectorStoreError("Embedding vectors cannot be empty.")
    try:
        vector = [float(value) for value in embedding]
    except (TypeError, ValueError) as exc:
        raise VectorStoreError("Embedding values must be numeric.") from exc
    if not all(math.isfinite(value) for value in vector):
        raise VectorStoreError("Embedding values must be finite.")
    return vector


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Compute cosine similarity, returning zero when either vector has zero norm."""
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _validate_top_k(top_k: int) -> None:
    """Reject nonsensical search limits."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

