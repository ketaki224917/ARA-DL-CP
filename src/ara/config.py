"""Application configuration loaded from YAML with dotenv/environment overrides."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FIELDS = {
    "ARA_LLM_BASE_URL": "llm_base_url",
    "ARA_LLM_MODEL": "llm_model",
    "ARA_LLM_REQUEST_TIMEOUT_SECONDS": "llm_request_timeout_seconds",
    "ARA_LLM_TEMPERATURE": "llm_temperature",
    "ARA_LLM_NUM_PREDICT": "llm_num_predict",
    "ARA_LLM_WRITER_NUM_PREDICT": "llm_writer_num_predict",
    "ARA_EMBEDDING_MODEL": "embedding_model",
    "ARA_EMBEDDING_CACHE_PATH": "embedding_cache_path",
    "ARA_DATA_DIR": "data_dir",
    "ARA_OUTPUT_DIR": "output_dir",
    "ARA_TRACE_DIR": "trace_dir",
    "ARA_RETRIEVAL_CHUNK_SIZE": "retrieval_chunk_size",
    "ARA_RETRIEVAL_CHUNK_OVERLAP": "retrieval_chunk_overlap",
    "ARA_RETRIEVAL_TOP_K": "retrieval_top_k",
    "ARA_RERANKER_MODEL": "reranker_model",
    "ARA_ANSWER_MINIMUM_EVIDENCE_SCORE": "answer_minimum_evidence_score",
    "ARA_ANSWER_MAX_EVIDENCE_CHUNKS": "answer_max_evidence_chunks",
    "ARA_INGEST_SOURCE_DIR": "ingest_source_dir",
    "ARA_VECTOR_STORE_DIR": "vector_store_dir",
    "ARA_BM25_INDEX_PATH": "bm25_index_path",
    "ARA_INGEST_MANIFEST_PATH": "ingest_manifest_path",
    "ARA_DL_DATA_PATH": "dl_data_path",
    "ARA_DL_SEED": "dl_seed",
    "ARA_DL_QUESTIONS_PER_CHUNK": "dl_questions_per_chunk",
    "ARA_DL_CANDIDATE_K": "dl_candidate_k",
    "ARA_DL_NEGATIVE_POOL_SIZE": "dl_negative_pool_size",
    "ARA_DL_PUBLIC_DATA_DIR": "dl_public_data_dir",
    "ARA_DL_PUBLIC_ARCHIVE_PATH": "dl_public_archive_path",
    "ARA_DL_PUBLIC_MAX_QUERIES": "dl_public_max_queries",
    "ARA_DL_MODEL_REVISION": "dl_model_revision",
    "ARA_DL_MODEL_CACHE_DIR": "dl_model_cache_dir",
    "ARA_DL_MAX_LENGTH": "dl_max_length",
    "ARA_DL_BATCH_SIZE": "dl_batch_size",
    "ARA_DL_CREDIBILITY_HEAD": "dl_credibility_head",
    "ARA_DL_EPOCHS": "dl_epochs",
    "ARA_DL_LEARNING_RATE": "dl_learning_rate",
    "ARA_DL_WEIGHT_DECAY": "dl_weight_decay",
    "ARA_DL_EARLY_STOPPING_PATIENCE": "dl_early_stopping_patience",
    "ARA_DL_EARLY_STOPPING_MIN_DELTA": "dl_early_stopping_min_delta",
    "ARA_DL_CHECKPOINT_PATH": "dl_checkpoint_path",
    "ARA_DL_EXPORT_PATH": "dl_export_path",
    "ARA_DL_CURVES_PATH": "dl_curves_path",
    "ARA_DL_METRICS_PATH": "dl_metrics_path",
    "ARA_DL_USE_SYNTHETIC_PAIRS": "dl_use_synthetic_pairs",
    "ARA_DL_USE_SCORER": "dl_use_scorer",
    "ARA_DL_DENSE_MODEL": "dl_dense_model",
    "ARA_DL_DENSE_MODEL_REVISION": "dl_dense_model_revision",
    "ARA_DL_EVAL_CANDIDATE_K": "dl_eval_candidate_k",
    "ARA_DL_EVAL_BATCH_SIZE": "dl_eval_batch_size",
    "ARA_DL_EVAL_METRICS_PATH": "dl_eval_metrics_path",
    "ARA_DL_ERROR_ANALYSIS_PATH": "dl_error_analysis_path",
    "ARA_DL_DENSE_EMBEDDINGS_CACHE_PATH": "dl_dense_embeddings_cache_path",
    "ARA_DL_RANDOM_NEGATIVE_CHECKPOINT_PATH": "dl_random_negative_checkpoint_path",
    "ARA_TTS_VOICE_MODEL_PATH": "tts_voice_model_path",
    "ARA_TTS_MODEL_CACHE_DIR": "tts_model_cache_dir",
    "ARA_TTS_VOICE_ID": "tts_voice_id",
    "ARA_TTS_VOICE_REVISION": "tts_voice_revision",
}


class Settings(BaseSettings):
    """Validated runtime settings for all ARA components."""

    model_config = SettingsConfigDict(env_prefix="ARA_", extra="ignore")

    llm_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:11434")
    llm_model: str = "qwen2.5:1.5b"
    llm_request_timeout_seconds: float = Field(default=120, gt=0)
    llm_temperature: float = Field(default=0.0, ge=0, le=2)
    llm_num_predict: int = Field(default=768, ge=64, le=8192)
    llm_writer_num_predict: int = Field(default=384, ge=64, le=8192)
    embedding_model: str = "embeddinggemma"
    embedding_cache_path: Path = Path("data/indexes/embeddings.sqlite3")
    data_dir: Path = Path("data")
    ingest_source_dir: Path = Path("data/sample_corpus")
    vector_store_dir: Path = Path("data/indexes/chroma")
    bm25_index_path: Path = Path("data/indexes/bm25.json")
    ingest_manifest_path: Path = Path("data/indexes/ingest_manifest.json")
    dl_data_path: Path = Path("data/dl_data/synthetic_pairs_offline.jsonl")
    dl_public_data_dir: Path = Path("data/dl_data/scifact_subset")
    dl_public_archive_path: Path = Path("data/dl_data/cache/scifact.tar.gz")
    dl_public_max_queries: int = Field(default=200, ge=3, le=1000)
    dl_model_revision: str = "df500e56a59fc34f37322735a40eff666200312e"
    dl_model_cache_dir: Path = Path("models/huggingface")
    dl_max_length: int = Field(default=256, ge=16, le=512)
    dl_batch_size: int = Field(default=4, ge=1, le=64)
    dl_credibility_head: bool = False
    dl_epochs: int = Field(default=3, ge=1, le=100)
    dl_learning_rate: float = Field(default=2e-5, gt=0, le=1)
    dl_weight_decay: float = Field(default=0.01, ge=0, le=1)
    dl_early_stopping_patience: int = Field(default=2, ge=1, le=20)
    dl_early_stopping_min_delta: float = Field(default=0.0, ge=0, le=1)
    dl_checkpoint_path: Path = Path("models/checkpoints/reranker.pt")
    dl_export_path: Path = Path("models/exported/reranker.pt")
    dl_curves_path: Path = Path("outputs/dl_training_loss.png")
    dl_metrics_path: Path = Path("outputs/dl_training_metrics.json")
    dl_use_synthetic_pairs: bool = True
    dl_use_scorer: bool = False
    dl_dense_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    dl_dense_model_revision: str = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    dl_eval_candidate_k: int = Field(default=20, ge=1, le=200)
    dl_eval_batch_size: int = Field(default=16, ge=1, le=128)
    dl_eval_metrics_path: Path = Path("outputs/dl_evaluation_metrics.json")
    dl_error_analysis_path: Path = Path("outputs/dl_error_analysis.json")
    dl_dense_embeddings_cache_path: Path = Path("data/indexes/dl_eval_test_embeddings.pt")
    dl_random_negative_checkpoint_path: Path = Path(
        "models/checkpoints/reranker_random_negatives.pt"
    )
    tts_voice_model_path: Path = Path("models/tts/en_US-sam-medium.onnx")
    tts_model_cache_dir: Path = Path("models/huggingface/tts")
    tts_voice_id: str = "en_US-sam-medium"
    tts_voice_revision: str = "b145f2ac26522d6a2ccde0164b7b0e48b1e3199c"
    dl_seed: int = 42
    dl_questions_per_chunk: int = Field(default=2, ge=1, le=5)
    dl_candidate_k: int = Field(default=20, ge=1, le=200)
    dl_negative_pool_size: int = Field(default=1, ge=1, le=50)
    output_dir: Path = Path("outputs")
    trace_dir: Path = Path("traces")
    retrieval_chunk_size: int = Field(default=900, ge=1)
    retrieval_chunk_overlap: int = Field(default=120, ge=0)
    retrieval_top_k: int = Field(default=8, ge=1)
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L6-v2"
    answer_minimum_evidence_score: float = Field(default=0.012, ge=0)
    answer_max_evidence_chunks: int = Field(default=8, ge=1)


def load_settings(
    config_path: Path | str = "config.yaml",
    env_file: Path | str = ".env",
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Load YAML defaults, then dotenv values, then process environment overrides.

    Args:
        config_path: YAML configuration path. A missing file is allowed and uses defaults.
        env_file: Optional dotenv file, usually the local `.env`.
        environ: Environment mapping override, useful for deterministic tests.
    """
    raw_config: dict[str, Any] = {}
    yaml_path = Path(config_path)
    if yaml_path.is_file():
        loaded = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Configuration at {yaml_path} must be a YAML mapping.")
        raw_config = loaded

    llm = _mapping(raw_config.get("llm"))
    embeddings = _mapping(raw_config.get("embeddings"))
    paths = _mapping(raw_config.get("paths"))
    retrieval = _mapping(raw_config.get("retrieval"))
    dl = _mapping(raw_config.get("dl"))
    tts = _mapping(raw_config.get("tts"))
    values: dict[str, Any] = {
        "llm_base_url": llm.get("base_url"),
        "llm_model": llm.get("model"),
        "llm_request_timeout_seconds": llm.get("request_timeout_seconds"),
        "llm_temperature": llm.get("temperature"),
        "llm_num_predict": llm.get("num_predict"),
        "llm_writer_num_predict": llm.get("writer_num_predict"),
        "embedding_model": embeddings.get("model"),
        "embedding_cache_path": embeddings.get("cache_path"),
        "data_dir": paths.get("data_dir"),
        "ingest_source_dir": paths.get("ingest_source_dir"),
        "vector_store_dir": paths.get("vector_store_dir"),
        "bm25_index_path": paths.get("bm25_index_path"),
        "ingest_manifest_path": paths.get("ingest_manifest_path"),
        "dl_data_path": paths.get("dl_data_path"),
        "dl_public_data_dir": paths.get("dl_public_data_dir"),
        "dl_public_archive_path": paths.get("dl_public_archive_path"),
        "dl_public_max_queries": dl.get("public_max_queries"),
        "dl_model_revision": dl.get("model_revision"),
        "dl_model_cache_dir": paths.get("dl_model_cache_dir"),
        "dl_max_length": dl.get("max_length"),
        "dl_batch_size": dl.get("batch_size"),
        "dl_credibility_head": dl.get("credibility_head"),
        "dl_epochs": dl.get("epochs"),
        "dl_learning_rate": dl.get("learning_rate"),
        "dl_weight_decay": dl.get("weight_decay"),
        "dl_early_stopping_patience": dl.get("early_stopping_patience"),
        "dl_early_stopping_min_delta": dl.get("early_stopping_min_delta"),
        "dl_checkpoint_path": paths.get("dl_checkpoint_path"),
        "dl_export_path": paths.get("dl_export_path"),
        "dl_curves_path": paths.get("dl_curves_path"),
        "dl_metrics_path": paths.get("dl_metrics_path"),
        "dl_use_synthetic_pairs": dl.get("use_synthetic_pairs"),
        "dl_use_scorer": dl.get("use_scorer"),
        "dl_dense_model": dl.get("dense_model"),
        "dl_dense_model_revision": dl.get("dense_model_revision"),
        "dl_eval_candidate_k": dl.get("eval_candidate_k"),
        "dl_eval_batch_size": dl.get("eval_batch_size"),
        "dl_eval_metrics_path": paths.get("dl_eval_metrics_path"),
        "dl_error_analysis_path": paths.get("dl_error_analysis_path"),
        "dl_dense_embeddings_cache_path": paths.get("dl_dense_embeddings_cache_path"),
        "dl_random_negative_checkpoint_path": paths.get("dl_random_negative_checkpoint_path"),
        "tts_voice_model_path": paths.get("tts_voice_model_path"),
        "tts_model_cache_dir": paths.get("tts_model_cache_dir"),
        "tts_voice_id": tts.get("voice_id"),
        "tts_voice_revision": tts.get("voice_revision"),
        "dl_seed": dl.get("seed"),
        "dl_questions_per_chunk": dl.get("questions_per_chunk"),
        "dl_candidate_k": dl.get("candidate_k"),
        "dl_negative_pool_size": dl.get("negative_pool_size"),
        "output_dir": paths.get("output_dir"),
        "trace_dir": paths.get("trace_dir"),
        "retrieval_chunk_size": retrieval.get("chunk_size"),
        "retrieval_chunk_overlap": retrieval.get("chunk_overlap"),
        "retrieval_top_k": retrieval.get("top_k"),
        "reranker_model": retrieval.get("reranker_model"),
        "answer_minimum_evidence_score": retrieval.get("min_evidence_score"),
        "answer_max_evidence_chunks": retrieval.get("max_evidence_chunks"),
    }
    values = {key: value for key, value in values.items() if value is not None}

    dotenv_path = Path(env_file)
    file_values = dotenv_values(dotenv_path) if dotenv_path.is_file() else {}
    _apply_env(values, file_values)
    _apply_env(values, os.environ if environ is None else environ)
    return Settings.model_validate(values)


def _mapping(value: Any) -> dict[str, Any]:
    """Return a dict for a YAML section, rejecting invalid section shapes."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("Configuration sections must be YAML mappings.")
    return value


def _apply_env(values: dict[str, Any], source: Mapping[str, Any]) -> None:
    """Apply recognized environment variable names to a settings dict."""
    for env_name, field_name in _ENV_FIELDS.items():
        value = source.get(env_name)
        if value is not None:
            values[field_name] = value
