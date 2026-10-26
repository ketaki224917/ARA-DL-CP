"""Held-out SciFact comparison for dense, generic, and fine-tuned rerankers."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch
from torch import Tensor, nn
from torch.utils.data import DataLoader

from ara.config import Settings, load_settings
from ara.dl.dataset import PairBatch, PairCollator, PairExample
from ara.dl.dense import HuggingFaceDenseEncoder
from ara.dl.model import (
    CrossEncoderScorer,
    available_device,
    load_pair_tokenizer,
)
from ara.dl.public_data import SciFactDocument, SciFactExample
from ara.dl.train import train_model
from ara.logging_setup import configure_logging
from ara.rag.bm25 import BM25Index
from ara.rag.chunking import DocumentChunk

logger = logging.getLogger(__name__)
_RRF_CONSTANT = 60
_CACHE_FORMAT_VERSION = 1


@dataclass(frozen=True)
class TestQuery:
    """One held-out query and its annotated relevant document IDs."""

    query_id: str
    text: str
    relevant_document_ids: frozenset[str]


@dataclass(frozen=True)
class EvaluationMetrics:
    """Macro ranking metrics averaged over the held-out query set."""

    system: str
    recall_at_10: float
    mrr: float
    ndcg_at_10: float
    query_count: int


@dataclass(frozen=True)
class EvaluationResult:
    """Ranking comparisons, candidate coverage, and persisted artifact paths."""

    metrics: tuple[EvaluationMetrics, ...]
    candidate_recall_at_20: float
    mean_candidate_count: float
    error_case_count: int
    metrics_path: Path
    table_path: Path
    error_analysis_path: Path


def evaluate_models(
    settings: Settings | None = None,
    *,
    data_dir: Path | str | None = None,
    candidate_k: int | None = None,
    generic_model: nn.Module | None = None,
    trained_model: nn.Module | None = None,
    random_negative_model: nn.Module | None = None,
    tokenizer: Any | None = None,
    dense_encoder: Any | None = None,
    include_random_negative_ablation: bool = True,
) -> EvaluationResult:
    """Compare RRF retrieval, the generic cross-encoder, and trained checkpoints.

    Only the test split is read for ranking metrics. When enabled, the no-hard-negative
    ablation is trained through `train_model` using train/validation only before the
    test query bundle is loaded.
    """
    resolved = settings or load_settings()
    root = Path(data_dir) if data_dir is not None else resolved.dl_public_data_dir
    retrieve_k = candidate_k if candidate_k is not None else resolved.dl_eval_candidate_k
    if retrieve_k < 1:
        raise ValueError("candidate_k must be positive")

    ablation_settings: Settings | None = None
    if include_random_negative_ablation and random_negative_model is None:
        ablation_settings = resolved.model_copy(
            update={
                "dl_checkpoint_path": resolved.dl_random_negative_checkpoint_path,
                "dl_metrics_path": _with_suffix(
                    resolved.dl_metrics_path, "_random_negatives"
                ),
                "dl_curves_path": _with_suffix(
                    resolved.dl_curves_path, "_random_negatives"
                ),
            }
        )
        train_model(
            ablation_settings,
            data_dir=root,
            include_synthetic_pairs=resolved.dl_use_synthetic_pairs,
            negative_strategy="random",
        )

    queries, documents = _load_test_bundle(root)
    document_by_id = {document.document_id: document for document in documents}
    chunks = [
        DocumentChunk(
            chunk_id=f"scifact:{document.document_id}",
            text=document.text,
            source=f"scifact:{document.document_id}",
            page=None,
            char_start=0,
            char_end=len(document.text),
        )
        for document in documents
    ]
    bm25 = BM25Index(chunks)
    encoder = dense_encoder or HuggingFaceDenseEncoder.from_settings(resolved)
    doc_embeddings = _load_or_encode_documents(documents, encoder, resolved)
    query_embeddings = encoder.encode([query.text for query in queries])
    rrf_rankings: dict[str, list[str]] = {}
    for row, query_embedding in zip(queries, query_embeddings, strict=True):
        dense_scores = torch.mv(doc_embeddings, query_embedding)
        dense_indices = torch.argsort(dense_scores, descending=True, stable=True)[
            :retrieve_k
        ].tolist()
        dense_ids = [documents[index].document_id for index in dense_indices]
        bm25_ids = [
            result.chunk.chunk_id.removeprefix("scifact:")
            for result in bm25.search(row.text, top_k=retrieve_k)
        ]
        rrf_rankings[row.query_id] = reciprocal_rank_fusion(bm25_ids, dense_ids)

    generic = generic_model or CrossEncoderScorer.from_pretrained(resolved)
    trained = trained_model or _load_checkpoint_model(resolved, resolved.dl_checkpoint_path)
    pair_tokenizer = tokenizer or load_pair_tokenizer(resolved)
    device = available_device()
    generic_scores = _score_candidates(
        generic,
        pair_tokenizer,
        queries,
        rrf_rankings,
        document_by_id,
        device=device,
        batch_size=resolved.dl_eval_batch_size,
        max_length=resolved.dl_max_length,
    )
    trained_scores = _score_candidates(
        trained,
        pair_tokenizer,
        queries,
        rrf_rankings,
        document_by_id,
        device=device,
        batch_size=resolved.dl_eval_batch_size,
        max_length=resolved.dl_max_length,
    )
    ranked: dict[str, dict[str, list[str]]] = {
        "BM25+dense RRF (no reranker)": rrf_rankings,
        "Generic MS MARCO cross-encoder": _rank_scores(generic_scores),
        "Fine-tuned cross-encoder": _rank_scores(trained_scores),
    }
    if include_random_negative_ablation:
        ablation = random_negative_model
        if ablation is None:
            ablation = _load_checkpoint_model(
                resolved, resolved.dl_random_negative_checkpoint_path
            )
        ablation_scores = _score_candidates(
            ablation,
            pair_tokenizer,
            queries,
            rrf_rankings,
            document_by_id,
            device=device,
            batch_size=resolved.dl_eval_batch_size,
            max_length=resolved.dl_max_length,
        )
        ranked["Random-negative ablation"] = _rank_scores(ablation_scores)

    metrics = tuple(
        _evaluate_rankings(name, queries, rankings)
        for name, rankings in ranked.items()
    )
    candidate_recall = _macro_candidate_recall(queries, rrf_rankings, cutoff=20)
    mean_candidate_count = sum(map(len, rrf_rankings.values())) / len(queries)
    errors = build_error_cases(
        queries,
        rrf_rankings,
        _rank_scores(trained_scores),
        trained_scores,
        document_by_id,
        limit=20,
    )
    result = EvaluationResult(
        metrics=metrics,
        candidate_recall_at_20=candidate_recall,
        mean_candidate_count=mean_candidate_count,
        error_case_count=len(errors),
        metrics_path=resolved.dl_eval_metrics_path,
        table_path=resolved.dl_eval_metrics_path.with_suffix(".md"),
        error_analysis_path=resolved.dl_error_analysis_path,
    )
    _write_json(result.metrics_path, _result_payload(result, resolved, retrieve_k))
    _write_text(result.table_path, _render_table(result, retrieve_k))
    _write_json(
        result.error_analysis_path,
        {
            "dataset": "SciFact internal held-out test split",
            "selection": (
                "up to 20 queries where the fine-tuned system did not rank "
                "a gold document first"
            ),
            "cases": errors,
        },
    )
    logger.info(
        "Evaluation complete: %d queries; candidate recall@20=%.4f; wrote %d error cases",
        len(queries),
        candidate_recall,
        len(errors),
    )
    return result


def reciprocal_rank_fusion(
    bm25_document_ids: Sequence[str],
    dense_document_ids: Sequence[str],
    *,
    constant: int = _RRF_CONSTANT,
) -> list[str]:
    """Fuse two ranked lists with deterministic reciprocal-rank fusion."""
    if constant < 1:
        raise ValueError("RRF constant must be positive")
    scores: dict[str, float] = {}
    for document_ids in (bm25_document_ids, dense_document_ids):
        for rank, document_id in enumerate(document_ids, start=1):
            scores[document_id] = scores.get(document_id, 0.0) + 1 / (constant + rank)
    return sorted(scores, key=lambda document_id: (-scores[document_id], document_id))


def evaluate_rankings(
    queries: Sequence[TestQuery],
    rankings: Mapping[str, Sequence[str]],
    *,
    system_name: str,
    cutoff: int = 10,
) -> EvaluationMetrics:
    """Compute macro recall@k, MRR, and binary nDCG@k over query rankings."""
    if cutoff < 1:
        raise ValueError("cutoff must be positive")
    if not queries:
        raise ValueError("cannot evaluate an empty query set")
    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    ndcgs: list[float] = []
    for query in queries:
        relevant = query.relevant_document_ids
        ranked_ids = list(rankings.get(query.query_id, ()))
        top_ids = ranked_ids[:cutoff]
        recalls.append(len(set(top_ids) & relevant) / len(relevant))
        first_rank = next(
            (
                index
                for index, document_id in enumerate(ranked_ids, start=1)
                if document_id in relevant
            ),
            None,
        )
        reciprocal_ranks.append(1.0 / first_rank if first_rank is not None else 0.0)
        dcg = sum(
            1.0 / math.log2(index + 2)
            for index, document_id in enumerate(top_ids)
            if document_id in relevant
        )
        ideal_count = min(len(relevant), cutoff)
        ideal_dcg = sum(1.0 / math.log2(index + 2) for index in range(ideal_count))
        ndcgs.append(dcg / ideal_dcg if ideal_dcg else 0.0)
    return EvaluationMetrics(
        system=system_name,
        recall_at_10=sum(recalls) / len(recalls),
        mrr=sum(reciprocal_ranks) / len(reciprocal_ranks),
        ndcg_at_10=sum(ndcgs) / len(ndcgs),
        query_count=len(queries),
    )


def build_error_cases(
    queries: Sequence[TestQuery],
    candidate_rankings: Mapping[str, Sequence[str]],
    trained_rankings: Mapping[str, Sequence[str]],
    trained_scores: Mapping[str, Mapping[str, float]],
    documents: Mapping[str, SciFactDocument],
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Select the worst top-rank misses and include the ranked evidence for review."""
    if limit < 1:
        raise ValueError("limit must be positive")
    failures: list[tuple[int, int | None, str, TestQuery]] = []
    for query in queries:
        ranking = list(trained_rankings.get(query.query_id, ()))
        first_relevant = next(
            (
                index
                for index, document_id in enumerate(ranking, start=1)
                if document_id in query.relevant_document_ids
            ),
            None,
        )
        top_relevant_count = len(
            set(ranking[:10]) & query.relevant_document_ids
        )
        misses_gold = top_relevant_count < len(query.relevant_document_ids)
        if first_relevant != 1 or misses_gold:
            severity = first_relevant if first_relevant is not None else len(ranking) + 1
            failures.append((severity, first_relevant, query.query_id, query))
    failures.sort(key=lambda item: (-item[0], item[2]))
    cases: list[dict[str, Any]] = []
    for _, first_rank, _, query in failures[:limit]:
        candidate_ids = list(candidate_rankings.get(query.query_id, ()))
        ranked_ids = list(trained_rankings.get(query.query_id, ()))
        cases.append(
            {
                "query_id": query.query_id,
                "query": query.text,
                "gold_document_ids": sorted(query.relevant_document_ids),
                "candidate_recall": len(
                    set(candidate_ids) & query.relevant_document_ids
                )
                / len(query.relevant_document_ids),
                "first_relevant_rank": first_rank,
                "failure_type": (
                    "gold_not_retrieved"
                    if first_rank is None
                    else (
                        "gold_not_ranked_first"
                        if first_rank > 1
                        else "gold_recall_below_1_at_10"
                    )
                ),
                "top_five": [
                    {
                        "document_id": document_id,
                        "relevance_score": trained_scores[query.query_id].get(document_id),
                        "text": documents[document_id].text[:500],
                        "is_relevant": document_id in query.relevant_document_ids,
                    }
                    for document_id in ranked_ids[:5]
                ],
            }
        )
    return cases


