"""Deterministic stdio MCP fixture for the offline end-to-end research demo."""

from __future__ import annotations

from mcp.server import MCPServer
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr


class SyntheticSearchHit(BaseModel):
    """Clearly synthetic evidence returned by the fixture server."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = "chunk:synthetic-offline-demo"
    text: str = (
        "Synthetic fixture evidence: hybrid retrieval combines dense and lexical "
        "signals to rank candidate documents."
    )
    source: str = "SYNTHETIC_FIXTURE_only.md"
    page: int = 1
    score: float = 0.9
    dense_rank: int = 1
    bm25_rank: int = 1
    dense_score: float = 0.82
    bm25_score: float = 1.7


class SyntheticSearchResponse(BaseModel):
    """Structured search output compatible with the ARA researcher."""

    model_config = ConfigDict(extra="forbid")

    results: list[SyntheticSearchHit]


server = MCPServer(
    name="ARA Synthetic Research Fixture",
    instructions="Returns synthetic evidence for offline end-to-end tests only.",
)


@server.tool()
def search_knowledge_base(
    query: StrictStr,
    top_k: StrictInt = 5,
    candidate_k: StrictInt = 20,
) -> SyntheticSearchResponse:
    """Return one synthetic local evidence chunk."""
    if not query.strip() or top_k < 1 or candidate_k < top_k:
        raise ValueError("invalid synthetic search arguments")
    return SyntheticSearchResponse(results=[SyntheticSearchHit()])


if __name__ == "__main__":
    server.run()
