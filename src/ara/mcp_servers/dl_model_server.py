"""Typed MCP interface for the future custom chunk relevance scorer."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Literal, TypeVar

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, StrictStr

from ara.mcp_servers.common import (
    error_payload,
    get_server_logger,
    log_tool_call,
    require_text,
    require_text_list,
)

_MAX_QUERY_LENGTH = 2_000
_MAX_CHUNK_IDS = 50
_MAX_CHUNK_ID_LENGTH = 128
_T = TypeVar("_T")


class ChunkScore(BaseModel):
    """Score fields the trained custom model will populate in P5.6."""

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
    """P2.4 placeholder; the trained scorer is added and loaded in P5.6."""

    def score_chunks(self, query: str, chunk_ids: list[str]) -> ScoreChunksResponse:
        """Validate a scoring request and return an explicit not-ready response."""
        require_text(query, "query", max_length=_MAX_QUERY_LENGTH)
        require_text_list(
            chunk_ids,
            "chunk_ids",
            max_items=_MAX_CHUNK_IDS,
            max_item_length=_MAX_CHUNK_ID_LENGTH,
        )
        return ScoreChunksResponse(
            status="not_ready",
            scores=[],
            message="The custom chunk scoring model is not trained or loaded.",
        )


def create_dl_model_server(service: DLModelService | None = None) -> MCPServer:
    """Build the MCP server for custom chunk scoring."""
    model_service = service if service is not None else DLModelService()
    server = MCPServer(
        name="ARA DL Model",
        instructions=(
            "Score candidate chunks with ARA's custom relevance and credibility model. "
            "The current implementation returns status not_ready until the model is trained."
        ),
    )

    @server.tool()
    def score_chunks(query: StrictStr, chunk_ids: list[StrictStr]) -> ScoreChunksResponse:
        """Return relevance and optional credibility scores for candidate chunk IDs."""
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
