"""Tests for configuration source precedence and validation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from ara.config import Settings, load_settings


def test_yaml_defaults_and_environment_overrides(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        "llm:\n  model: local-model\n"
        "  num_predict: 640\n"
        "  writer_num_predict: 448\n"
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
            "ARA_LLM_NUM_PREDICT": "512",
            "ARA_LLM_WRITER_NUM_PREDICT": "320",
            "ARA_EMBEDDING_MODEL": "environment-embedder",
            "ARA_RETRIEVAL_TOP_K": "4",
            "ARA_RERANKER_MODEL": "local-cross-encoder",
            "ARA_ANSWER_MINIMUM_EVIDENCE_SCORE": "0.03",
            "ARA_ANSWER_MAX_EVIDENCE_CHUNKS": "5",
            "ARA_INGEST_SOURCE_DIR": "private_docs",
            "ARA_VECTOR_STORE_DIR": "indexes/vectors",
            "ARA_DL_SEED": "17",
            "ARA_DL_QUESTIONS_PER_CHUNK": "3",
            "ARA_DL_PUBLIC_MAX_QUERIES": "72",
            "ARA_DL_MAX_LENGTH": "128",
            "ARA_DL_BATCH_SIZE": "2",
            "ARA_DL_EPOCHS": "5",
            "ARA_DL_LEARNING_RATE": "0.001",
            "ARA_DL_EARLY_STOPPING_PATIENCE": "4",
            "ARA_DL_CHECKPOINT_PATH": "checkpoints/test.pt",
            "ARA_DL_EXPORT_PATH": "exports/test.pt",
            "ARA_DL_USE_SYNTHETIC_PAIRS": "false",
            "ARA_DL_USE_SCORER": "true",
            "ARA_DL_DENSE_MODEL": "tiny-dense-test",
            "ARA_DL_EVAL_CANDIDATE_K": "12",
            "ARA_TTS_VOICE_MODEL_PATH": "voices/custom.onnx",
            "ARA_TTS_MODEL_CACHE_DIR": "cache/tts",
            "ARA_TTS_VOICE_ID": "en_US-amy-medium",
            "ARA_TTS_VOICE_REVISION": "pinned-voice-revision",
        },
    )

    assert settings.llm_model == "environment-model"
    assert settings.llm_num_predict == 512
    assert settings.llm_writer_num_predict == 320
    assert settings.data_dir == Path("corpus")
    assert settings.embedding_model == "environment-embedder"
    assert settings.retrieval_top_k == 4
    assert settings.reranker_model == "local-cross-encoder"
    assert settings.answer_minimum_evidence_score == pytest.approx(0.03)
    assert settings.answer_max_evidence_chunks == 5
    assert settings.ingest_source_dir == Path("private_docs")
    assert settings.vector_store_dir == Path("indexes/vectors")
    assert settings.bm25_index_path == Path("data/indexes/bm25.json")
    assert settings.dl_seed == 17
    assert settings.dl_questions_per_chunk == 3
    assert settings.dl_public_max_queries == 72
    assert settings.dl_max_length == 128
    assert settings.dl_batch_size == 2
    assert settings.dl_epochs == 5
    assert settings.dl_learning_rate == pytest.approx(0.001)
    assert settings.dl_early_stopping_patience == 4
    assert settings.dl_checkpoint_path == Path("checkpoints/test.pt")
    assert settings.dl_export_path == Path("exports/test.pt")
    assert settings.dl_use_synthetic_pairs is False
    assert settings.dl_use_scorer is True
    assert settings.dl_dense_model == "tiny-dense-test"
    assert settings.dl_eval_candidate_k == 12
    assert settings.tts_voice_model_path == Path("voices/custom.onnx")
    assert settings.tts_model_cache_dir == Path("cache/tts")
    assert settings.tts_voice_id == "en_US-amy-medium"
    assert settings.tts_voice_revision == "pinned-voice-revision"


def test_missing_yaml_uses_defaults(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "missing.yaml", tmp_path / "missing.env", environ={})

    assert settings.llm_model == "qwen2.5:1.5b"
    assert settings.embedding_model == "embeddinggemma"
    assert settings.reranker_model == "cross-encoder/ms-marco-MiniLM-L6-v2"
    assert settings.answer_minimum_evidence_score == pytest.approx(0.012)
    assert settings.answer_max_evidence_chunks == 8
    assert settings.ingest_source_dir == Path("data/sample_corpus")
    assert settings.vector_store_dir == Path("data/indexes/chroma")
    assert settings.llm_request_timeout_seconds == 120
    assert settings.llm_num_predict == 768
    assert settings.llm_writer_num_predict == 768
    assert settings.dl_seed == 42
    assert settings.dl_data_path == Path("data/dl_data/synthetic_pairs_offline.jsonl")
    assert settings.dl_public_data_dir == Path("data/dl_data/scifact_subset")
    assert settings.dl_public_max_queries == 693
    assert settings.dl_model_revision == "df500e56a59fc34f37322735a40eff666200312e"
    assert settings.dl_model_cache_dir == Path("models/huggingface")
    assert settings.dl_max_length == 256
    assert settings.dl_batch_size == 4
    assert settings.dl_epochs == 3
    assert settings.dl_learning_rate == pytest.approx(2e-5)
    assert settings.dl_weight_decay == pytest.approx(0.01)
    assert settings.dl_early_stopping_patience == 2
    assert settings.dl_checkpoint_path == Path("models/checkpoints/reranker.pt")
    assert settings.dl_export_path == Path("models/exported/reranker.pt")
    assert settings.dl_curves_path == Path("outputs/dl_training_loss.png")
    assert settings.dl_metrics_path == Path("outputs/dl_training_metrics.json")
    assert settings.dl_use_synthetic_pairs is True
    assert settings.dl_use_scorer is False
    assert settings.dl_dense_model == "sentence-transformers/all-MiniLM-L6-v2"
    assert settings.dl_dense_model_revision == "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    assert settings.dl_eval_candidate_k == 20
    assert settings.dl_eval_batch_size == 16
    assert settings.dl_eval_metrics_path == Path("outputs/dl_evaluation_metrics.json")
    assert settings.dl_error_analysis_path == Path("outputs/dl_error_analysis.json")
    assert settings.dl_dense_embeddings_cache_path == Path(
        "data/indexes/dl_eval_test_embeddings.pt"
    )
    assert settings.dl_random_negative_checkpoint_path == Path(
        "models/checkpoints/reranker_random_negatives.pt"
    )
    assert settings.tts_voice_model_path == Path("models/tts/en_US-sam-medium.onnx")
    assert settings.tts_model_cache_dir == Path("models/huggingface/tts")
    assert settings.tts_voice_id == "en_US-sam-medium"
    assert settings.tts_voice_revision == "b145f2ac26522d6a2ccde0164b7b0e48b1e3199c"


def test_tts_values_load_from_yaml(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        "paths:\n  tts_voice_model_path: voice/model.onnx\n"
        "  tts_model_cache_dir: voice/cache\n"
        "tts:\n  voice_id: en_US-amy-medium\n  voice_revision: commit123\n",
        encoding="utf-8",
    )

    settings = load_settings(config, tmp_path / "missing.env", environ={})

    assert settings.tts_voice_model_path == Path("voice/model.onnx")
    assert settings.tts_model_cache_dir == Path("voice/cache")
    assert settings.tts_voice_id == "en_US-amy-medium"
    assert settings.tts_voice_revision == "commit123"


def test_invalid_configuration_section_is_rejected(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    config.write_text("llm: nope\n", encoding="utf-8")

    with pytest.raises(ValueError, match="YAML mappings"):
        load_settings(config, tmp_path / "missing.env", environ={})


def test_settings_validate_ranges() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, retrieval_chunk_overlap=-1)
