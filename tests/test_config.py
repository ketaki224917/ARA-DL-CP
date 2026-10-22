"""Tests for configuration source precedence and validation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from ara.config import Settings, load_settings


def test_yaml_defaults_and_environment_overrides(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        "llm:\n  model: local-model\n"
        "embeddings:\n  model: local-embedder\n"
        "paths:\n  data_dir: corpus\n",
        encoding="utf-8",
    )
    dotenv = tmp_path / ".env"
    dotenv.write_text("ARA_LLM_MODEL=dotenv-model\n", encoding="utf-8")

    settings = load_settings(
        config,
        dotenv,
        environ={
            "ARA_LLM_MODEL": "environment-model",
            "ARA_EMBEDDING_MODEL": "environment-embedder",
            "ARA_RETRIEVAL_TOP_K": "4",
            "ARA_RERANKER_MODEL": "local-cross-encoder",
        },
    )

    assert settings.llm_model == "environment-model"
    assert settings.data_dir == Path("corpus")
    assert settings.embedding_model == "environment-embedder"
    assert settings.retrieval_top_k == 4
    assert settings.reranker_model == "local-cross-encoder"


def test_missing_yaml_uses_defaults(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.yaml", tmp_path / "missing.env", environ={})

    assert settings.llm_model == "qwen2.5:1.5b"
    assert settings.embedding_model == "embeddinggemma"
    assert settings.reranker_model == "cross-encoder/ms-marco-MiniLM-L6-v2"
    assert settings.llm_request_timeout_seconds == 120


def test_invalid_configuration_section_is_rejected(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text("llm: nope\n", encoding="utf-8")

    with pytest.raises(ValueError, match="YAML mappings"):
        load_settings(config, tmp_path / "missing.env", environ={})


def test_settings_validate_ranges() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, retrieval_chunk_overlap=-1)

