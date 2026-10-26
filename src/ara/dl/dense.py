"""Local mean-pooled transformer embeddings for dense retrieval evaluation."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import torch
from torch import Tensor, nn
from torch.nn import functional as functional

from ara.config import Settings, load_settings
from ara.dl.hf_compat import configure_system_certificates
from ara.dl.model import available_device

logger = logging.getLogger(__name__)


class HuggingFaceDenseEncoder:
    """Encode passages with attention-mask mean pooling and L2 normalization."""

    def __init__(
        self,
        model: nn.Module,
        tokenizer: Any,
        *,
        device: torch.device | str,
        batch_size: int,
        max_length: int,
    ) -> None:
        if batch_size < 1 or max_length < 1:
            raise ValueError("batch_size and max_length must be positive")
        self.model = model
        self.tokenizer = tokenizer
        self.device = torch.device(device)
        self.batch_size = batch_size
        self.max_length = max_length
        self.model.to(self.device)
        self.model.eval()

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> HuggingFaceDenseEncoder:
        """Load the configured sentence embedding model only when evaluation starts."""
        configure_system_certificates()
        from transformers import AutoModel, AutoTokenizer

        resolved = settings or load_settings()
        model = AutoModel.from_pretrained(
            resolved.dl_dense_model,
            revision=resolved.dl_dense_model_revision,
            cache_dir=str(resolved.dl_model_cache_dir),
        )
        tokenizer = AutoTokenizer.from_pretrained(
            resolved.dl_dense_model,
            revision=resolved.dl_dense_model_revision,
            cache_dir=str(resolved.dl_model_cache_dir),
            use_fast=True,
        )
        logger.info(
            "Loaded dense encoder %s at %s",
            resolved.dl_dense_model,
            resolved.dl_dense_model_revision,
        )
        return cls(
            model,
            tokenizer,
            device=available_device(),
            batch_size=resolved.dl_eval_batch_size,
            max_length=resolved.dl_max_length,
        )

    @torch.inference_mode()
    def encode(self, texts: Sequence[str]) -> Tensor:
        """Return one unit-normalized mean-pooled embedding per input text."""
        if not texts:
            hidden_size = getattr(self.model.config, "hidden_size", 0)
            return torch.empty((0, int(hidden_size)), dtype=torch.float32)
        batches: list[Tensor] = []
        for start in range(0, len(texts), self.batch_size):
            batch_texts = list(texts[start : start + self.batch_size])
            encoded = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            )
            model_inputs = {name: value.to(self.device) for name, value in encoded.items()}
            output = self.model(**model_inputs)
            token_embeddings = output.last_hidden_state
            attention_mask = model_inputs["attention_mask"].unsqueeze(-1).to(
                dtype=token_embeddings.dtype
            )
            pooled = (token_embeddings * attention_mask).sum(dim=1) / attention_mask.sum(
                dim=1
            ).clamp(min=1e-9)
            batches.append(functional.normalize(pooled, p=2, dim=1).cpu())
        result = torch.cat(batches, dim=0)
        if result.shape[0] != len(texts) or not bool(torch.isfinite(result).all()):
            raise RuntimeError("dense encoder returned invalid embeddings")
        return result
