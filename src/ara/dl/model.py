"""Pretrained cross-encoder scorer with an optional supervised credibility head."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from torch import Tensor, nn

from ara.config import Settings, load_settings
from ara.dl.hf_compat import configure_system_certificates

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CrossEncoderOutput:
    """Per-pair logits from the relevance and optional credibility heads."""

    relevance_logits: Tensor
    credibility_logits: Tensor | None = None


class CrossEncoderScorer(nn.Module):
    """Fine-tunable sequence-pair model initialized from a pretrained reranker."""

    def __init__(self, backbone: nn.Module, *, credibility_head: bool = False) -> None:
        super().__init__()
        self.backbone = backbone
        self.credibility_head: nn.Linear | None = None
        if credibility_head:
            hidden_size = getattr(backbone.config, "hidden_size", None)
            if not isinstance(hidden_size, int) or hidden_size < 1:
                raise ValueError("backbone config must expose a positive hidden_size")
            self.credibility_head = nn.Linear(hidden_size, 1)

    @classmethod
    def from_pretrained(
        cls,
        settings: Settings | None = None,
        *,
        model_name: str | None = None,
        revision: str | None = None,
        cache_dir: Path | str | None = None,
        credibility_head: bool | None = None,
    ) -> CrossEncoderScorer:
        """Load the configured Hugging Face sequence-classification checkpoint lazily."""
        configure_system_certificates()
        from transformers import AutoModelForSequenceClassification

        resolved = settings or load_settings()
        checkpoint = model_name or resolved.reranker_model
        model_revision = revision or resolved.dl_model_revision
        model_cache = Path(cache_dir) if cache_dir is not None else resolved.dl_model_cache_dir
        use_credibility = (
            resolved.dl_credibility_head if credibility_head is None else credibility_head
        )
        backbone = AutoModelForSequenceClassification.from_pretrained(
            checkpoint,
            revision=model_revision,
            cache_dir=str(model_cache),
            num_labels=1,
        )
        logger.info(
            "Loaded cross-encoder checkpoint %s at %s from %s",
            checkpoint,
            model_revision,
            model_cache,
        )
        return cls(backbone, credibility_head=use_credibility)

    def forward(
        self,
        *,
        input_ids: Tensor,
        attention_mask: Tensor | None = None,
        token_type_ids: Tensor | None = None,
    ) -> CrossEncoderOutput:
        """Return one relevance logit and, when enabled, one credibility logit per pair."""
        inputs: dict[str, Any] = {"input_ids": input_ids, "return_dict": True}
        if attention_mask is not None:
            inputs["attention_mask"] = attention_mask
        if token_type_ids is not None:
            inputs["token_type_ids"] = token_type_ids
        if self.credibility_head is not None:
            inputs["output_hidden_states"] = True

        outputs = self.backbone(**inputs)
        relevance_logits = outputs.logits.reshape(-1)
        credibility_logits: Tensor | None = None
        if self.credibility_head is not None:
            hidden_states = outputs.hidden_states
            if not hidden_states:
                raise RuntimeError("backbone did not return hidden states for credibility scoring")
            credibility_logits = self.credibility_head(hidden_states[-1][:, 0, :]).reshape(-1)
        return CrossEncoderOutput(
            relevance_logits=relevance_logits,
            credibility_logits=credibility_logits,
        )

    @staticmethod
    def compute_loss(
        output: CrossEncoderOutput,
        relevance_labels: Tensor,
        *,
        credibility_labels: Tensor | None = None,
        credibility_mask: Tensor | None = None,
        credibility_weight: float = 1.0,
    ) -> Tensor:
        """Compute binary relevance loss and masked optional credibility loss."""
        if relevance_labels.numel() != output.relevance_logits.numel():
            raise ValueError("relevance labels and logits must have the same number of items")
        if credibility_weight < 0:
            raise ValueError("credibility_weight must be non-negative")
        if (credibility_labels is None) != (credibility_mask is None):
            raise ValueError("credibility labels and mask must be supplied together")
        relevance_loss = nn.functional.binary_cross_entropy_with_logits(
            output.relevance_logits,
            relevance_labels.to(dtype=output.relevance_logits.dtype),
        )
        if output.credibility_logits is None:
            if credibility_labels is not None and credibility_mask is not None and bool(
                credibility_mask.any()
            ):
                raise ValueError("credibility labels were supplied but the head is disabled")
            return relevance_loss
        if credibility_labels is None or credibility_mask is None:
            return relevance_loss
        mask = credibility_mask.to(dtype=torch.bool)
        if mask.numel() != output.credibility_logits.numel():
            raise ValueError("credibility mask and logits must have the same number of items")
        if not bool(mask.any()):
            return relevance_loss
        credibility_loss = nn.functional.binary_cross_entropy_with_logits(
            output.credibility_logits[mask],
            credibility_labels[mask].to(dtype=output.credibility_logits.dtype),
        )
        return relevance_loss + credibility_weight * credibility_loss


def load_pair_tokenizer(
    settings: Settings | None = None,
    *,
    model_name: str | None = None,
    revision: str | None = None,
    cache_dir: Path | str | None = None,
) -> Any:
    """Load the checkpoint's pair tokenizer only when explicitly requested."""
    configure_system_certificates()
    from transformers import AutoTokenizer

    resolved = settings or load_settings()
    checkpoint = model_name or resolved.reranker_model
    model_revision = revision or resolved.dl_model_revision
    model_cache = Path(cache_dir) if cache_dir is not None else resolved.dl_model_cache_dir
    tokenizer = AutoTokenizer.from_pretrained(
        checkpoint,
        revision=model_revision,
        cache_dir=str(model_cache),
        use_fast=True,
    )
    logger.info("Loaded tokenizer for %s at %s", checkpoint, model_revision)
    return tokenizer


def available_device() -> torch.device:
    """Choose CUDA, then Apple MPS, then CPU without assuming accelerator support."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
