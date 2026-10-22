"""Integrity checks for the labeled retrieval evaluation set."""

import json
from pathlib import Path

from ara.rag.chunking import chunk_document
from ara.rag.types import LoadedDocument

ROOT = Path(__file__).resolve().parents[1]
EVAL_PATH = ROOT / "data/eval_sets/rag_eval.jsonl"
CORPUS_PATH = ROOT / "data/sample_corpus"


def test_eval_set_has_balanced_categories_and_valid_gold_chunk_ids() -> None:
    records = [json.loads(line) for line in EVAL_PATH.read_text(encoding="utf-8").splitlines()]
    chunks = [
        chunk
        for path in sorted(CORPUS_PATH.glob("[0-9][0-9]_*.md"))
        for chunk in chunk_document(
            LoadedDocument(source=path.name, text=path.read_text(encoding="utf-8"))
        )
    ]
    chunk_ids = {chunk.chunk_id for chunk in chunks}

    assert len(records) >= 40
    assert len({record["id"] for record in records}) == len(records)
    categories = {record["category"] for record in records}
    assert categories == {"factoid", "multi_hop", "unanswerable"}
    assert sum(record["category"] == "multi_hop" for record in records) >= 5
    assert sum(record["category"] == "unanswerable" for record in records) >= 5
    assert all(
        len(record["gold_chunk_ids"]) >= 2
        for record in records
        if record["category"] == "multi_hop"
    )

    for record in records:
        assert bool(record["gold_chunk_ids"]) is record["answerable"]
        assert set(record["gold_chunk_ids"]).issubset(chunk_ids)
        assert (record["expected_answer"] is not None) is record["answerable"]
