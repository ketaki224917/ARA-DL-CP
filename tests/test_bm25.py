"""Tests for lexical BM25 retrieval and persistence."""

import json

import pytest

from ara.rag.bm25 import BM25Index, BM25IndexError
from ara.rag.chunking import DocumentChunk


def chunk(
    chunk_id: str,
    text: str,
    *,
    source: str = "guide.md",
    page: int | None = None,
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        text=text,
        source=source,
        page=page,
        char_start=0,
        char_end=len(text),
    )


def test_search_ranks_term_matches_and_filters_provenance() -> None:
    index = BM25Index(
        [
            chunk("a", "Ollama embeddings use local models."),
            chunk("b", "Embeddings can be cached.", source="cache.md", page=2),
            chunk("c", "A guide to hybrid retrieval."),
        ]
    )

    matches = index.search("EMBEDDINGS ollama", where={"source": "guide.md"})

    assert [match.chunk.chunk_id for match in matches] == ["a"]
    assert matches[0].score > 0


def test_search_is_empty_for_unmatched_or_blank_queries() -> None:
    index = BM25Index([chunk("a", "local retrieval")])

    assert index.search("nothing-matches") == []
    assert index.search(" !!! ") == []
    assert BM25Index().search("retrieval") == []


def test_search_ties_are_deterministic_and_top_k_is_applied() -> None:
    index = BM25Index([chunk("z", "same token"), chunk("a", "same token")])

    matches = index.search("same", top_k=1)

    assert [match.chunk.chunk_id for match in matches] == ["a"]


def test_save_and_load_preserve_search_results(tmp_path) -> None:
    original = BM25Index(
        [chunk("a", "Local retrieval with citations."), chunk("b", "Remote retrieval.", page=3)],
        k1=1.2,
        b=0.6,
    )
    path = tmp_path / "nested" / "bm25.json"
    original.save(path)

    restored = BM25Index.load(path)

    assert len(restored) == 2
    assert restored.k1 == pytest.approx(1.2)
    assert restored.b == pytest.approx(0.6)
    assert restored.search("retrieval citations") == original.search("retrieval citations")
    assert not list(path.parent.glob("*.tmp"))


def test_load_rejects_malformed_index(tmp_path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"format_version": 99, "chunks": []}), encoding="utf-8")

    with pytest.raises(BM25IndexError, match="Could not load"):
        BM25Index.load(path)


def test_settings_and_duplicate_chunk_ids_are_validated() -> None:
    with pytest.raises(ValueError, match="k1"):
        BM25Index(k1=0)
    with pytest.raises(ValueError, match="b"):
        BM25Index(b=1.1)
    with pytest.raises(ValueError, match="unique"):
        BM25Index([chunk("same", "one"), chunk("same", "two")])
    with pytest.raises(ValueError, match="top_k"):
        BM25Index().search("query", top_k=0)
