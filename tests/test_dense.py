"""Tests for lazy local dense embedding inference."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Literal

import pytest

torch = pytest.importorskip("torch")


class TinyTokenizer:
    def __call__(
        self,
        texts: list[str],
        *,
        padding: bool,
        truncation: bool,
        max_length: int,
        return_tensors: Literal["pt"],
    ) -> dict[str, torch.Tensor]:
        assert padding and truncation and max_length >= 1 and return_tensors == "pt"
        lengths = [max(1, len(text)) for text in texts]
        input_ids = torch.zeros((len(texts), max(lengths)), dtype=torch.long)
        mask = torch.zeros_like(input_ids)
        for index, length in enumerate(lengths):
            input_ids[index, :length] = torch.arange(1, length + 1)
            mask[index, :length] = 1
        return {"input_ids": input_ids, "attention_mask": mask}


class TinyEncoder(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.config = SimpleNamespace(hidden_size=2)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor):
        first = input_ids.to(dtype=torch.float32)
        second = torch.ones_like(first)
        hidden = torch.stack((first, second), dim=-1)
        return SimpleNamespace(last_hidden_state=hidden)


def test_dense_encoder_batches_mean_pools_and_normalizes() -> None:
    from ara.dl.dense import HuggingFaceDenseEncoder

    encoder = HuggingFaceDenseEncoder(
        TinyEncoder(), TinyTokenizer(), device="cpu", batch_size=2, max_length=16
    )

    embeddings = encoder.encode(["a", "ab", "abc"])

    assert embeddings.shape == (3, 2)
    assert torch.allclose(torch.linalg.vector_norm(embeddings, dim=1), torch.ones(3))
    assert torch.isfinite(embeddings).all()
    assert encoder.encode([]).shape == (0, 2)
