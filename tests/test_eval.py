"""Tests for the retrieval evaluation metrics and report output."""

import json
import math

import pytest

from ara.rag.eval import (
    EvaluationError,
    EvaluationQuestion,
    Prediction,
    compare_runs,
    evaluate_predictions,
    format_metrics_table,
    load_evaluation_set,
    save_metrics_json,
)


def questions() -> list[EvaluationQuestion]:
    return [
        EvaluationQuestion("q1", "factoid", "first", "answer", True, ("a", "b")),
        EvaluationQuestion("q2", "factoid", "second", "answer", True, ("x",)),
        EvaluationQuestion("q3", "unanswerable", "third", None, False, ()),
    ]


def test_metrics_compute_recall_mrr_ndcg_citation_precision_and_abstention() -> None:
    predictions = {
        "q1": Prediction(("z", "a", "b"), ("a", "b")),
        "q2": Prediction(("x",), ("x",)),
        "q3": Prediction((), ("a",), abstained=True),
    }

    metrics = evaluate_predictions(questions(), predictions, k=2)

    assert metrics.question_count == 3
    assert metrics.answerable_count == 2
    assert metrics.unanswerable_count == 1
    assert metrics.recall_at_k == pytest.approx(0.75)
    assert metrics.mrr == pytest.approx(0.75)
    assert metrics.ndcg_at_k == pytest.approx((1 + 1 / (math.log2(3) + 1)) / 2)
    assert metrics.citation_precision == pytest.approx(0.75)
    assert metrics.answerable_response_rate == 1.0
    assert metrics.unanswerable_abstention_rate == 1.0


def test_missing_predictions_count_as_zero_and_duplicate_ids_do_not_inflate_scores() -> None:
    metrics = evaluate_predictions(
        questions(),
        {"q2": Prediction(("x", "x"), ("x", "x"))},
        k=1,
    )

    assert metrics.recall_at_k == pytest.approx(0.5)
    assert metrics.mrr == pytest.approx(0.5)
    assert metrics.citation_precision == 1.0
    assert metrics.answerable_response_rate == 0.5


def test_compare_runs_and_markdown_table_are_stable() -> None:
    reports = compare_runs(
        questions(),
        {
            "hybrid": {"q2": Prediction(("x",), ("x",))},
            "dense": {"q2": Prediction((), ())},
        },
    )
    table = format_metrics_table(reports)

    assert list(reports) == ["dense", "hybrid"]
    assert "Recall@k" in table
    assert "Citation precision" in table
    assert table.index("dense") < table.index("hybrid")


def test_metrics_json_is_saved_with_metadata(tmp_path) -> None:
    metrics = evaluate_predictions(questions(), {})
    path = tmp_path / "nested" / "metrics.json"

    save_metrics_json(path, {"dense": metrics}, metadata={"model": "test"})

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["metadata"] == {"model": "test"}
    assert payload["systems"]["dense"]["question_count"] == 3
    assert not list(path.parent.glob("*.tmp"))


def test_loader_rejects_duplicate_ids_and_inconsistent_answerability(tmp_path) -> None:
    path = tmp_path / "eval.jsonl"
    valid = {
        "id": "q1",
        "category": "factoid",
        "question": "q",
        "expected_answer": "a",
        "answerable": True,
        "gold_chunk_ids": ["chunk:a"],
    }
    path.write_text(json.dumps(valid) + "\n" + json.dumps(valid) + "\n", encoding="utf-8")

    with pytest.raises(EvaluationError, match="Duplicate"):
        load_evaluation_set(path)

    valid["answerable"] = False
    path.write_text(json.dumps(valid), encoding="utf-8")
    with pytest.raises(EvaluationError, match="answerable"):
        load_evaluation_set(path)


def test_metric_parameters_and_unknown_prediction_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="k"):
        evaluate_predictions(questions(), {}, k=0)
    with pytest.raises(ValueError, match="unknown question"):
        evaluate_predictions(questions(), {"unknown": Prediction()})
