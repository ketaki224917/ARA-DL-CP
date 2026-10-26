"""MCP interface for the local trained chunk relevance scorer."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, TypeVar

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, StrictStr

from ara.mcp_servers.common import (
    ToolNotFoundError,
    error_payload,
    get_server_logger,
    log_tool_call,
    require_text,
    require_text_list,
)
from ara.rag.vectorstore import ChromaVectorStore, VectorStore

if TYPE_CHECKING:
    from ara.config import Settings

_MAX_QUERY_LENGTH = 2_000
_MAX_CHUNK_IDS = 50
_MAX_CHUNK_ID_LENGTH = 128
_FORMAT_VERSION = 1
_T = TypeVar("_T")
logger = logging.getLogger(__name__)


class ChunkScore(BaseModel):
    """Calibrated relevance and optional credibility probabilities for one chunk."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    relevance_score: float
    credibility_score: float | None


class ScoreChunksResponse(BaseModel):
    """Machine-readable status and scores from the custom model service."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "not_ready"]
    scores: list[ChunkScore]
    message: str | None


class DLModelService:
    """Lazy local inference service with injectable store/model seams for tests."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        vector_store: VectorStore | None = None,
        scorer: Any | None = None,
        tokenizer: Any | None = None,
    ) -> None:
        self._settings = settings
        self._vector_store = vector_store
        self._scorer = scorer
        self._tokenizer = tokenizer

    def score_chunks(self, query: str, chunk_ids: list[str]) -> ScoreChunksResponse:
        """Score up to 50 indexed chunks, returning probabilities in request order."""
        normalized_query = require_text(query, "query", max_length=_MAX_QUERY_LENGTH)
        normalized_ids = require_text_list(
            chunk_ids,
            "chunk_ids",
            max_items=_MAX_CHUNK_IDS,
            max_item_length=_MAX_CHUNK_ID_LENGTH,
        )
        settings = self._resolve_settings()
        if not self._ensure_model(settings):
            return ScoreChunksResponse(
                status="not_ready",
                scores=[],
                message=(
                    f"The exported scorer is missing at {settings.dl_export_path}; "
                    "train and export the model before scoring."
                ),
            )

        chunks = self._resolve_vector_store(settings).get(normalized_ids)
        chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        if set(chunks_by_id) != set(normalized_ids):
            raise ToolNotFoundError("One or more requested chunk IDs are not in the index.")
        passages = [chunks_by_id[chunk_id].text for chunk_id in normalized_ids]
        scores = self._score_pairs(normalized_query, normalized_ids, passages, settings)
        return ScoreChunksResponse(status="ready", scores=scores, message=None)

    def _resolve_settings(self) -> Settings:
        if self._settings is None:
            from ara.config import load_settings

            self._settings = load_settings()
        return self._settings

    def _resolve_vector_store(self, settings: Settings) -> VectorStore:
        if self._vector_store is None:
            self._vector_store = ChromaVectorStore(settings.vector_store_dir)
        return self._vector_store

    def _ensure_model(self, settings: Settings) -> bool:
        if self._scorer is not None and self._tokenizer is not None:
            return True
        if self._scorer is not None or self._tokenizer is not None:
            raise RuntimeError("Both scorer and tokenizer must be configured together.")
        bundle_path = settings.dl_export_path
        if not bundle_path.is_file():
            logger.info("Custom scorer is not ready; exported bundle is missing at %s", bundle_path)
            return False

        import torch

        bundle = torch.load(bundle_path, map_location="cpu", weights_only=True)
        if not isinstance(bundle, Mapping):
            raise ValueError("Exported scorer bundle must contain a mapping.")
        if bundle.get("format_version") != _FORMAT_VERSION:
            raise ValueError("Exported scorer bundle format is unsupported.")
        if bundle.get("model_name") != settings.reranker_model:
            raise ValueError("Exported scorer model name does not match configuration.")
        if bundle.get("model_revision") != settings.dl_model_revision:
            raise ValueError("Exported scorer revision does not match configuration.")
        credibility_head = bundle.get("credibility_head")
        state_dict = bundle.get("model_state_dict")
        if not isinstance(credibility_head, bool) or not isinstance(state_dict, Mapping):
            raise ValueError("Exported scorer bundle is missing model metadata or weights.")

        from ara.dl.model import CrossEncoderScorer, load_pair_tokenizer

        self._scorer = CrossEncoderScorer.from_pretrained(
            settings,
            credibility_head=credibility_head,
        )
        self._scorer.load_state_dict(state_dict)
        self._tokenizer = load_pair_tokenizer(settings)
        logger.info("Loaded exported custom scorer from %s", bundle_path)
        return True

    def _score_pairs(
        self,
        query: str,
        chunk_ids: Sequence[str],
        passages: Sequence[str],
        settings: Settings,
    ) -> list[ChunkScore]:
        import torch

        from ara.dl.model import available_device

        if self._scorer is None or self._tokenizer is None:
            raise RuntimeError("Scorer initialization did not complete.")
        device = available_device()
        self._scorer.to(device)
        self._scorer.eval()
        relevance: list[float] = []
        credibility: list[float | None] = []
        for offset in range(0, len(passages), settings.dl_batch_size):
            batch_passages = passages[offset : offset + settings.dl_batch_size]
            encoded = self._tokenizer(
                [query] * len(batch_passages),
                list(batch_passages),
                padding=True,
                truncation=True,
                max_length=settings.dl_max_length,
                return_tensors="pt",
            )
            model_inputs = {name: value.to(device) for name, value in encoded.items()}
            with torch.inference_mode():
                output = self._scorer(**model_inputs)
            relevance.extend(
                float(value)
                for value in torch.sigmoid(output.relevance_logits).detach().cpu().tolist()
            )
            credibility_logits = output.credibility_logits
            if credibility_logits is None:
                credibility.extend([None] * len(batch_passages))
            else:
                credibility.extend(
                    float(value)
                    for value in torch.sigmoid(credibility_logits).detach().cpu().tolist()
                )
        if len(relevance) != len(chunk_ids) or len(credibility) != len(chunk_ids):
            raise RuntimeError("Scorer returned an unexpected number of predictions.")
        return [
            ChunkScore(
                chunk_id=chunk_id,
                relevance_score=relevance_score,
                credibility_score=credibility_score,
            )
            for chunk_id, relevance_score, credibility_score in zip(
                chunk_ids, relevance, credibility, strict=True
            )
        ]


