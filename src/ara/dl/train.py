"""Seeded CPU-capable training loop for the ARA SciFact cross-encoder."""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import tempfile
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import torch
from torch import Tensor, nn

from ara.config import Settings, load_settings
from ara.dl.dataset import PairBatch, PairTokenizer, build_pair_examples, make_pair_dataloader
from ara.dl.model import CrossEncoderScorer, available_device, load_pair_tokenizer
from ara.logging_setup import configure_logging

logger = logging.getLogger(__name__)
_CHECKPOINT_FORMAT_VERSION = 1


@dataclass(frozen=True)
class EpochMetrics:
    """Training and validation binary cross-entropy for one epoch."""

    epoch: int
    training_loss: float
    validation_loss: float


@dataclass(frozen=True)
class TrainingResult:
    """Best checkpoint and reproducible run metrics."""

    history: tuple[EpochMetrics, ...]
    best_epoch: int
    best_validation_loss: float
    stopped_early: bool
    training_example_count: int
    validation_example_count: int
    negative_strategy: Literal["bm25", "random"]
    checkpoint_path: Path
    metrics_path: Path
    curves_path: Path
    smoke_batch_limit: int | None


def train_model(
    settings: Settings | None = None,
    *,
    model: nn.Module | None = None,
    tokenizer: PairTokenizer | None = None,
    data_dir: Path | str | None = None,
    device: torch.device | str | None = None,
    epochs: int | None = None,
    include_synthetic_pairs: bool | None = None,
    negative_strategy: Literal["bm25", "random"] = "bm25",
    max_batches_per_epoch: int | None = None,
) -> TrainingResult:
    """Train on train pairs, early-stop on validation, and never inspect test labels.

    `max_batches_per_epoch` is intended only for smoke runs. Passing it records the
    result as a smoke run in the metrics JSON and does not change the normal config.
    Models and tokenizers are loaded lazily so importing this module is offline-safe.
    """
    resolved = settings or load_settings()
    run_epochs = epochs if epochs is not None else resolved.dl_epochs
    if run_epochs < 1:
        raise ValueError("epochs must be positive")
    if max_batches_per_epoch is not None and max_batches_per_epoch < 1:
        raise ValueError("max_batches_per_epoch must be positive when specified")
    _seed_everything(resolved.dl_seed)

    dataset_dir = Path(data_dir) if data_dir is not None else resolved.dl_public_data_dir
    use_synthetic = (
        resolved.dl_use_synthetic_pairs
        if include_synthetic_pairs is None
        else include_synthetic_pairs
    )
    train_pairs = build_pair_examples(
        dataset_dir,
        "train",
        candidate_k=resolved.dl_candidate_k,
        negative_pool_size=resolved.dl_negative_pool_size,
        seed=resolved.dl_seed,
        negative_strategy=negative_strategy,
        include_synthetic_train=use_synthetic,
        synthetic_path=resolved.dl_data_path,
    )
    validation_pairs = build_pair_examples(
        dataset_dir,
        "validation",
        candidate_k=resolved.dl_candidate_k,
        negative_pool_size=resolved.dl_negative_pool_size,
        seed=resolved.dl_seed,
        negative_strategy=negative_strategy,
    )
    _validate_training_pairs(train_pairs.examples, split_name="train")
    _validate_training_pairs(validation_pairs.examples, split_name="validation")

    pair_tokenizer = tokenizer or load_pair_tokenizer(resolved)
    scorer = model or CrossEncoderScorer.from_pretrained(resolved)
    target_device = torch.device(device) if device is not None else available_device()
    scorer.to(target_device)
    training_loader = make_pair_dataloader(
        train_pairs.examples,
        pair_tokenizer,
        batch_size=resolved.dl_batch_size,
        max_length=resolved.dl_max_length,
        shuffle=True,
        seed=resolved.dl_seed,
    )
    validation_loader = make_pair_dataloader(
        validation_pairs.examples,
        pair_tokenizer,
        batch_size=resolved.dl_batch_size,
        max_length=resolved.dl_max_length,
        shuffle=False,
        seed=resolved.dl_seed,
    )
    optimizer = torch.optim.AdamW(
        scorer.parameters(),
        lr=resolved.dl_learning_rate,
        weight_decay=resolved.dl_weight_decay,
    )

    history: list[EpochMetrics] = []
    best_state: dict[str, Tensor] | None = None
    best_epoch = 0
    best_validation_loss = float("inf")
    epochs_without_improvement = 0
    stopped_early = False
    for epoch in range(1, run_epochs + 1):
        training_loss = _run_epoch(
            scorer,
            training_loader,
            target_device,
            optimizer=optimizer,
            max_batches=max_batches_per_epoch,
        )
        validation_loss = _run_epoch(
            scorer,
            validation_loader,
            target_device,
            optimizer=None,
            max_batches=max_batches_per_epoch,
        )
        metrics = EpochMetrics(
            epoch=epoch,
            training_loss=training_loss,
            validation_loss=validation_loss,
        )
        history.append(metrics)
        logger.info(
            "DL epoch %d/%d train_loss=%.6f validation_loss=%.6f",
            epoch,
            run_epochs,
            training_loss,
            validation_loss,
        )

        if validation_loss < best_validation_loss - resolved.dl_early_stopping_min_delta:
            best_validation_loss = validation_loss
            best_epoch = epoch
            epochs_without_improvement = 0
            best_state = _cpu_state_dict(scorer)
            _save_checkpoint(
                resolved.dl_checkpoint_path,
                state_dict=best_state,
                settings=resolved,
                training_epochs=run_epochs,
                negative_strategy=negative_strategy,
                best_epoch=best_epoch,
                best_validation_loss=best_validation_loss,
                history=history,
            )
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= resolved.dl_early_stopping_patience:
                stopped_early = True
                logger.info("Early stopping after epoch %d", epoch)
                break

    if best_state is None:
        raise RuntimeError("training did not produce a finite validation checkpoint")
    scorer.load_state_dict(best_state)
    result = TrainingResult(
        history=tuple(history),
        best_epoch=best_epoch,
        best_validation_loss=best_validation_loss,
        stopped_early=stopped_early,
        training_example_count=len(train_pairs.examples),
        validation_example_count=len(validation_pairs.examples),
        negative_strategy=negative_strategy,
        checkpoint_path=resolved.dl_checkpoint_path,
        metrics_path=resolved.dl_metrics_path,
        curves_path=resolved.dl_curves_path,
        smoke_batch_limit=max_batches_per_epoch,
    )
    _write_metrics(result, resolved)
    _save_loss_curve(result.history, resolved.dl_curves_path)
    logger.info(
        "Saved best DL checkpoint to %s, metrics to %s, and loss curve to %s",
        result.checkpoint_path,
        result.metrics_path,
        result.curves_path,
    )
    return result


