"""Tests for deterministic chunk boundaries and metadata."""

import pytest

from ara.rag.chunking import chunk_document, chunk_documents
from ara.rag.types import LoadedDocument


def test_chunking_preserves_source_page_offsets_and_content() -> None:
    text = "Alpha paragraph.\n\nBeta paragraph.\n\nGamma paragraph."
    document = LoadedDocument(source="report.pdf", page=3, text=text)

    chunks = chunk_document(document, chunk_size=24, overlap=4)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.source == "report.pdf"
        assert chunk.page == 3
        assert text[chunk.char_start : chunk.char_end] == chunk.text
        assert chunk.char_end - chunk.char_start <= 24


def test_chunk_ids_are_deterministic_for_the_same_input() -> None:
    document = LoadedDocument(source="a.txt", text="one two three four five six")

    first = chunk_document(document, chunk_size=12, overlap=2)
    second = chunk_document(document, chunk_size=12, overlap=2)

    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]


def test_batch_chunking_skips_empty_documents() -> None:
    documents = [LoadedDocument(source="empty.txt", text=" \n ")]

    assert chunk_documents(documents, chunk_size=10, overlap=0) == []


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (10, -1), (10, 10)],
)
def test_invalid_chunking_settings_are_rejected(chunk_size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        chunk_document(
            LoadedDocument(source="a.txt", text="text"),
            chunk_size=chunk_size,
            overlap=overlap,
        )

