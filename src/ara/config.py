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
}


class Settings(BaseSettings):
    """Validated runtime settings for all ARA components."""

    model_config = SettingsConfigDict(env_prefix="ARA_", extra="ignore")

    llm_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:11434")
    llm_model: str = "qwen2.5:1.5b"
    llm_request_timeout_seconds: float = Field(default=120, gt=0)
    llm_temperature: float = Field(default=0.0, ge=0, le=2)
    embedding_model: str = "embeddinggemma"
    embedding_cache_path: Path = Path("data/indexes/embeddings.sqlite3")
    data_dir: Path = Path("data")
    ingest_source_dir: Path = Path("data/sample_corpus")
    vector_store_dir: Path = Path("data/indexes/chroma")
    bm25_index_path: Path = Path("data/indexes/bm25.json")
    ingest_manifest_path: Path = Path("data/indexes/ingest_manifest.json")
    dl_data_path: Path = Path("data/dl_data/synthetic_pairs.jsonl")
    dl_public_data_dir: Path = Path("data/dl_data/scifact_subset")
    dl_public_archive_path: Path = Path("data/dl_data/cache/scifact.tar.gz")
    dl_public_max_queries: int = Field(default=200, ge=3, le=1000)
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
    values: dict[str, Any] = {
        "llm_base_url": llm.get("base_url"),
        "llm_model": llm.get("model"),
        "llm_request_timeout_seconds": llm.get("request_timeout_seconds"),
        "llm_temperature": llm.get("temperature"),
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