def _run_epoch(
    model: nn.Module,
    batches: Any,
    device: torch.device,
    *,
    optimizer: torch.optim.Optimizer | None,
    max_batches: int | None,
) -> float:
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    total_examples = 0
    for batch_index, batch in enumerate(batches):
        if max_batches is not None and batch_index >= max_batches:
            break
        if not isinstance(batch, PairBatch):
            raise TypeError("DataLoader returned an unexpected batch type")
        model_inputs = {name: tensor.to(device) for name, tensor in batch.model_inputs.items()}
        relevance_labels = batch.relevance_labels.to(device)
        credibility_labels = batch.credibility_labels.to(device)
        credibility_mask = batch.credibility_mask.to(device)

        if optimizer is not None:
            optimizer.zero_grad(set_to_none=True)
        with torch.set_grad_enabled(training):
            output = model(**model_inputs)
            loss = CrossEncoderScorer.compute_loss(
                output,
                relevance_labels,
                credibility_labels=credibility_labels,
                credibility_mask=credibility_mask,
            )
        if optimizer is not None:
            loss.backward()
            optimizer.step()
        batch_size = int(relevance_labels.numel())
        total_loss += float(loss.detach().item()) * batch_size
        total_examples += batch_size
    if total_examples == 0:
        raise ValueError("training or validation loader produced no examples")
    return total_loss / total_examples


