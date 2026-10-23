"""Batched local Ollama embeddings with a persistent SQLite vector cache."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx

from ara.config import Settings, load_settings

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    """Raised when the embedding service returns an invalid result or request fails."""


class _SQLiteEmbeddingCache:
    """Small persistent cache keyed by model name and a hash of input text."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def get_many(self, keys: Sequence[str]) -> dict[str, list[float]]:
        """Read cached vectors for a collection of hashed keys."""
        if not keys:
            return {}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            self._create_table(connection)
            results: dict[str, list[float]] = {}
            for key in keys:
                row = connection.execute(
                    "SELECT vector_json FROM embeddings WHERE cache_key = ?", (key,)
                ).fetchone()
                if row is not None:
                    try:
                        results[key] = _validate_vector(json.loads(row[0]))
                    except (EmbeddingError, TypeError, ValueError) as exc:
                        logger.warning("Ignoring malformed cached embedding %s: %s", key[:12], exc)
                        connection.execute(
                            "DELETE FROM embeddings WHERE cache_key = ?", (key,)
                        )
            return results

    def put_many(self, vectors: Sequence[tuple[str, list[float]]]) -> None:
        """Persist vectors atomically, replacing any prior row for the same key."""
        if not vectors:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            self._create_table(connection)
            connection.executemany(
                "INSERT OR REPLACE INTO embeddings(cache_key, vector_json) VALUES (?, ?)",
                [
                    (key, json.dumps(vector, separators=(",", ":")))
                    for key, vector in vectors
                ],
            )

    @staticmethod
    def _create_table(connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS embeddings ("
            "cache_key TEXT PRIMARY KEY, vector_json TEXT NOT NULL)"
        )


class OllamaEmbeddings:
    """Compute local embeddings in batches and reuse vectors from a SQLite cache.

    Requests go to Ollama's `/api/embed` endpoint. The HTTP client and cache database
    are created only when embedding work is requested.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        http_client: httpx.Client | None = None,
        batch_size: int = 32,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        resolved = settings or load_settings()
        self.base_url = str(resolved.llm_base_url).rstrip("/")
        self.model = resolved.embedding_model
        self.timeout_seconds = resolved.llm_request_timeout_seconds
        self.batch_size = batch_size
        self.cache_path = resolved.embedding_cache_path
        self._cache = _SQLiteEmbeddingCache(self.cache_path)
        self._http_client = http_client
        self._owns_http_client = http_client is None

    def embed_query(self, text: str) -> list[float]:
        """Embed one query string."""
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed texts in bounded batches, returning vectors in the original order."""
        if any(not isinstance(text, str) for text in texts):
            raise TypeError("All embedding inputs must be strings")
        if not texts:
            return []

        unique_texts = list(dict.fromkeys(texts))
        keys = {text: self._cache_key(text) for text in unique_texts}
        vectors = self._cache.get_many(list(keys.values()))
        missing = [text for text in unique_texts if keys[text] not in vectors]
        for offset in range(0, len(missing), self.batch_size):
            batch = missing[offset : offset + self.batch_size]
            batch_vectors = self._request_embeddings(batch)
            self._cache.put_many(
                [(keys[text], vector) for text, vector in zip(batch, batch_vectors, strict=True)]
            )
            vectors.update(
                (keys[text], vector) for text, vector in zip(batch, batch_vectors, strict=True)
            )
        if len({len(vector) for vector in vectors.values()}) > 1:
            raise EmbeddingError("Cached or generated vectors have inconsistent dimensions.")
        return [vectors[keys[text]] for text in texts]

    def close(self) -> None:
        """Close the internally owned HTTP client, if created."""
        if self._owns_http_client and self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> OllamaEmbeddings:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            response = self._http().post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": list(texts)},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.exception("Local embedding request failed")
            raise EmbeddingError("Ollama embedding request failed.") from exc
        raw_vectors = payload.get("embeddings") if isinstance(payload, dict) else None
        if not isinstance(raw_vectors, list) or len(raw_vectors) != len(texts):
            raise EmbeddingError("Ollama returned an unexpected number of embeddings.")
        vectors = [_validate_vector(vector) for vector in raw_vectors]
        dimensions = {len(vector) for vector in vectors}
        if len(dimensions) > 1:
            raise EmbeddingError("Ollama returned vectors with inconsistent dimensions.")
        return vectors

    def _cache_key(self, text: str) -> str:
        """Hash model and content to avoid storing source text in the cache."""
        return hashlib.sha256(f"{self.model}\0{text}".encode()).hexdigest()

    def _http(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=self.timeout_seconds)
        return self._http_client


def _validate_vector(value: Any) -> list[float]:
    """Validate and normalize an embedding returned by the service."""
    if not isinstance(value, list) or not value:
        raise EmbeddingError("Ollama returned an empty or malformed embedding.")
    try:
        vector = [float(dimension) for dimension in value]
    except (TypeError, ValueError) as exc:
        raise EmbeddingError("Ollama returned a non-numeric embedding value.") from exc
    if not all(math.isfinite(dimension) for dimension in vector):
        raise EmbeddingError("Ollama returned a non-finite embedding value.")
    return vector

