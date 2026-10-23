"""Tests for idempotent dense and lexical index reconciliation."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from ara.rag.bm25 import BM25Index
from ara.rag.chunking import DocumentChunk
from ara.rag.indexing import ingest_corpus
from ara.rag.types import LoadedDocument
from ara.rag.vectorstore import InMemoryVectorStore


class FakeEmbeddings:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[float(len(text)), 1.0] for text in texts]

    def close(self) -> None:
        return None


def make_settings(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        ingest_source_dir=tmp_path / "sources",
        embedding_model="test-embedding-model",
        retrieval_chunk_size=64,
        retrieval_chunk_overlap=8,
        bm25_index_path=tmp_path / "indexes" / "bm25.json",
        ingest_manifest_path=tmp_path / "indexes" / "manifest.json",
        vector_store_dir=tmp_path / "indexes" / "chroma",
    )


def test_ingest_is_idempotent_and_skips_unchanged_corpus(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    store = InMemoryVectorStore()
    embeddings = FakeEmbeddings()
    documents = [LoadedDocument(source="notes.md", text="local retrieval evidence " * 8)]

    def loader(_: Path) -> list[LoadedDocument]:
        return documents

    first = ingest_corpus(
        settings=settings,
        document_loader=loader,
        embeddings=embeddings,
        vector_store=store,
    )
    second = ingest_corpus(
        settings=settings,
        document_loader=loader,
        embeddings=embeddings,
        vector_store=store,
    )

    assert first.skipped is False
    assert first.added_count > 0
    assert second.skipped is True
    assert second.chunk_count == first.chunk_count
    assert len(embeddings.calls) == 1
    assert len(store.ids()) == first.chunk_count


def test_ingest_replaces_changed_chunks_and_rebuilds_bm25(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    store = InMemoryVectorStore()
    embeddings = FakeEmbeddings()
    documents = [LoadedDocument(source="notes.md", text="old content " * 10)]

    before = ingest_corpus(
        settings=settings,
        document_loader=lambda _: documents,
        embeddings=embeddings,
        vector_store=store,
    )
    documents[:] = [LoadedDocument(source="notes.md", text="new content " * 10)]
    after = ingest_corpus(
        settings=settings,
        document_loader=lambda _: documents,
        embeddings=embeddings,
        vector_store=store,
    )

    assert before.chunk_count == after.chunk_count
    assert after.skipped is False
    assert after.added_count > 0
    assert after.removed_count > 0
    assert set(BM25Index.load(settings.bm25_index_path).chunk_ids) == set(store.ids())


def test_ingest_rejects_empty_source_without_deleting_existing_index(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    store = InMemoryVectorStore()
    existing = DocumentChunk("existing", "text", "notes.md", None, 0, 4)
    store.upsert([existing], [[1.0, 0.0]])

    with pytest.raises(ValueError, match="No supported source"):
        ingest_corpus(
            settings=settings,
            document_loader=lambda _: [],
            embeddings=FakeEmbeddings(),
            vector_store=store,
        )

    assert store.ids() == ["existing"]


def test_embedding_model_change_rebuilds_vectors_even_when_chunk_ids_match(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    store = InMemoryVectorStore()
    embeddings = FakeEmbeddings()
    documents = [LoadedDocument(source="notes.md", text="stable text for stable chunk ids")]

    def loader(_: Path) -> list[LoadedDocument]:
        return documents

    ingest_corpus(
        settings=settings,
        document_loader=loader,
        embeddings=embeddings,
        vector_store=store,
    )
    settings.embedding_model = "different-model"

    updated = ingest_corpus(
        settings=settings,
        document_loader=loader,
        embeddings=embeddings,
        vector_store=store,
    )

    assert updated.skipped is False
    assert updated.updated_count == updated.chunk_count
    assert updated.added_count == updated.removed_count == 0
    assert len(embeddings.calls) == 2


def test_ingest_rebuilds_a_malformed_bm25_file(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.bm25_index_path.parent.mkdir(parents=True)
    settings.bm25_index_path.write_text("bad json", encoding="utf-8")
    store = InMemoryVectorStore()
    docs = [LoadedDocument(source="notes.md", text="rebuild this lexical index")]

    result = ingest_corpus(
        settings=settings,
        document_loader=lambda _: docs,
        embeddings=FakeEmbeddings(),
        vector_store=store,
    )

    assert result.skipped is False
    assert settings.bm25_index_path.is_file()
