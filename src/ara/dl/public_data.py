"""Prepare a small, document-disjoint SciFact subset for reranker experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
import tarfile
import tempfile
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field

from ara.config import Settings, load_settings

logger = logging.getLogger(__name__)
SCIFACT_DOWNLOAD_URL = "https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz"
SCIFACT_ARCHIVE_SHA256 = "11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be"
SCIFACT_REPOSITORY = "https://github.com/allenai/scifact"
SCIFACT_PAPER = "https://aclanthology.org/2020.emnlp-main.609/"
_MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
_SPLIT_RATIOS: dict[str, float] = {"train": 0.60, "validation": 0.10, "test": 0.30}
_SPLIT_NAMES = tuple(_SPLIT_RATIOS)


class DatasetPreparationError(RuntimeError):
    """Raised when the public dataset cannot be safely verified or prepared."""


class _Rationale(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: Literal["SUPPORT", "CONTRADICT"]
    sentences: list[int] = Field(min_length=1)


class _Claim(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    claim: str = Field(min_length=1)
    evidence: dict[str, list[_Rationale]]


class _CorpusDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")

    doc_id: int
    title: str
    abstract: list[str]


class SciFactPositive(BaseModel):
    """One annotated relevant document and its support/refute evidence label."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)
    relevance: Literal[1] = 1
    verdict: Literal["SUPPORT", "CONTRADICT"]
    evidence_sentences: list[int] = Field(min_length=1)


class SciFactExample(BaseModel):
    """A labeled scientific claim assigned to one held-out document split."""

    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    split: Literal["train", "validation", "test"]
    positives: list[SciFactPositive] = Field(min_length=1)


