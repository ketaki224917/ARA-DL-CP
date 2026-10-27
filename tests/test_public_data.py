"""Tests for checksum-pinned public retrieval data preparation and document splits."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any

import pytest

from ara.dl import public_data
from ara.dl.public_data import DatasetPreparationError


def _raw_claim(claim_id: int, document_id: int, label: str = "SUPPORT") -> dict[str, Any]:
    return {
        "id": claim_id,
        "claim": f"Scientific claim {claim_id} has an annotated evidence abstract.",
        "evidence": {
            str(document_id): [{"label": label, "sentences": [0, 2]}],
        },
        "cited_doc_ids": [document_id],
    }


def _fixture_archive(path: Path) -> bytes:
    claims = [_raw_claim(index, 2000 + index) for index in range(12)]
    claims[1] = _raw_claim(1, 2000, "CONTRADICT")
    claims[8] = {
        **claims[8],
        "evidence": {
            "2008": [
                {"label": "SUPPORT", "sentences": [1]},
                {"label": "SUPPORT", "sentences": [2]},
            ],
            "2009": [{"label": "CONTRADICT", "sentences": [3]}],
        },
    }
    documents = [
        {"doc_id": 2000 + index, "title": f"Evidence title {index}", "abstract": [
            f"Evidence abstract {index} contains a scientific result and supporting details."
        ], "structured": False}
        for index in range(13)
    ]
    members = {
        "data/claims_train.jsonl": claims[:8],
        "data/claims_dev.jsonl": claims[8:],
        "data/corpus.jsonl": documents,
    }
    with tarfile.open(path, mode="w:gz") as archive:
        for name, records in members.items():
            payload = "".join(json.dumps(record) + "\n" for record in records).encode()
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return path.read_bytes()


def test_subset_preserves_labels_and_groups_documents_without_leakage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = tmp_path / "scifact.tar.gz"
    payload = _fixture_archive(archive)
    monkeypatch.setattr(public_data, "SCIFACT_ARCHIVE_SHA256", hashlib.sha256(payload).hexdigest())

    first_dir = tmp_path / "prepared-a"
    second_dir = tmp_path / "prepared-b"
    metadata = public_data.prepare_scifact_subset(archive, first_dir, max_queries=100, seed=4)
    public_data.prepare_scifact_subset(archive, second_dir, max_queries=100, seed=4)

    assert metadata["selected_query_count"] == 12
    assert metadata["document_overlap"] is False
    assert metadata["split_ratios"] == {
        "train": 0.60,
        "validation": 0.10,
        "test": 0.30,
    }
    assert metadata["query_counts"]["train"] > 0
    assert metadata["query_counts"]["validation"] > 0
    assert metadata["query_counts"]["test"] > 0
    for name in (
        "corpus_train.jsonl",
        "corpus_validation.jsonl",
        "corpus_test.jsonl",
        "queries_train.jsonl",
        "queries_validation.jsonl",
        "queries_test.jsonl",
        "metadata.json",
    ):
        assert (first_dir / name).read_bytes() == (second_dir / name).read_bytes()

    split_docs: dict[str, set[str]] = {}
    split_queries: dict[str, list[dict[str, Any]]] = {}
    for split in ("train", "validation", "test"):
        split_docs[split] = {
            json.loads(line)["document_id"]
            for line in (first_dir / f"corpus_{split}.jsonl").read_text().splitlines()
        }
        split_queries[split] = [
            json.loads(line)
            for line in (first_dir / f"queries_{split}.jsonl").read_text().splitlines()
        ]
    assert not (split_docs["train"] & split_docs["validation"])
    assert not (split_docs["train"] & split_docs["test"])
    assert not (split_docs["validation"] & split_docs["test"])
    for split, rows in split_queries.items():
        assert all(row["split"] == split for row in rows)
        assert all(
            positive["document_id"] in split_docs[split]
            for row in rows
            for positive in row["positives"]
        )
    verdicts = {
        positive["verdict"]
        for rows in split_queries.values()
        for row in rows
        for positive in row["positives"]
    }
    assert verdicts == {"SUPPORT", "CONTRADICT"}
    assert all(
        positive["relevance"] == 1
        for rows in split_queries.values()
        for row in rows
        for positive in row["positives"]
    )
    claim_with_multiple_rationales = next(
        row
        for rows in split_queries.values()
        for row in rows
        if row["query_id"] == "scifact:8"
    )
    positives_for_shared_doc = [
        positive
        for positive in claim_with_multiple_rationales["positives"]
        if positive["document_id"] == "2008"
    ]
    assert len(positives_for_shared_doc) == 1
    assert positives_for_shared_doc[0]["evidence_sentences"] == [1, 2]


def test_download_verifies_pinned_sha_and_uses_atomic_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"verified archive bytes"
    monkeypatch.setattr(public_data, "SCIFACT_ARCHIVE_SHA256", hashlib.sha256(payload).hexdigest())

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def geturl(self) -> str:
            return public_data.SCIFACT_DOWNLOAD_URL

        def read(self, _limit: int) -> bytes:
            return payload

    monkeypatch.setattr(public_data, "urlopen", lambda *_args, **_kwargs: Response())
    destination = tmp_path / "cache" / "scifact.tar.gz"

    assert public_data.download_scifact_archive(destination) == destination
    assert destination.read_bytes() == payload
    assert list(destination.parent.glob("*.tmp")) == []


def test_download_rejects_changed_archive_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(public_data, "urlopen", lambda *_args, **_kwargs: _Response(b"changed"))
    destination = tmp_path / "scifact.tar.gz"

    with pytest.raises(DatasetPreparationError, match="SHA-256 mismatch"):
        public_data.download_scifact_archive(destination)
    assert not destination.exists()


class _Response:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def geturl(self) -> str:
        return public_data.SCIFACT_DOWNLOAD_URL

    def read(self, _limit: int) -> bytes:
        return self.payload


def test_archive_checksum_is_required_before_preparation(tmp_path: Path) -> None:
    archive = tmp_path / "wrong.tar.gz"
    archive.write_bytes(b"not the official archive")

    with pytest.raises(DatasetPreparationError, match="pinned SHA-256"):
        public_data.prepare_scifact_subset(archive, tmp_path / "out")
