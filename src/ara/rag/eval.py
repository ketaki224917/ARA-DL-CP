"""Load retrieval labels, score retriever runs, and format comparison reports."""

from __future__ import annotations

import json
import logging
import math
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EvaluationError(RuntimeError):
    """Raised when an evaluation set or result file is malformed."""


@dataclass(frozen=True)
class EvaluationQuestion:
    """One labeled query and its answerability and gold passage IDs."""

    question_id: str
    category: str
    question: str
    expected_answer: str | None
    answerable: bool
    gold_chunk_ids: tuple[str, ...]


@dataclass(frozen=True)
class Prediction:
    """One retriever/answerer result for an evaluation question."""

    ranked_chunk_ids: tuple[str, ...] = ()
    cited_chunk_ids: tuple[str, ...] = ()
    abstained: bool = False


@dataclass(frozen=True)
class EvaluationMetrics:
    """Aggregate retrieval and citation metrics for one system run."""

    question_count: int
    answerable_count: int
    unanswerable_count: int
    cutoff: int
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    citation_precision: float
    answerable_response_rate: float
    unanswerable_abstention_rate: float


def load_evaluation_set(path: Path | str) -> list[EvaluationQuestion]:
    """Read and validate the project's JSONL evaluation set."""
    source = Path(path)
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise EvaluationError(f"Could not read evaluation set {source}: {exc}") from exc
    questions: list[EvaluationQuestion] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            question = _question_from_record(record)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise EvaluationError(
                f"Invalid evaluation record at {source}:{line_number}: {exc}"
            ) from exc
        if question.question_id in seen_ids:
            raise EvaluationError(f"Duplicate evaluation ID {question.question_id!r}.")
        seen_ids.add(question.question_id)
        questions.append(question)
    if not questions:
        raise EvaluationError(f"Evaluation set {source} contains no records.")
    return questions


def evaluate_predictions(
    questions: Sequence[EvaluationQuestion],
    predictions: Mapping[str, Prediction],
    *,
    k: int = 5,
) -> EvaluationMetrics:
    """Compute retrieval metrics on answerable questions and citation metrics overall.

    Recall@k is the fraction of each query's gold IDs present in the first `k`.
    MRR uses the first relevant ID anywhere in the returned ranking. nDCG@k uses
    binary relevance. Citation precision is micro-averaged across all emitted
    citations, counting any citation on an unanswerable query as incorrect. Missing
    predictions count as empty rankings, no citations, and no abstention.
    """
    if type(k) is not int or k < 1:
        raise ValueError("k must be at least 1")
    if not questions:
        raise ValueError("questions must not be empty")
    if len({question.question_id for question in questions}) != len(questions):
        raise ValueError("evaluation question IDs must be unique")
    for question in questions:
        if question.answerable != bool(question.gold_chunk_ids):
            raise ValueError("answerable must match whether gold_chunk_ids is non-empty")
        if len(set(question.gold_chunk_ids)) != len(question.gold_chunk_ids):
            raise ValueError("gold_chunk_ids must be unique")
    question_ids = {question.question_id for question in questions}
    extra_ids = set(predictions) - question_ids
    if extra_ids:
        raise ValueError(f"Predictions include unknown question IDs: {sorted(extra_ids)}")

    answerable = [question for question in questions if question.answerable]
    unanswerable = [question for question in questions if not question.answerable]
    recall_values: list[float] = []
    reciprocal_ranks: list[float] = []
    ndcg_values: list[float] = []
    correct_citations = 0
    total_citations = 0
    answered_count = 0
    abstained_unanswerable = 0

    for question in questions:
        prediction = predictions.get(question.question_id, Prediction())
        has_prediction = question.question_id in predictions
        ranked_ids = _unique(prediction.ranked_chunk_ids)
        cited_ids = _unique(prediction.cited_chunk_ids)
        gold_ids = set(question.gold_chunk_ids)
        total_citations += len(cited_ids)
        correct_citations += len(set(cited_ids) & gold_ids)
        if question.answerable:
            if has_prediction and not prediction.abstained:
                answered_count += 1
            recall_values.append(len(set(ranked_ids[:k]) & gold_ids) / len(gold_ids))
            reciprocal_ranks.append(_reciprocal_rank(ranked_ids, gold_ids))
            ndcg_values.append(_ndcg_at_k(ranked_ids, gold_ids, k))
        elif has_prediction and prediction.abstained:
            abstained_unanswerable += 1

    return EvaluationMetrics(
        question_count=len(questions),
        answerable_count=len(answerable),
        unanswerable_count=len(unanswerable),
        cutoff=k,
        recall_at_k=_mean(recall_values),
        mrr=_mean(reciprocal_ranks),
        ndcg_at_k=_mean(ndcg_values),
        citation_precision=correct_citations / total_citations if total_citations else 0.0,
        answerable_response_rate=answered_count / len(answerable) if answerable else 0.0,
        unanswerable_abstention_rate=(
            abstained_unanswerable / len(unanswerable) if unanswerable else 0.0
        ),
    )