def create_dl_model_server(service: DLModelService | None = None) -> MCPServer:
    """Build the MCP server exposing local cross-encoder inference."""
    model_service = service if service is not None else DLModelService()
    server = MCPServer(
        name="ARA DL Model",
        instructions=(
            "Score indexed chunks with ARA's locally trained relevance model. "
            "The tool returns status not_ready until a model has been trained and exported."
        ),
    )

    @server.tool()
    def score_chunks(query: StrictStr, chunk_ids: list[StrictStr]) -> ScoreChunksResponse:
        """Return relevance and optional credibility probabilities for chunk IDs."""
        return _invoke_tool(
            "score_chunks",
            lambda: model_service.score_chunks(query, chunk_ids),
        )

    return server


def _invoke_tool(tool_name: str, operation: Callable[[], _T]) -> _T:
    """Log tool metadata and translate failures into safe MCP tool errors."""
    logger = get_server_logger("dl-model")
    try:
        with log_tool_call(logger, server_name="dl-model", tool_name=tool_name):
            return operation()
    except Exception as exc:
        payload = json.dumps(error_payload(exc), ensure_ascii=False, separators=(",", ":"))
        raise ToolError(payload) from exc


def main() -> None:
    """Run the DL model MCP server over stdio."""
    create_dl_model_server().run()


if __name__ == "__main__":
    main()