def _load_test_bundle(root: Path) -> tuple[list[TestQuery], list[SciFactDocument]]:
    query_path = root / "queries_test.jsonl"
    corpus_path = root / "corpus_test.jsonl"
    queries = [
        TestQuery(
            query_id=row.query_id,
            text=row.query,
            relevant_document_ids=frozenset(item.document_id for item in row.positives),
        )
        for row in _load_jsonl(query_path, SciFactExample)
    ]
    documents = sorted(
        _load_jsonl(corpus_path, SciFactDocument), key=lambda document: document.document_id
    )
    document_ids = {document.document_id for document in documents}
    if any(not query.relevant_document_ids.issubset(document_ids) for query in queries):
        raise ValueError("test query evidence refers to a document outside the test corpus")
    if not queries or not documents:
        raise ValueError("held-out test split must contain queries and documents")
    return queries, documents


def _load_jsonl(path: Path, schema: type[Any]) -> list[Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required evaluation data is missing: {path}")
    rows: list[Any] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            rows.append(schema.model_validate_json(line))
        except ValueError as exc:
            raise ValueError(f"Invalid evaluation record at {path}:{line_number}: {exc}") from exc
    return rows


def _load_or_encode_documents(
    documents: Sequence[SciFactDocument],
    encoder: Any,
    settings: Settings,
) -> Tensor:
    fingerprint = _documents_fingerprint(documents)
    path = settings.dl_dense_embeddings_cache_path
    if path.is_file():
        try:
            cached = torch.load(path, map_location="cpu", weights_only=True)
            if (
                isinstance(cached, dict)
                and cached.get("format_version") == _CACHE_FORMAT_VERSION
                and cached.get("model") == settings.dl_dense_model
                and cached.get("revision") == settings.dl_dense_model_revision
                and cached.get("corpus_fingerprint") == fingerprint
                and isinstance(cached.get("embeddings"), Tensor)
                and cached["embeddings"].shape[0] == len(documents)
            ):
                return cached["embeddings"]
            logger.info("Ignoring stale dense test embedding cache at %s", path)
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            logger.warning("Could not read dense embedding cache at %s: %s", path, exc)
    embeddings = encoder.encode([document.text for document in documents]).detach().cpu()
    if embeddings.shape[0] != len(documents):
        raise ValueError("dense encoder returned a different number of embeddings than documents")
    payload = {
        "format_version": _CACHE_FORMAT_VERSION,
        "model": settings.dl_dense_model,
        "revision": settings.dl_dense_model_revision,
        "corpus_fingerprint": fingerprint,
        "embeddings": embeddings,
    }
    _atomic_torch_save(path, payload)
    return embeddings


def _documents_fingerprint(documents: Sequence[SciFactDocument]) -> str:
    digest = hashlib.sha256()
    for document in documents:
        digest.update(document.document_id.encode("utf-8"))
        digest.update(b"\0")
        digest.update(document.text.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _score_candidates(
    model: nn.Module,
    tokenizer: Any,
    queries: Sequence[TestQuery],
    candidates: Mapping[str, Sequence[str]],
    documents: Mapping[str, SciFactDocument],
    *,
    device: torch.device,
    batch_size: int,
    max_length: int,
) -> dict[str, dict[str, float]]:
    examples: list[PairExample] = []
    pair_ids: list[tuple[str, str]] = []
    query_by_id = {query.query_id: query for query in queries}
    for query_id, document_ids in candidates.items():
        query = query_by_id[query_id]
        for document_id in document_ids:
            examples.append(
                PairExample(
                    query_id=query_id,
                    query=query.text,
                    document_id=document_id,
                    passage=documents[document_id].text,
                    relevance_label=0.0,
                    split="test",
                    source="scifact",
                )
            )
            pair_ids.append((query_id, document_id))
    loader = DataLoader(
        examples,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        collate_fn=PairCollator(tokenizer, max_length=max_length),
    )
    model.to(device)
    model.eval()
    logits: list[float] = []
    with torch.inference_mode():
        for batch in loader:
            if not isinstance(batch, PairBatch):
                raise TypeError("evaluation DataLoader returned an unexpected batch type")
            model_inputs = {name: value.to(device) for name, value in batch.model_inputs.items()}
            output = model(**model_inputs)
            logits.extend(float(value) for value in output.relevance_logits.cpu().tolist())
    if len(logits) != len(pair_ids):
        raise RuntimeError("reranker returned a different number of scores than candidate pairs")
    scores: dict[str, dict[str, float]] = {query.query_id: {} for query in queries}
    for (query_id, document_id), score in zip(pair_ids, logits, strict=True):
        scores[query_id][document_id] = score
    return scores


def _rank_scores(scores: Mapping[str, Mapping[str, float]]) -> dict[str, list[str]]:
    return {
        query_id: sorted(
            document_scores,
            key=lambda document_id: (-document_scores[document_id], document_id),
        )
        for query_id, document_scores in scores.items()
    }


def _evaluate_rankings(
    system_name: str,
    queries: Sequence[TestQuery],
    rankings: Mapping[str, Sequence[str]],
) -> EvaluationMetrics:
    return evaluate_rankings(queries, rankings, system_name=system_name, cutoff=10)


def _macro_candidate_recall(
    queries: Sequence[TestQuery],
    candidates: Mapping[str, Sequence[str]],
    *,
    cutoff: int,
) -> float:
    recalls = [
        len(set(candidates.get(query.query_id, ())[:cutoff]) & query.relevant_document_ids)
        / len(query.relevant_document_ids)
        for query in queries
    ]
    return sum(recalls) / len(recalls)


def _result_payload(
    result: EvaluationResult,
    settings: Settings,
    candidate_k: int,
) -> dict[str, Any]:
    return {
        "dataset": "SciFact internal held-out test split",
        "test_split_is_official": False,
        "dense_model": settings.dl_dense_model,
        "dense_model_revision": settings.dl_dense_model_revision,
        "cross_encoder_model": settings.reranker_model,
        "cross_encoder_revision": settings.dl_model_revision,
        "candidate_k_per_retriever": candidate_k,
        "candidate_recall_at_20": result.candidate_recall_at_20,
        "mean_rrf_candidate_count": result.mean_candidate_count,
        "metrics": [asdict(row) for row in result.metrics],
        "error_case_count": result.error_case_count,
        "error_analysis_path": str(result.error_analysis_path),
    }


def _render_table(result: EvaluationResult, candidate_k: int) -> str:
    lines = [
        "# P5.5 Reranker Evaluation",
        "",
        "SciFact internal held-out test partition; this is not the original official test set.",
        "Gold relevance includes both SUPPORT and CONTRADICT evidence documents.",
        (
            f"BM25+dense RRF candidate depth: top {candidate_k} from each retriever; "
            f"candidate recall@20: {result.candidate_recall_at_20:.4f}; "
            f"mean union size: {result.mean_candidate_count:.2f}."
        ),
        "",
        "| System | Recall@10 | MRR | nDCG@10 | Queries |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in result.metrics:
        lines.append(
            f"| {row.system} | {row.recall_at_10:.4f} | {row.mrr:.4f} | "
            f"{row.ndcg_at_10:.4f} | {row.query_count} |"
        )
    lines.extend(
        [
            "",
            "Failure review cases saved: "
            f"{result.error_case_count}. See `{result.error_analysis_path}`.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    _write_atomic_text(path, serialized)


def _write_text(path: Path, text: str) -> None:
    _write_atomic_text(path, text)


def _write_atomic_text(path: Path, text: str) -> None:
    temporary_path = _temporary_path(path)
    try:
        temporary_path.write_text(text, encoding="utf-8")
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _atomic_torch_save(path: Path, payload: Mapping[str, Any]) -> None:
    temporary_path = _temporary_path(path)
    try:
        torch.save(dict(payload), temporary_path)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _temporary_path(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=destination.parent,
        prefix=f"{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        return Path(stream.name)


def _load_checkpoint_model(settings: Settings, checkpoint_path: Path) -> CrossEncoderScorer:
    if not checkpoint_path.is_file():
        raise FileNotFoundError(
            f"Cross-encoder checkpoint not found at {checkpoint_path}; "
            "train it with ara.dl.train first."
        )
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if not isinstance(payload, dict):
        raise ValueError(f"Checkpoint payload is not a mapping: {checkpoint_path}")
    if payload.get("format_version") != 1 or not isinstance(payload.get("model_state_dict"), dict):
        raise ValueError(f"Unsupported or malformed cross-encoder checkpoint: {checkpoint_path}")
    if payload.get("model_name") != settings.reranker_model:
        raise ValueError("checkpoint model name does not match the configured reranker")
    if payload.get("model_revision") != settings.dl_model_revision:
        raise ValueError("checkpoint revision does not match the configured reranker")
    model = CrossEncoderScorer.from_pretrained(settings)
    model.load_state_dict(payload["model_state_dict"])
    return model


def _with_suffix(path: Path, suffix: str) -> Path:
    return path.with_name(f"{path.stem}{suffix}{path.suffix}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the held-out comparison and, by default, train the random-negative ablation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, help="prepared SciFact split directory")
    parser.add_argument("--candidate-k", type=int, help="top candidates per dense/BM25 retriever")
    parser.add_argument(
        "--no-random-negative-ablation",
        action="store_true",
        help="skip training and comparing the no-hard-negative ablation",
    )
    args = parser.parse_args(argv)
    configure_logging()
    result = evaluate_models(
        data_dir=args.data_dir,
        candidate_k=args.candidate_k,
        include_random_negative_ablation=not args.no_random_negative_ablation,
    )
    logger.info("Saved evaluation table to %s", result.table_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
