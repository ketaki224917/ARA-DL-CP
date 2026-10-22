"""Tests for in-memory ranking and the Chroma protocol adapter."""

from pathlib import Path
from typing import Any

import pytest

from ara.rag.chunking import DocumentChunk
from ara.rag.vectorstore import (
    ChromaVectorStore,
    InMemoryVectorStore,
    QdrantVectorStore,
    VectorStoreError,
)


def chunk(chunk_id: str, text: str, source: str = "a.txt", page: int | None = None) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        text=text,
        source=source,
        page=page,
        char_start=0,
        char_end=len(text),
    )


class FakeCollection:
    def __init__(self) -> None:
        self.upsert_args: dict[str, Any] = {}
        self.query_args: dict[str, Any] = {}
        self.get_args: dict[str, Any] = {}

    def upsert(self, **kwargs: Any) -> None:
        self.upsert_args = kwargs

    def query(self, **kwargs: Any) -> dict[str, list[list[Any]]]:
        self.query_args = kwargs
        return {
            "ids": [["b", "a"]],
            "documents": [["second", "first"]],
            "metadatas": [
                [
                    {"source": "b.txt", "char_start": 0, "char_end": 6, "page": 2},
                    {"source": "a.txt", "char_start": 0, "char_end": 5},
                ]
            ],
            "distances": [[0.1, 0.3]],
        }

    def get(self, **kwargs: Any) -> dict[str, list[Any]]:
        self.get_args = kwargs
        return {
            "ids": ["a", "b"],
            "documents": ["first", "second"],
            "metadatas": [
                {"source": "a.txt", "char_start": 0, "char_end": 5},
                {"source": "b.txt", "char_start": 0, "char_end": 6, "page": 2},
            ],
        }


def test_memory_store_ranks_cosine_and_applies_metadata_filters() -> None:
    store = InMemoryVectorStore()
    store.upsert(
        [chunk("a", "alpha", source="a.txt"), chunk("b", "beta", source="b.txt")],
        [[1, 0], [0, 1]],
    )

    matches = store.search([0.9, 0.1], where={"source": "a.txt"})

    assert [match.chunk.chunk_id for match in matches] == ["a"]
    assert matches[0].score > 0.99


def test_memory_store_get_preserves_requested_order() -> None:
    store = InMemoryVectorStore()
    store.upsert([chunk("a", "first"), chunk("b", "second")], [[1], [0]])

    assert [item.chunk_id for item in store.get(["b", "missing", "a"])] == ["b", "a"]


def test_memory_store_validates_dimensions_and_count() -> None:
    store = InMemoryVectorStore()
    store.upsert([chunk("a", "one")], [[1, 0]])

    with pytest.raises(VectorStoreError, match="dimensions"):
        store.search([1, 0, 0])
    with pytest.raises(VectorStoreError, match="counts"):
        store.upsert([chunk("b", "two")], [])


def test_chroma_adapter_upserts_metadata_and_converts_distances() -> None:
    collection = FakeCollection()
    store = ChromaVectorStore(Path("unused"), collection=collection)
    store.upsert([chunk("a", "text", page=4)], [[0.1, 0.2]])

    matches = store.search([0.2, 0.3], top_k=2, where={"source": "a.txt"})

    assert collection.upsert_args["ids"] == ["a"]
    assert collection.upsert_args["metadatas"] == [
        {"source": "a.txt", "char_start": 0, "char_end": 4, "page": 4}
    ]
    assert collection.query_args["where"] == {"source": "a.txt"}
    assert [match.chunk.chunk_id for match in matches] == ["b", "a"]
    assert [match.score for match in matches] == pytest.approx([0.9, 0.7])


def test_chroma_get_preserves_requested_order_and_reconstructs_page_metadata() -> None:
    store = ChromaVectorStore(Path("unused"), collection=FakeCollection())

    chunks = store.get(["b", "a"])

    assert [item.chunk_id for item in chunks] == ["b", "a"]
    assert chunks[0].page == 2
    assert chunks[1].page is None


def test_chroma_rejects_malformed_query_response() -> None:
    class MalformedCollection(FakeCollection):
        def query(self, **_: Any) -> dict[str, list[list[Any]]]:
            return {"ids": [[]]}

    store = ChromaVectorStore(Path("unused"), collection=MalformedCollection())

    with pytest.raises(VectorStoreError, match="malformed query"):
        store.search([1.0])


def test_qdrant_stub_reports_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="not implemented"):
        QdrantVectorStore()

