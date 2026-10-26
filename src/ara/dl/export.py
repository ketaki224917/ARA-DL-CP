"""Validate and package a trained cross-encoder for local inference."""

from __future__ import annotations

import argparse
import logging
import tempfile
from collections.abc import Mapping
from pathlib import Path

import torch
from torch import Tensor

from ara.config import Settings, load_settings
from ara.logging_setup import configure_logging

logger = logging.getLogger(__name__)
_FORMAT_VERSION = 1


def export_checkpoint(settings: Settings | None = None) -> Path:
    """Write a minimal inference bundle from the validated training checkpoint."""
    resolved = settings or load_settings()
    source_path = resolved.dl_checkpoint_path
    if not source_path.is_file():
        raise FileNotFoundError(
            f"Trained checkpoint not found at {source_path}; run ara.dl.train first."
        )
    payload = torch.load(source_path, map_location="cpu", weights_only=True)
    if not isinstance(payload, Mapping):
        raise ValueError("Training checkpoint must contain a mapping.")
    if payload.get("format_version") != _FORMAT_VERSION:
        raise ValueError("Training checkpoint format is unsupported.")
    if payload.get("model_name") != resolved.reranker_model:
        raise ValueError("Training checkpoint model name does not match configuration.")
    if payload.get("model_revision") != resolved.dl_model_revision:
        raise ValueError("Training checkpoint revision does not match configuration.")
    state_dict = payload.get("model_state_dict")
    if not isinstance(state_dict, Mapping) or not state_dict:
        raise ValueError("Training checkpoint has no model state dictionary.")
    if any(
        not isinstance(name, str) or not isinstance(value, Tensor)
        for name, value in state_dict.items()
    ):
        raise ValueError("Training checkpoint state dictionary is malformed.")
    credibility_head = payload.get("credibility_head")
    if not isinstance(credibility_head, bool):
        raise ValueError("Training checkpoint credibility-head metadata is malformed.")

    bundle = {
        "format_version": _FORMAT_VERSION,
        "model_name": resolved.reranker_model,
        "model_revision": resolved.dl_model_revision,
        "credibility_head": credibility_head,
        "model_state_dict": dict(state_dict),
    }
    destination = resolved.dl_export_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=destination.parent,
        prefix=f"{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_stream:
        temporary_path = Path(temporary_stream.name)
    try:
        torch.save(bundle, temporary_path)
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    logger.info("Exported trained cross-encoder to %s", destination)
    return destination


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    configure_logging()
    export_checkpoint()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
