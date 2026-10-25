"""Offline tests for deterministic training, early stopping, and artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pytest

torch = pytest.importorskip("torch")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _make_split(root: Path, split: str) -> None:
    _write_jsonl(
        root / f"corpus_{split}.jsonl",
        [
            {
                "document_id": f"{split}-pos",
                "title": "Cardiac risk",
                "text": "Blood pressure increases cardiac disease risk in adult patients.",
            },
            {
                "document_id": f"{split}-neg",
                "title": "Treatment outcomes",
                "text": "A trial compared cardiac pressure treatment outcomes for adult patients.",
            },
        ],
    )
    _write_jsonl(
        root / f"queries_{split}.jsonl",
        [
            {
                "query_id": f"{split}:q1",
                "query": "Does blood pressure change cardiac disease risk?",
                "split": split,
                "positives": [{"document_id": f"{split}-pos", "relevance": 1}],
            }
        ],
    )


class TinyTokenizer:
    """Deterministic fake pair tokenizer for exercising the full optimizer loop."""

    def __call__(
        self,
        queries: list[str],
        passages: list[str],
        *,
        padding: bool,
        truncation: bool,
        max_length: int,
        return_tensors: Literal["pt"],
    ) -> dict[str, torch.Tensor]:
        assert padding and truncation and max_length >= 16 and return_tensors == "pt"
        features = [
            [len(query), len(passage)]
            for query, passage in zip(queries, passages, strict=True)
        ]
        return {
            "input_ids": torch.tensor(features, dtype=torch.long),
            "attention_mask": torch.ones((len(features), 2), dtype=torch.long),
        }


def _tiny_model() -> torch.nn.Module:
    from ara.dl.model import CrossEncoderOutput

    class TinyScorer(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.classifier = torch.nn.Linear(1, 1)

        def forward(
            self,
            *,
            input_ids: torch.Tensor,
            attention_mask: torch.Tensor | None = None,
        ) -> CrossEncoderOutput:
            features = input_ids.to(dtype=torch.float32).mean(dim=1, keepdim=True) / 100.0
            return CrossEncoderOutput(self.classifier(features).reshape(-1))

    return TinyScorer()


def _settings(data_dir: Path, output_dir: Path):
    from ara.config import Settings

    return Settings(
        _env_file=None,
        dl_public_data_dir=data_dir,
        dl_use_synthetic_pairs=False,
        dl_epochs=5,
        dl_learning_rate=0.01,
        dl_weight_decay=0,
        dl_early_stopping_patience=1,
        dl_early_stopping_min_delta=1.0,
        dl_batch_size=2,
        dl_max_length=32,
        dl_checkpoint_path=output_dir / "best.pt",
        dl_curves_path=output_dir / "loss.png",
        dl_metrics_path=output_dir / "metrics.json",
    )


def test_training_is_seeded_early_stops_and_saves_best_artifacts(tmp_path: Path) -> None:
    _make_split(tmp_path, "train")
    _make_split(tmp_path, "validation")

    from ara.dl.train import train_model

    results = []
    for name in ("run-one", "run-two"):
        torch.manual_seed(23)
        results.append(
            train_model(
                _settings(tmp_path, tmp_path / name),
                model=_tiny_model(),
                tokenizer=TinyTokenizer(),
                device="cpu",
            )
        )

    first, second = results
    assert first.history == second.history
    assert len(first.history) == 2
    assert first.best_epoch == 1
    assert first.stopped_early is True
    assert first.training_example_count == 2
    assert first.validation_example_count == 2
    assert first.best_validation_loss == pytest.approx(first.history[0].validation_loss)

    checkpoint = torch.load(first.checkpoint_path, map_location="cpu", weights_only=True)
    assert checkpoint["format_version"] == 1
    assert checkpoint["best_epoch"] == first.best_epoch
    assert checkpoint["model_revision"] == "df500e56a59fc34f37322735a40eff666200312e"
    assert checkpoint["training_config"]["epochs"] == 5
    assert Path(first.checkpoint_path).is_file()
    assert Path(first.metrics_path).is_file()
    assert Path(first.curves_path).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    metrics = json.loads(first.metrics_path.read_text(encoding="utf-8"))
    assert metrics["best_epoch"] == 1
    assert metrics["stopped_early"] is True
