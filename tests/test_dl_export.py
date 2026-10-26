"""Tests for the safe inference bundle exporter."""

from pathlib import Path

import pytest

from ara.config import Settings


def _dl_tools():
    torch = pytest.importorskip("torch")
    from ara.dl.export import export_checkpoint

    return torch, export_checkpoint


def test_export_checkpoint_writes_minimal_bundle_atomically(tmp_path: Path) -> None:
    torch, export_checkpoint = _dl_tools()
    source = tmp_path / "trained.pt"
    destination = tmp_path / "nested" / "exported.pt"
    settings = Settings(
        _env_file=None,
        dl_checkpoint_path=source,
        dl_export_path=destination,
    )
    torch.save(
        {
            "format_version": 1,
            "model_name": settings.reranker_model,
            "model_revision": settings.dl_model_revision,
            "credibility_head": False,
            "training_config": {"epochs": 3},
            "history": [{"epoch": 1}],
            "model_state_dict": {"weight": torch.tensor([1.0, 2.0])},
        },
        source,
    )

    result = export_checkpoint(settings)
    bundle = torch.load(result, map_location="cpu", weights_only=True)

    assert result == destination
    assert bundle["format_version"] == 1
    assert bundle["model_name"] == settings.reranker_model
    assert bundle["model_revision"] == settings.dl_model_revision
    assert bundle["credibility_head"] is False
    assert set(bundle) == {
        "format_version",
        "model_name",
        "model_revision",
        "credibility_head",
        "model_state_dict",
    }
    assert torch.equal(bundle["model_state_dict"]["weight"], torch.tensor([1.0, 2.0]))
    assert list(destination.parent.iterdir()) == [destination]


def test_export_checkpoint_rejects_model_revision_mismatch(tmp_path: Path) -> None:
    torch, export_checkpoint = _dl_tools()
    source = tmp_path / "trained.pt"
    settings = Settings(
        _env_file=None,
        dl_checkpoint_path=source,
        dl_export_path=tmp_path / "exported.pt",
    )
    torch.save(
        {
            "format_version": 1,
            "model_name": settings.reranker_model,
            "model_revision": "wrong-revision",
            "credibility_head": False,
            "model_state_dict": {"weight": torch.tensor([1.0])},
        },
        source,
    )

    with pytest.raises(ValueError, match="revision"):
        export_checkpoint(settings)


def test_export_checkpoint_reports_missing_training_checkpoint(tmp_path: Path) -> None:
    _, export_checkpoint = _dl_tools()
    settings = Settings(
        _env_file=None,
        dl_checkpoint_path=tmp_path / "missing.pt",
        dl_export_path=tmp_path / "exported.pt",
    )

    with pytest.raises(FileNotFoundError, match="run ara.dl.train"):
        export_checkpoint(settings)
