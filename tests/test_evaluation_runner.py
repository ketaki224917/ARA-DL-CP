"""Tests for resumable RAG evaluation checkpoints."""

import json

import pytest

from ara.rag.eval import EvaluationError, EvaluationQuestion
from ara.rag.evaluation_runner import SYSTEMS, run_resumable_evaluation


def _questions() -> list[EvaluationQuestion]:
    return [
        EvaluationQuestion("q1", "factoid", "first", "answer", True, ("chunk:a",)),
        EvaluationQuestion("q2", "unanswerable", "second", None, False, ()),
    ]


def _rankings(question: EvaluationQuestion) -> dict[str, list[str]]:
    if question.question_id == "q1":
        return {
            "Dense": ["chunk:a", "chunk:x"],
            "BM25": ["chunk:x", "chunk:a"],
            "Hybrid RRF": ["chunk:a", "chunk:x"],
            "Hybrid RRF + reranker": ["chunk:a", "chunk:x"],
        }
    return {system: ["chunk:x"] for system in SYSTEMS}


def test_resumable_runner_keeps_per_query_checkpoints_and_metrics(tmp_path) -> None:
    first_calls: list[str] = []

    def interrupted(question: EvaluationQuestion):
        first_calls.append(question.question_id)
        if question.question_id == "q2":
            raise RuntimeError("simulated interruption")
        return _rankings(question)

    with pytest.raises(RuntimeError, match="simulated interruption"):
        run_resumable_evaluation(
            _questions(),
            interrupted,
            output_dir=tmp_path,
            metadata={"corpus": "fixture"},
            candidate_k=2,
            k=1,
        )

    checkpoint = tmp_path / "predictions.jsonl"
    records = [
        json.loads(line)
        for line in checkpoint.read_text(encoding="utf-8").splitlines()
    ]
    assert [record["id"] for record in records] == ["q1"]

    resumed_calls: list[str] = []

    def resume(question: EvaluationQuestion):
        resumed_calls.append(question.question_id)
        return _rankings(question)

    result = run_resumable_evaluation(
        _questions(),
        resume,
        output_dir=tmp_path,
        metadata={"corpus": "fixture"},
        candidate_k=2,
        k=1,
    )

    assert result.resumed_queries == 1
    assert result.total_queries == 2
    assert resumed_calls == ["q2"]
    assert result.metrics["Dense"].recall_at_k == 1.0
    assert result.metrics["Dense"].citation_precision == 0.5
    assert len(checkpoint.read_text(encoding="utf-8").splitlines()) == 2
    assert "Citation precision@1" in result.table_path.read_text(encoding="utf-8")


def test_resume_rejects_changed_metadata_and_incomplete_systems(tmp_path) -> None:
    run_resumable_evaluation(
        _questions(),
        _rankings,
        output_dir=tmp_path,
        metadata={"corpus": "first"},
        candidate_k=2,
        k=1,
    )

    with pytest.raises(EvaluationError, match="settings changed"):
        run_resumable_evaluation(
            _questions(),
            _rankings,
            output_dir=tmp_path,
            metadata={"corpus": "second"},
            candidate_k=2,
            k=1,
        )

    with pytest.raises(EvaluationError, match="all four"):
        run_resumable_evaluation(
            _questions(),
            lambda _: {"Dense": ["chunk:a"]},
            output_dir=tmp_path / "bad",
            metadata={},
            candidate_k=2,
            k=1,
            resume=False,
        )
