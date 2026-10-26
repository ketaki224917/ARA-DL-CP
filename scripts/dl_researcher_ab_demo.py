"""Run a controlled researcher A/B through the local DL MCP server."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from mcp import Client
from mcp.server import MCPServer
from mcp.types import CallToolResult

from ara.agents.researcher import Researcher
from ara.agents.state import AgentState, PlanTask
from ara.agents.trace import TraceEvent
from ara.config import load_settings
from ara.llm.client import ChatMessage, ToolCall
from ara.mcp_servers.dl_model_server import DLModelService, create_dl_model_server
from ara.mcp_servers.rag_server import SearchHit, SearchResponse
from ara.rag.chunking import DocumentChunk
from ara.rag.vectorstore import InMemoryVectorStore

logger = logging.getLogger(__name__)
_QUERY = "Does folic acid and vitamin B6 intake reduce homocysteine levels?"
_RECORDS = (
    (
        "chunk:other",
        "The observational study assessed vitamin intake and coronary heart disease risk "
        "but did not report homocysteine changes.",
        "other.md",
    ),
    (
        "chunk:gold",
        "The clinical trial found folic acid and vitamin B6 supplementation reduced plasma "
        "homocysteine levels compared with placebo.",
        "gold.md",
    ),
)


class _ScriptedLLM:
    """Select one local search and then stop each controlled run."""

    def __init__(self) -> None:
        self._calls = [
            [ToolCall(name="search_knowledge_base", arguments={"query": _QUERY})],
            [],
            [],
            [],
        ]

    def tool_calls(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[Mapping[str, Any]],
        *,
        temperature: float | None = None,
    ) -> list[ToolCall]:
        del messages, tools
        if temperature != 0.0 or not self._calls:
            raise RuntimeError("unexpected scripted LLM call")
        return self._calls.pop(0)


class _MCPRouter:
    """Route named server calls through the MCP SDK's in-memory client."""

    def __init__(self, servers: Mapping[str, MCPServer]) -> None:
        self._servers = servers

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Mapping[str, object],
        *,
        timeout_seconds: float | None = None,
        retries: int | None = None,
    ) -> CallToolResult:
        del timeout_seconds, retries
        if server_name not in self._servers:
            raise ValueError(f"unknown MCP server: {server_name}")
        async with Client(self._servers[server_name]) as client:
            return await client.call_tool(tool_name, dict(arguments))


def _make_rag_server() -> tuple[MCPServer, InMemoryVectorStore]:
    server = MCPServer(name="ARA controlled RAG")
    store = InMemoryVectorStore()
    store.upsert(
        [
            DocumentChunk(
                chunk_id,
                text,
                source,
                None,
                0,
                len(text),
            )
            for chunk_id, text, source in _RECORDS
        ],
        [[1.0], [1.0]],
    )

    @server.tool()
    def search_knowledge_base(
        query: str,
        top_k: int = 5,
        candidate_k: int = 20,
    ) -> SearchResponse:
        """Return a controlled retrieval order with the non-gold passage first."""
        del query, top_k, candidate_k
        return SearchResponse(
            results=[
                SearchHit(
                    chunk_id=chunk_id,
                    text=text,
                    source=source,
                    page=None,
                    score=0.92 - 0.1 * index,
                    dense_rank=index + 1,
                    bm25_rank=index + 1,
                    dense_score=0.9 - 0.1 * index,
                    bm25_score=1.0 - 0.1 * index,
                )
                for index, (chunk_id, text, source) in enumerate(_RECORDS)
            ]
        )

    return server, store


async def _run_once(
    *,
    enabled: bool,
    rag_server: MCPServer,
    dl_server: MCPServer,
) -> dict[str, Any]:
    state = AgentState(
        topic="Folate and homocysteine",
        plan=[
            PlanTask(task_id="task-1", question="Assess the direct evidence."),
            PlanTask(task_id="task-2", question="Check study limitations."),
            PlanTask(task_id="task-3", question="Summarize the findings."),
        ],
    )
    events: list[TraceEvent] = []
    summary = await Researcher(
        _MCPRouter({"rag": rag_server, "dl-model": dl_server}),
        _ScriptedLLM(),
        local_top_k=2,
        use_dl_scorer=enabled,
    ).research(state, trace_callback=events.append)
    ranked_ids = list(state.evidence_store)
    gold_rank = ranked_ids.index("chunk:gold") + 1
    return {
        "scorer_enabled": enabled,
        "ranked_chunk_ids": ranked_ids,
        "gold_rank": gold_rank,
        "gold_mrr": 1 / gold_rank,
        "mcp_tool_calls": summary.tool_calls_made,
        "scorer_status": next(
            (
                event.result_summary
                for event in events
                if event.server_name == "dl-model" and event.tool_name == "score_chunks"
            ),
            "disabled",
        ),
    }


async def run_demo() -> dict[str, Any]:
    """Run the baseline and configured scorer on the same two passage fixture."""
    settings = load_settings()
    if not settings.dl_export_path.is_file():
        raise FileNotFoundError(
            f"Exported scorer missing at {settings.dl_export_path}; "
            "run ara.dl.train and ara.dl.export first."
        )
    rag_server, store = _make_rag_server()
    dl_server = create_dl_model_server(DLModelService(settings=settings, vector_store=store))
    baseline = await _run_once(enabled=False, rag_server=rag_server, dl_server=dl_server)
    reranked = await _run_once(enabled=True, rag_server=rag_server, dl_server=dl_server)
    return {
        "experiment": "controlled two-passage researcher/MCP wiring demo",
        "query": _QUERY,
        "interpretation": (
            "One synthetic fixture verifies the MCP integration and evidence ordering; "
            "it is not a statistical quality evaluation."
        ),
        "systems": [baseline, reranked],
    }


def _write_artifacts(payload: Mapping[str, Any]) -> tuple[Path, Path]:
    output_dir = load_settings().output_dir
    json_path = output_dir / "dl_researcher_ab.json"
    markdown_path = output_dir / "dl_researcher_ab.md"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    systems = payload["systems"]
    rows = [
        "# P5.7 Researcher Scorer A/B",
        "",
        str(payload["interpretation"]),
        "",
        "| System | Gold rank | Gold MRR | MCP calls | Scorer status |",
        "|---|---:|---:|---:|---|",
    ]
    for row in systems:
        name = "DL scorer enabled" if row["scorer_enabled"] else "Baseline"
        rows.append(
            f"| {name} | {row['gold_rank']} | {row['gold_mrr']:.4f} | "
            f"{row['mcp_tool_calls']} | {row['scorer_status']} |"
        )
    markdown_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return json_path, markdown_path


def main() -> int:
    """Run the demo and persist its output artifacts."""
    from ara.logging_setup import configure_logging

    configure_logging()
    payload = asyncio.run(run_demo())
    json_path, markdown_path = _write_artifacts(payload)
    logger.info("Saved controlled A/B artifacts to %s and %s", json_path, markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
