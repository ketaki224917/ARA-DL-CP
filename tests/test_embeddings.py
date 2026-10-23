"""Tests for batched local embeddings and persistent cache behavior."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from ara.config import Settings
from ara.rag.embeddings import EmbeddingError, OllamaEmbeddings


def make_embedder(
    tmp_path: Path,
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    batch_size: int = 32,
) -> OllamaEmbeddings:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    settings = Settings.model_validate(
        {"embedding_cache_path": tmp_path / "cache" / "vectors.sqlite3"}
    )
    return OllamaEmbeddings(settings, http_client=client, batch_size=batch_size)


def vector_response(payload: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json=payload)


def test_embedding_batches_unique_texts_and_caches_results(tmp_path: Path) -> None:
    requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.read())
        requests.append(body)
        vectors = {"alpha": [1.0, 0.0], "beta": [0.0, 1.0]}
        return vector_response({"embeddings": [vectors[text] for text in body["input"]]})

    embedder = make_embedder(tmp_path, handler, batch_size=2)
    first = embedder.embed_documents(["alpha", "beta", "alpha"])
    second = embedder.embed_documents(["alpha", "beta"])

    assert first == [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]
    assert second == first[:2]
    assert len(requests) == 1
    assert requests[0]["input"] == ["alpha", "beta"]
    assert (tmp_path / "cache" / "vectors.sqlite3").is_file()
    embedder.close()


def test_embedding_splits_missing_texts_into_batches(tmp_path: Path) -> None:
    batch_lengths: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.read())
        batch_lengths.append(len(body["input"]))
        return vector_response({"embeddings": [[1.0] for _ in body["input"]]})

    embedder = make_embedder(tmp_path, handler, batch_size=2)

    assert len(embedder.embed_documents(["a", "b", "c", "d", "e"])) == 5
    assert batch_lengths == [2, 2, 1]
    embedder.close()


def test_empty_input_does_not_call_server(tmp_path: Path) -> None:
    def fail_if_called(_: httpx.Request) -> httpx.Response:
        raise AssertionError("empty input must not call the embedding server")

    embedder = make_embedder(tmp_path, fail_if_called)

    assert embedder.embed_documents([]) == []
    embedder.close()


@pytest.mark.parametrize(
    "payload",
    [{"embeddings": []}, {"embeddings": [[]]}, {"embeddings": [[float("nan")]]}],
)
def test_malformed_embedding_response_is_rejected(
    tmp_path: Path, payload: dict[str, Any]
) -> None:
    embedder = make_embedder(tmp_path, lambda _: vector_response(payload))

    with pytest.raises(EmbeddingError):
        embedder.embed_query("query")
    embedder.close()


def test_http_failure_is_wrapped(tmp_path: Path) -> None:
    embedder = make_embedder(tmp_path, lambda _: httpx.Response(503))

    with pytest.raises(EmbeddingError, match="request failed"):
        embedder.embed_query("query")
    embedder.close()


def test_invalid_batch_size_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="batch_size"):
        OllamaEmbeddings(Settings.model_validate({}), batch_size=0)