def _validate_training_pairs(examples: Sequence[Any], *, split_name: str) -> None:
    if not examples:
        raise ValueError(f"{split_name} split contains no query/passage pairs")
    labels = {example.relevance_label for example in examples}
    if not {0.0, 1.0}.issubset(labels):
        raise ValueError(f"{split_name} split must contain positive and negative pairs")


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _cpu_state_dict(model: nn.Module) -> dict[str, Tensor]:
    return {name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()}


def _save_checkpoint(
    path: Path,
    *,
    state_dict: dict[str, Tensor],
    settings: Settings,
    training_epochs: int,
    negative_strategy: Literal["bm25", "random"],
    best_epoch: int,
    best_validation_loss: float,
    history: Sequence[EpochMetrics],
) -> None:
    payload = {
        "format_version": _CHECKPOINT_FORMAT_VERSION,
        "model_name": settings.reranker_model,
        "model_revision": settings.dl_model_revision,
        "credibility_head": settings.dl_credibility_head,
        "seed": settings.dl_seed,
        "best_epoch": best_epoch,
        "best_validation_loss": best_validation_loss,
        "training_config": {
            "epochs": training_epochs,
            "learning_rate": settings.dl_learning_rate,
            "weight_decay": settings.dl_weight_decay,
            "early_stopping_patience": settings.dl_early_stopping_patience,
            "early_stopping_min_delta": settings.dl_early_stopping_min_delta,
            "batch_size": settings.dl_batch_size,
            "max_length": settings.dl_max_length,
            "negative_strategy": negative_strategy,
        },
        "history": [asdict(row) for row in history],
        "model_state_dict": state_dict,
    }
    temporary_path = _temporary_path(path)
    try:
        torch.save(payload, temporary_path)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_metrics(result: TrainingResult, settings: Settings) -> None:
    payload = {
        "best_epoch": result.best_epoch,
        "best_validation_loss": result.best_validation_loss,
        "stopped_early": result.stopped_early,
        "training_example_count": result.training_example_count,
        "validation_example_count": result.validation_example_count,
        "negative_strategy": result.negative_strategy,
        "smoke_batch_limit": result.smoke_batch_limit,
        "checkpoint_path": str(result.checkpoint_path),
        "curves_path": str(result.curves_path),
        "seed": settings.dl_seed,
        "history": [asdict(row) for row in result.history],
    }
    path = result.metrics_path
    temporary_path = _temporary_path(path)
    try:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _save_loss_curve(history: Sequence[EpochMetrics], path: Path) -> None:
    if "MPLCONFIGDIR" not in os.environ:
        matplotlib_cache = Path(tempfile.gettempdir()) / "ara-matplotlib-cache"
        matplotlib_cache.mkdir(parents=True, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = str(matplotlib_cache)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    epochs = [row.epoch for row in history]
    figure, axis = plt.subplots(figsize=(7, 4))
    axis.plot(epochs, [row.training_loss for row in history], marker="o", label="Train")
    axis.plot(epochs, [row.validation_loss for row in history], marker="o", label="Validation")
    axis.set(title="Cross-encoder training loss", xlabel="Epoch", ylabel="Binary cross-entropy")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=140)
    plt.close(figure)


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


def main(argv: Sequence[str] | None = None) -> int:
    """Run training from config, with explicit limits available for smoke checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, help="SciFact split directory")
    parser.add_argument("--epochs", type=int, help="override configured epoch count")
    parser.add_argument("--no-synthetic-pairs", action="store_true")
    parser.add_argument("--random-negatives", action="store_true")
    parser.add_argument(
        "--max-batches",
        type=int,
        help="smoke-only limit applied to train and validation batches per epoch",
    )
    args = parser.parse_args(argv)
    configure_logging()
    result = train_model(
        data_dir=args.data_dir,
        epochs=args.epochs,
        include_synthetic_pairs=False if args.no_synthetic_pairs else None,
        negative_strategy="random" if args.random_negatives else "bm25",
        max_batches_per_epoch=args.max_batches,
    )
    logger.info(
        "Training complete: best_epoch=%d validation_loss=%.6f stopped_early=%s",
        result.best_epoch,
        result.best_validation_loss,
        result.stopped_early,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
