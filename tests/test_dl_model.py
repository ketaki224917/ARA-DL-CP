"""Offline tests for the custom DL cross-encoder wrapper."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")


def _tiny_backbone() -> torch.nn.Module:
    transformers = pytest.importorskip("transformers")
    config = transformers.BertConfig(
        vocab_size=32,
        hidden_size=16,
        num_hidden_layers=1,
        num_attention_heads=2,
        intermediate_size=32,
        num_labels=1,
    )
    return transformers.BertForSequenceClassification(config)


def test_cross_encoder_relevance_and_optional_credibility_heads_backpropagate() -> None:
    from ara.dl.model import CrossEncoderScorer

    torch.manual_seed(5)
    model = CrossEncoderScorer(_tiny_backbone(), credibility_head=True)
    inputs = {
        "input_ids": torch.tensor([[1, 2, 3, 0], [4, 5, 0, 0]]),
        "attention_mask": torch.tensor([[1, 1, 1, 0], [1, 1, 0, 0]]),
        "token_type_ids": torch.zeros((2, 4), dtype=torch.long),
    }

    output = model(**inputs)
    loss = model.compute_loss(
        output,
        torch.tensor([1.0, 0.0]),
        credibility_labels=torch.tensor([0.0, 1.0]),
        credibility_mask=torch.tensor([False, True]),
    )
    loss.backward()

    assert output.relevance_logits.shape == (2,)
    assert output.credibility_logits is not None
    assert output.credibility_logits.shape == (2,)
    assert torch.isfinite(loss)
    assert model.credibility_head is not None
    assert model.credibility_head.weight.grad is not None
    assert model.backbone.classifier.weight.grad is not None


def test_relevance_only_head_returns_scalar_per_pair() -> None:
    from ara.dl.model import CrossEncoderScorer, available_device

    model = CrossEncoderScorer(_tiny_backbone())
    output = model(input_ids=torch.tensor([[1, 2, 3]]))

    assert output.relevance_logits.shape == (1,)
    assert output.credibility_logits is None
    assert available_device().type in {"cpu", "cuda", "mps"}


def test_relevance_label_count_must_match_logits() -> None:
    from ara.dl.model import CrossEncoderScorer

    model = CrossEncoderScorer(_tiny_backbone())
    output = model(input_ids=torch.tensor([[1, 2, 3]]))

    with pytest.raises(ValueError, match="same number"):
        model.compute_loss(output, torch.tensor([1.0, 0.0]))