class SciFactDocument(BaseModel):
    """One public scientific abstract retained with its original corpus identifier."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)
    title: str
    text: str = Field(min_length=1)


@dataclass(frozen=True)
class _Component:
    claims: tuple[_Claim, ...]
    document_ids: frozenset[str]


class _UnionFind:
    def __init__(self) -> None:
        self.parents: dict[str, str] = {}

    def find(self, value: str) -> str:
        parent = self.parents.setdefault(value, value)
        if parent != value:
            self.parents[value] = self.find(parent)
        return self.parents[value]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parents[right_root] = left_root


def download_scifact_archive(destination: Path | str) -> Path:
    """Download the official archive only on explicit CLI request and verify its digest."""
    target = Path(destination)
    if target.is_file() and _sha256(target) == SCIFACT_ARCHIVE_SHA256:
        logger.info("Using verified SciFact archive at %s", target)
        return target

    request = Request(SCIFACT_DOWNLOAD_URL, headers={"User-Agent": "ARA-research-agent/0.1"})
    temporary_path: Path | None = None
    try:
        with urlopen(request, timeout=60) as response:
            final_url = urlparse(response.geturl())
            if (
                final_url.scheme != "https"
                or final_url.hostname != "scifact.s3-us-west-2.amazonaws.com"
            ):
                raise DatasetPreparationError("SciFact download redirected to an untrusted host.")
            payload = response.read(_MAX_ARCHIVE_BYTES + 1)
        if len(payload) > _MAX_ARCHIVE_BYTES:
            raise DatasetPreparationError("SciFact archive exceeded the 50 MiB download limit.")
        digest = hashlib.sha256(payload).hexdigest()
        if digest != SCIFACT_ARCHIVE_SHA256:
            raise DatasetPreparationError(
                "SciFact archive SHA-256 mismatch; upstream bytes changed or download was corrupt."
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f"{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(payload)
            stream.flush()
        temporary_path.replace(target)
    except DatasetPreparationError:
        raise
    except Exception as exc:
        logger.exception("Could not download official SciFact data")
        raise DatasetPreparationError(f"Could not download SciFact archive: {exc}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    logger.info("Downloaded and verified SciFact archive (%s) to %s", digest, target)
    return target


def prepare_scifact_subset(
    archive_path: Path | str,
    output_dir: Path | str,
    *,
    max_queries: int = 693,
    seed: int = 42,
) -> dict[str, Any]:
    """Build a deterministic, source-document-disjoint train/validation/test bundle."""
    if max_queries < 3:
        raise ValueError("max_queries must be at least three to populate all splits")
    archive = Path(archive_path)
    actual_digest = _sha256(archive)
    if actual_digest != SCIFACT_ARCHIVE_SHA256:
        raise DatasetPreparationError("SciFact archive does not match the pinned SHA-256 digest.")
    claims, corpus = _read_archive(archive)
    eligible_claims = [
        claim
        for claim in claims
        if claim.evidence and all(doc_id in corpus for doc_id in claim.evidence)
    ]
    if len(eligible_claims) < 3:
        raise DatasetPreparationError("SciFact archive has fewer than three labeled claims.")
    if len({claim.id for claim in eligible_claims}) != len(eligible_claims):
        raise DatasetPreparationError("SciFact claim IDs are duplicated across labeled splits.")

    rng = random.Random(seed)
    selected = sorted(
        rng.sample(eligible_claims, min(max_queries, len(eligible_claims))),
        key=lambda claim: claim.id,
    )
    components = _build_components(selected)
    if len(components) < len(_SPLIT_NAMES):
        raise DatasetPreparationError(
            "Selected claims form fewer than three document-linked groups; "
            "increase max_queries or change the seed."
        )
    split_by_claim, split_by_document = _assign_splits(components)
    for document_id in corpus:
        split_by_document.setdefault(document_id, _split_for_unassigned_doc(document_id, seed))

    split_examples: dict[str, list[SciFactExample]] = {name: [] for name in _SPLIT_NAMES}
    for claim in selected:
        split = split_by_claim[str(claim.id)]
        positives = [
            SciFactPositive(
                document_id=doc_id,
                verdict=rationale.label,
                evidence_sentences=rationale.sentences,
            )
            for doc_id, rationales in sorted(claim.evidence.items())
            for rationale in rationales
        ]
        unique_positives = _dedupe_positives(positives)
        if not unique_positives:
            continue
        if any(split_by_document[item.document_id] != split for item in unique_positives):
            raise DatasetPreparationError("A claim's positive evidence crossed document splits.")
        split_examples[split].append(
            SciFactExample(
                query_id=f"scifact:{claim.id}",
                query=claim.claim,
                split=split,  # type: ignore[arg-type]
                positives=unique_positives,
            )
        )

    split_documents: dict[str, list[SciFactDocument]] = {name: [] for name in _SPLIT_NAMES}
    for doc_id, document in corpus.items():
        split = split_by_document[doc_id]
        split_documents[split].append(document)
    for split in _SPLIT_NAMES:
        split_documents[split].sort(key=lambda item: item.document_id)
        split_examples[split].sort(key=lambda item: item.query_id)
    _validate_splits(split_documents, split_examples)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for split in _SPLIT_NAMES:
        _write_jsonl(output / f"corpus_{split}.jsonl", split_documents[split])
        _write_jsonl(output / f"queries_{split}.jsonl", split_examples[split])
    metadata: dict[str, Any] = {
        "dataset": "SciFact",
        "upstream_repository": SCIFACT_REPOSITORY,
        "paper": SCIFACT_PAPER,
        "download_url": SCIFACT_DOWNLOAD_URL,
        "archive_sha256": actual_digest,
        "claim_splits_used": ["train", "dev"],
        "official_test_claims_used": False,
        "claim_license": "CC BY 4.0",
        "abstract_license": "ODC-By 1.0 (S2ORC corpus)",
        "seed": seed,
        "requested_max_queries": max_queries,
        "selected_query_count": sum(map(len, split_examples.values())),
        "query_counts": {split: len(rows) for split, rows in split_examples.items()},
        "document_counts": {split: len(rows) for split, rows in split_documents.items()},
        "document_linked_component_count": len(components),
        "split_ratios": _SPLIT_RATIOS,
        "split_method": (
            "Claims connected by shared evidence document IDs are kept in one split; "
            "remaining corpus documents are assigned by seeded SHA-256 bucket."
        ),
        "relevance_mapping": (
            "Documents annotated SUPPORT or CONTRADICT are both relevant for retrieval; "
            "the verdict and rationale sentence IDs are retained."
        ),
        "document_overlap": False,
    }
    _write_json(output / "metadata.json", metadata)
    logger.info(
        "Prepared SciFact subset with %d queries and %d documents: %s",
        metadata["selected_query_count"],
        len(corpus),
        metadata["query_counts"],
    )
    return metadata


def _read_archive(
    archive: Path,
) -> tuple[list[_Claim], dict[str, SciFactDocument]]:
    try:
        with tarfile.open(archive, mode="r:gz") as tar:
            claims: list[_Claim] = []
            for split in ("train", "dev"):
                member = tar.extractfile(f"data/claims_{split}.jsonl")
                if member is None:
                    raise DatasetPreparationError(f"SciFact archive lacks claims_{split}.jsonl")
                claims.extend(_Claim.model_validate_json(line) for line in member)
            member = tar.extractfile("data/corpus.jsonl")
            if member is None:
                raise DatasetPreparationError("SciFact archive lacks corpus.jsonl")
            corpus: dict[str, SciFactDocument] = {}
            for line in member:
                raw = _CorpusDocument.model_validate_json(line)
                doc_id = str(raw.doc_id)
                if doc_id in corpus:
                    raise DatasetPreparationError(f"Duplicate SciFact document ID {doc_id!r}.")
                text = " ".join(raw.abstract).strip()
                if not text:
                    continue
                corpus[doc_id] = SciFactDocument(
                    document_id=doc_id,
                    title=raw.title,
                    text=f"{raw.title}\n\n{text}" if raw.title else text,
                )
    except DatasetPreparationError:
        raise
    except (KeyError, OSError, tarfile.TarError, ValueError) as exc:
        raise DatasetPreparationError(f"Could not parse SciFact archive: {exc}") from exc
    missing = sorted(
        {doc_id for claim in claims for doc_id in claim.evidence if doc_id not in corpus}
    )
    if missing:
        raise DatasetPreparationError(
            f"SciFact claim evidence refers to absent corpus IDs (first: {missing[0]})."
        )
    return claims, corpus


def _build_components(claims: Sequence[_Claim]) -> list[_Component]:
    union_find = _UnionFind()
    for claim in claims:
        query_node = f"q:{claim.id}"
        for document_id in claim.evidence:
            union_find.union(query_node, f"d:{document_id}")

    members: dict[str, dict[str, Any]] = defaultdict(lambda: {"claims": [], "documents": set()})
    for claim in claims:
        root = union_find.find(f"q:{claim.id}")
        members[root]["claims"].append(claim)
        members[root]["documents"].update(claim.evidence)
    components = [
        _Component(
            claims=tuple(value["claims"]),
            document_ids=frozenset(value["documents"]),
        )
        for value in members.values()
    ]
    return sorted(
        components,
        key=lambda component: (
            -len(component.claims),
            hashlib.sha256(
                ",".join(str(claim.id) for claim in component.claims).encode()
            ).hexdigest(),
        ),
    )


def _assign_splits(
    components: Sequence[_Component],
) -> tuple[dict[str, str], dict[str, str]]:
    query_counts = {split: 0 for split in _SPLIT_NAMES}
    split_by_claim: dict[str, str] = {}
    split_by_document: dict[str, str] = {}
    for index, component in enumerate(components):
        if index < len(_SPLIT_NAMES):
            split = _SPLIT_NAMES[index]
        else:
            split = min(
                _SPLIT_NAMES,
                key=lambda name: (query_counts[name] / _SPLIT_RATIOS[name], name),
            )
        query_counts[split] += len(component.claims)
        for claim in component.claims:
            split_by_claim[str(claim.id)] = split
        for document_id in component.document_ids:
            existing = split_by_document.setdefault(document_id, split)
            if existing != split:
                raise DatasetPreparationError("Evidence document assigned to multiple splits.")
    return split_by_claim, split_by_document


def _split_for_unassigned_doc(document_id: str, seed: int) -> str:
    value = int(hashlib.sha256(f"{seed}:{document_id}".encode()).hexdigest(), 16) / (1 << 256)
    if value < _SPLIT_RATIOS["train"]:
        return "train"
    if value < _SPLIT_RATIOS["train"] + _SPLIT_RATIOS["validation"]:
        return "validation"
    return "test"


def _dedupe_positives(values: Iterable[SciFactPositive]) -> list[SciFactPositive]:
    sentence_ids: dict[tuple[str, Literal["SUPPORT", "CONTRADICT"]], set[int]] = defaultdict(set)
    for item in values:
        sentence_ids[(item.document_id, item.verdict)].update(item.evidence_sentences)
    return [
        SciFactPositive(
            document_id=document_id,
            verdict=verdict,
            evidence_sentences=sorted(indices),
        )
        for (document_id, verdict), indices in sorted(sentence_ids.items())
    ]


def _validate_splits(
    documents: Mapping[str, Sequence[SciFactDocument]],
    examples: Mapping[str, Sequence[SciFactExample]],
) -> None:
    seen_documents: set[str] = set()
    for split in _SPLIT_NAMES:
        document_ids = {item.document_id for item in documents[split]}
        if seen_documents & document_ids:
            raise DatasetPreparationError("Document leakage detected across SciFact splits.")
        seen_documents.update(document_ids)
        for example in examples[split]:
            if example.split != split or any(
                positive.document_id not in document_ids for positive in example.positives
            ):
                raise DatasetPreparationError("Query evidence does not match its document split.")
    if any(not documents[split] or not examples[split] for split in _SPLIT_NAMES):
        raise DatasetPreparationError(
            "All three SciFact splits must contain queries and documents."
        )


def _write_jsonl(path: Path, values: Iterable[BaseModel]) -> None:
    _write_text(path, "".join(value.model_dump_json() + "\n" for value in values))


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    _write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _write_text(path: Path, text: str) -> None:
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
            stream.write(text)
            stream.flush()
        temporary_path.replace(path)
    except OSError as exc:
        raise DatasetPreparationError(f"Could not write dataset file {path}: {exc}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _settings_config(settings: Settings) -> tuple[Path, Path, int, int]:
    return (
        settings.dl_public_archive_path,
        settings.dl_public_data_dir,
        settings.dl_public_max_queries,
        settings.dl_seed,
    )


def main() -> None:
    """Download and prepare SciFact when explicitly requested on the CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="fetch the pinned official archive")
    parser.add_argument("--archive", type=Path, help="existing archive path")
    parser.add_argument("--output", type=Path, help="prepared bundle directory")
    parser.add_argument("--max-queries", type=int, help="maximum labeled claims in the subset")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    default_archive, default_output, default_max, seed = _settings_config(settings)
    archive = args.archive or default_archive
    output = args.output or default_output
    max_queries = args.max_queries if args.max_queries is not None else default_max
    if args.download:
        download_scifact_archive(archive)
    elif not archive.is_file():
        parser.error(f"Archive not found at {archive}; pass --download to fetch the pinned source.")
    prepare_scifact_subset(archive, output, max_queries=max_queries, seed=seed)


if __name__ == "__main__":
    main()
