"""Run and checkpoint the four-system sample-corpus retrieval evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ara.config import Settings, load_settings
from ara.rag.bm25 import BM25Index
from ara.rag.eval import (
    EvaluationError,
    EvaluationMetrics,
    EvaluationQuestion,
    Prediction,
    compare_runs,
    load_evaluation_set,
)
from ara.rag.retriever import fuse_ranked_results

logger = logging.getLogger(__name__)

SYSTEMS = ("Dense", "BM25", "Hybrid RRF", "Hybrid RRF + reranker")
_CHECKPOINT_VERSION = 1


@dataclass(frozen=True)
class RetrievalEvaluationResult:
    """Paths and measured metrics from one completed retrieval evaluation."""

    metrics: Mapping[str, EvaluationMetrics]
    predictions_path: Path
    metrics_path: Path
    table_path: Path
    resumed_queries: int
    total_queries: int


def run_retrieval_evaluation(
    settings: Settings | None = None,
    *,
    evaluation_path: Path | str | None = None,
    output_dir: Path | str | None = None,
    candidate_k: int = 20,
    k: int = 5,
    resume: bool = True,
) -> RetrievalEvaluationResult:
    """Measure dense, BM25, RRF, and RRF-plus-cross-encoder retrieval.

    Each completed query is persisted before the next one starts, so interrupted
    model or service calls can be resumed without repeating successful queries.
    """
    if candidate_k < k or k < 1:
        raise ValueError("candidate_k must be greater than or equal to positive k")
    resolved = settings or load_settings()
    questions_path = Path(evaluation_path or resolved.data_dir / "eval_sets/rag_eval.jsonl")
    destination = Path(output_dir or resolved.output_dir / "rag_retrieval_evaluation")
    questions = load_evaluation_set(questions_path)

    from ara.dl.model import CrossEncoderScorer, available_device, load_pair_tokenizer
    from ara.rag.embeddings import OllamaEmbeddings
    from ara.rag.reranker import CrossEncoderReranker
    from ara.rag.vectorstore import ChromaVectorStore

    vector_store = ChromaVectorStore(resolved.vector_store_dir)
    lexical_index = BM25Index.load(resolved.bm25_index_path)
    vector_ids = vector_store.ids()
    if not vector_ids or set(vector_ids) != set(lexical_index.chunk_ids):
        raise EvaluationError("Dense and BM25 indexes are empty or contain different chunk IDs.")

    device = available_device()
    model = CrossEncoderScorer.from_pretrained(resolved, credibility_head=False)
    tokenizer = load_pair_tokenizer(resolved)
    predictor = _TransformersPredictor(
        model,
        tokenizer,
        device=device,
        max_length=resolved.dl_max_length,
    )
    reranker = CrossEncoderReranker(
        resolved.reranker_model,
        device=str(device),
        batch_size=resolved.dl_eval_batch_size,
        model=predictor,
    )
    metadata = {
        "format_version": _CHECKPOINT_VERSION,
        "evaluation_set_sha256": _sha256_file(questions_path),
        "question_count": len(questions),
        "corpus_chunk_count": len(vector_ids),
        "corpus_ids_sha256": _sha256_text("\n".join(sorted(vector_ids))),
        "bm25_index_sha256": _sha256_file(resolved.bm25_index_path),
        "embedding_model": resolved.embedding_model,
        "reranker_model": resolved.reranker_model,
        "reranker_revision": resolved.dl_model_revision,
        "device": str(device),
        "candidate_k": candidate_k,
        "metric_k": k,
        "systems": list(SYSTEMS),
    }

    with OllamaEmbeddings(resolved) as embedder:

        def retrieve(question: EvaluationQuestion) -> Mapping[str, Sequence[str]]:
            query_vector = embedder.embed_query(question.question)
            dense = vector_store.search(query_vector, top_k=candidate_k)
            bm25 = lexical_index.search(question.question, top_k=candidate_k)
            hybrid = fuse_ranked_results(dense, bm25, top_k=candidate_k)
            reranked = reranker.rerank(question.question, hybrid, top_k=candidate_k)
            return {
                "Dense": [result.chunk.chunk_id for result in dense],
                "BM25": [result.chunk.chunk_id for result in bm25],
                "Hybrid RRF": [result.chunk.chunk_id for result in hybrid],
                "Hybrid RRF + reranker": [result.chunk.chunk_id for result in reranked],
            }

        return run_resumable_evaluation(
            questions,
            retrieve,
            output_dir=destination,
            metadata=metadata,
            candidate_k=candidate_k,
            k=k,
            resume=resume,
        )


def run_resumable_evaluation(
    questions: Sequence[EvaluationQuestion],
    retrieve: Callable[[EvaluationQuestion], Mapping[str, Sequence[str]]],
    *,
    output_dir: Path | str,
    metadata: Mapping[str, Any],
    candidate_k: int,
    k: int,
    resume: bool = True,
) -> RetrievalEvaluationResult:
    """Run an injected per-question evaluator with strict checkpoint validation."""
    if not questions:
        raise ValueError("questions must not be empty")
    if candidate_k < k or k < 1:
        raise ValueError("candidate_k must be greater than or equal to positive k")
    if len({question.question_id for question in questions}) != len(questions):
        raise ValueError("question IDs must be unique")

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    metadata_path = destination / "metadata.json"
    predictions_path = destination / "predictions.jsonl"
    metrics_path = destination / "metrics.json"
    table_path = destination / "metrics.md"
    expected_metadata = {**metadata, "candidate_k": candidate_k, "metric_k": k}
    completed: dict[str, dict[str, list[str]]] = {}

    if resume:
        if predictions_path.exists() and not metadata_path.exists():
            raise EvaluationError(
                "Checkpoint predictions exist without metadata; rerun with --fresh."
            )
        if metadata_path.exists():
            try:
                stored_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise EvaluationError(f"Could not read evaluation metadata: {exc}") from exc
            if stored_metadata != expected_metadata:
                raise EvaluationError("Evaluation settings changed; rerun with --fresh to restart.")
            completed = _load_checkpoint(
                predictions_path, questions, candidate_k=candidate_k
            )
    else:
        _write_json_atomically(metadata_path, expected_metadata)
        _write_jsonl_atomically(predictions_path, [])
        metrics_path.unlink(missing_ok=True)
        table_path.unlink(missing_ok=True)

    if not metadata_path.exists():
        _write_json_atomically(metadata_path, expected_metadata)
    question_ids = {question.question_id for question in questions}
    if set(completed) - question_ids:
        raise EvaluationError("Checkpoint contains questions outside the current evaluation set.")

    resumed_queries = len(completed)
    for question in questions:
        if question.question_id in completed:
            continue
        raw_rankings = retrieve(question)
        if set(raw_rankings) != set(SYSTEMS):
            raise EvaluationError(
                "Each query must return rankings for all four configured systems."
            )
        rankings = {
            name: _validate_ranking(raw_rankings[name], candidate_k=candidate_k)
            for name in SYSTEMS
        }
        completed[question.question_id] = rankings
        _write_jsonl_atomically(
            predictions_path,
            [
                {"id": item.question_id, "rankings": completed[item.question_id]}
                for item in questions
                if item.question_id in completed
            ],
        )
        logger.info(
            "Evaluated query %d/%d (%s)",
            len(completed),
            len(questions),
            question.question_id,
        )

    predictions = {
        system: {
            question.question_id: Prediction(
                ranked_chunk_ids=tuple(completed[question.question_id][system]),
                cited_chunk_ids=tuple(completed[question.question_id][system][:k]),
            )
            for question in questions
        }
        for system in SYSTEMS
    }
    metrics = compare_runs(questions, predictions, k=k)
    _write_json_atomically(
        metrics_path,
        {
            "metadata": expected_metadata,
            "systems": {
                name: {
                    "question_count": value.question_count,
                    "answerable_count": value.answerable_count,
                    "unanswerable_count": value.unanswerable_count,
                    "k": value.cutoff,
                    "recall_at_k": value.recall_at_k,
                    "mrr": value.mrr,
                    "ndcg_at_k": value.ndcg_at_k,
                    "citation_precision_at_k": value.citation_precision,
                }
                for name, value in metrics.items()
            },
        },
    )
    _write_text_atomically(table_path, _render_table(metrics, metadata=expected_metadata))
    return RetrievalEvaluationResult(
        metrics=metrics,
        predictions_path=predictions_path,
        metrics_path=metrics_path,
        table_path=table_path,
        resumed_queries=resumed_queries,
        total_queries=len(questions),
    )


class _TransformersPredictor:
    """Adapt ARA's pinned Transformers cross-encoder to the reranker interface."""

    def __init__(self, model: Any, tokenizer: Any, *, device: Any, max_length: int) -> None:
        self.model = model.to(device).eval()
        self.tokenizer = tokenizer
        self.device = device
        self.max_length = max_length

    def predict(
        self,
        sentences: Sequence[tuple[str, str]],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> list[float]:
        """Score query/passage pairs in bounded inference batches."""
        del show_progress_bar
        import torch

        scores: list[float] = []
        with torch.inference_mode():
            for offset in range(0, len(sentences), batch_size):
                batch = sentences[offset : offset + batch_size]
                encoded = self.tokenizer(
                    [query for query, _ in batch],
                    [passage for _, passage in batch],
                    padding=True,
                    truncation=True,
                    max_length=self.max_length,
                    return_tensors="pt",
                )
                inputs = {name: tensor.to(self.device) for name, tensor in encoded.items()}
                output = self.model(**inputs)
                scores.extend(float(value) for value in output.relevance_logits.cpu().tolist())
        return scores


def _load_checkpoint(
    path: Path,
    questions: Sequence[EvaluationQuestion],
    *,
    candidate_k: int,
) -> dict[str, dict[str, list[str]]]:
    """Read and validate one completed ranking record per query."""
    if not path.exists():
        return {}
    expected_ids = {question.question_id for question in questions}
    results: dict[str, dict[str, list[str]]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            record = json.loads(line)
            question_id = record["id"]
            rankings = record["rankings"]
            if question_id not in expected_ids or question_id in results:
                raise ValueError(f"invalid or duplicate question ID on line {line_number}")
            if not isinstance(rankings, dict) or set(rankings) != set(SYSTEMS):
                raise ValueError(f"invalid system rankings on line {line_number}")
            results[question_id] = {
                name: _validate_ranking(rankings[name], candidate_k=candidate_k)
                for name in SYSTEMS
            }
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise EvaluationError(f"Could not load retrieval checkpoint {path}: {exc}") from exc
    return results


def _validate_ranking(ranking: Sequence[str], *, candidate_k: int) -> list[str]:
    if isinstance(ranking, (str, bytes)) or not isinstance(ranking, Sequence):
        raise EvaluationError("rankings must be sequences of chunk ID strings")
    values = list(ranking)
    if len(values) > candidate_k or any(
        not isinstance(value, str) or not value for value in values
    ):
        raise EvaluationError("ranking contains invalid IDs or exceeds candidate_k")
    if len(set(values)) != len(values):
        raise EvaluationError("ranking chunk IDs must be unique")
    return values


def _render_table(
    metrics: Mapping[str, EvaluationMetrics], *, metadata: Mapping[str, Any]
) -> str:
    k = int(metadata["metric_k"])
    question_count = metadata.get("question_count", metrics[SYSTEMS[0]].question_count)
    chunk_count = metadata.get("corpus_chunk_count", "unknown")
    embedding_model = metadata.get("embedding_model", "unknown")
    reranker_model = metadata.get("reranker_model", "unknown")
    reranker_revision = metadata.get("reranker_revision", "unknown")
    device = metadata.get("device", "unknown")
    lines = [
        "# Sample-corpus retrieval evaluation",
        "",
        f"Queries: {question_count} | Chunks: {chunk_count}",
        f"Candidate depth: {metadata['candidate_k']} | Metrics cutoff: {k}",
        f"Embedding model: `{embedding_model}`",
        f"Reranker: `{reranker_model}` at `{reranker_revision}`",
        f"Device: `{device}`",
        "",
        "Citation precision@k treats the top-k retrieved chunk IDs as candidate citations and "
        "compares them with gold chunk IDs; no LLM answer generation is included.",
        "",
        f"| System | Recall@{k} | MRR | nDCG@{k} | Citation precision@{k} |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in SYSTEMS:
        value = metrics[name]
        lines.append(
            f"| {name} | {value.recall_at_k:.3f} | {value.mrr:.3f} | "
            f"{value.ndcg_at_k:.3f} | {value.citation_precision:.3f} |"
        )
    return "\n".join(lines) + "\n"


def _write_jsonl_atomically(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    content = "".join(
        json.dumps(record, ensure_ascii=False) + "\n" for record in records
    )
    _write_text_atomically(path, content)


def _write_json_atomically(path: Path, payload: Mapping[str, Any]) -> None:
    _write_text_atomically(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _write_text_atomically(path: Path, content: str) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f"{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except OSError as exc:
        raise EvaluationError(f"Could not write evaluation artifact {path}: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _sha256_file(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for running or resuming the fixed RAG evaluation set."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-set", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--fresh", action="store_true", help="discard prior query checkpoints")
    args = parser.parse_args(argv)
    result = run_retrieval_evaluation(
        evaluation_path=args.evaluation_set,
        output_dir=args.output_dir,
        candidate_k=args.candidate_k,
        k=args.k,
        resume=not args.fresh,
    )
    logger.info(
        "Retrieval evaluation complete: queries=%d resumed=%d metrics=%s",
        result.total_queries,
        result.resumed_queries,
        result.table_path,
    )
    return 0


__all__ = [
    "RetrievalEvaluationResult",
    "run_resumable_evaluation",
    "run_retrieval_evaluation",
]