def compare_runs(
    questions: Sequence[EvaluationQuestion],
    runs: Mapping[str, Mapping[str, Prediction]],
    *,
    k: int = 5,
) -> dict[str, EvaluationMetrics]:
    """Score named system outputs on the same fixed question set."""
    if not runs:
        raise ValueError("runs must contain at least one system")
    return {
        name: evaluate_predictions(questions, predictions, k=k)
        for name, predictions in sorted(runs.items())
    }


def format_metrics_table(metrics: Mapping[str, EvaluationMetrics]) -> str:
    """Format comparable system summaries as a Markdown table."""
    headers = (
        "System",
        "Recall@k",
        "MRR",
        "nDCG@k",
        "Citation precision",
        "Answer rate",
        "Unanswerable abstention",
    )
    rows = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for name, result in sorted(metrics.items()):
        values = (
            name,
            f"{result.recall_at_k:.3f}",
            f"{result.mrr:.3f}",
            f"{result.ndcg_at_k:.3f}",
            f"{result.citation_precision:.3f}",
            f"{result.answerable_response_rate:.3f}",
            f"{result.unanswerable_abstention_rate:.3f}",
        )
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def save_metrics_json(
    path: Path | str,
    metrics: Mapping[str, EvaluationMetrics],
    *,
    metadata: Mapping[str, Any],
) -> None:
    """Atomically persist metric values with run metadata as JSON."""
    destination = Path(path)
    temporary_path: Path | None = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f"{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(
                {
                    "metadata": dict(metadata),
                    "systems": {name: asdict(result) for name, result in metrics.items()},
                },
                stream,
                ensure_ascii=False,
                indent=2,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(destination)
    except (OSError, TypeError, ValueError) as exc:
        raise EvaluationError(f"Could not save evaluation results to {destination}: {exc}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    logger.info("Saved evaluation metrics for %d systems to %s", len(metrics), destination)


def _question_from_record(record: Any) -> EvaluationQuestion:
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    question_id = record.get("id")
    category = record.get("category")
    question = record.get("question")
    answerable = record.get("answerable")
    gold_ids = record.get("gold_chunk_ids")
    answer = record.get("expected_answer")
    if not all(
        isinstance(value, str) and value.strip()
        for value in (question_id, category, question)
    ):
        raise ValueError("id, category, and question must be non-empty strings")
    if category not in {"factoid", "multi_hop", "unanswerable"}:
        raise ValueError("category must be factoid, multi_hop, or unanswerable")
    if type(answerable) is not bool:
        raise ValueError("answerable must be a boolean")
    if not isinstance(gold_ids, list) or any(
        not isinstance(chunk_id, str) or not chunk_id.strip() for chunk_id in gold_ids
    ):
        raise ValueError("gold_chunk_ids must be a list of non-empty strings")
    if len(set(gold_ids)) != len(gold_ids):
        raise ValueError("gold_chunk_ids must be unique")
    if answerable != bool(gold_ids):
        raise ValueError("answerable must match whether gold_chunk_ids is non-empty")
    if answerable and (not isinstance(answer, str) or not answer.strip()):
        raise ValueError("answerable questions require an expected_answer")
    if not answerable and answer is not None:
        raise ValueError("unanswerable questions must have a null expected_answer")
    return EvaluationQuestion(
        question_id=question_id,
        category=category,
        question=question,
        expected_answer=answer,
        answerable=answerable,
        gold_chunk_ids=tuple(gold_ids),
    )


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _reciprocal_rank(ranked_ids: Sequence[str], gold_ids: set[str]) -> float:
    return next(
        (1.0 / rank for rank, chunk_id in enumerate(ranked_ids, start=1) if chunk_id in gold_ids),
        0.0,
    )


def _ndcg_at_k(ranked_ids: Sequence[str], gold_ids: set[str], k: int) -> float:
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, chunk_id in enumerate(ranked_ids[:k], start=1)
        if chunk_id in gold_ids
    )
    ideal_count = min(len(gold_ids), k)
    ideal_dcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return dcg / ideal_dcg if ideal_dcg else 0.0


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0
