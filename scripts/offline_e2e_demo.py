"""Run the Planner → Researcher → MCP path offline with synthetic test doubles."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx
from mcp import StdioServerParameters

from ara.agents.orchestrator import Orchestrator
from ara.agents.planner import Planner
from ara.agents.researcher import Researcher
from ara.agents.state import AgentState, RunMetadata
from ara.config import Settings
from ara.llm.client import ChatMessage, OllamaClient, ToolCall
from ara.mcp_client.client import MCPClient

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE_SERVER = Path(__file__).with_name("offline_research_mcp_server.py")
_PLAN = {
    "tasks": [
        {
            "task_id": "find_local_example",
            "question": "Find the synthetic local retrieval example.",
            "rationale": "Exercise local evidence retrieval through MCP.",
            "depends_on": [],
        },
        {
            "task_id": "review_rank_signals",
            "question": "Identify the ranking signals in the fixture.",
            "rationale": "Cover the retrieval mechanism from another angle.",
            "depends_on": [],
        },
        {
            "task_id": "summarize_limits",
            "question": "Identify limitations that should be checked in real sources.",
            "rationale": "Keep the demonstration explicit about its synthetic evidence.",
            "depends_on": [],
        },
    ]
}


class ScriptedToolCalls:
    """Make one deterministic local search choice, then finish each task."""

    def __init__(self) -> None:
        self._selected = False

    def tool_calls(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[Mapping[str, Any]],
        *,
        temperature: float | None = None,
    ) -> list[ToolCall]:
        if not messages or not tools or temperature != 0.0:
            raise ValueError("unexpected offline tool-call request")
        if not self._selected:
            self._selected = True
            return [ToolCall(name="search_knowledge_base", arguments={"query": "hybrid retrieval"})]
        return []


def _mock_ollama_client() -> tuple[OllamaClient, httpx.Client]:
    def respond(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps(_PLAN, ensure_ascii=False)}},
        )

    http_client = httpx.Client(transport=httpx.MockTransport(respond))
    llm_client = OllamaClient(Settings.model_construct(), http_client=http_client)
    return llm_client, http_client


async def run_demo(trace_dir: Path, run_id: str) -> AgentState:
    llm_client, http_client = _mock_ollama_client()
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-u", str(_FIXTURE_SERVER)],
        cwd=str(_PROJECT_ROOT),
    )
    try:
        async with MCPClient(timeout_seconds=10, retries=0) as mcp_client:
            await mcp_client.connect("rag", parameters)
            state = AgentState(
                topic="Offline synthetic research run for hybrid retrieval",
                run_metadata=RunMetadata(run_id=run_id),
            )
            orchestrator = Orchestrator(
                Planner(llm_client, max_retries=0),
                Researcher(mcp_client, ScriptedToolCalls(), max_tool_calls=3),
                trace_dir=trace_dir,
            )
            await orchestrator.run(state)
            if state.run_metadata.status != "completed":
                raise RuntimeError("offline orchestration did not complete")
            if state.plan and any(task.status != "completed" for task in state.plan):
                raise RuntimeError("offline research left a plan task incomplete")
            if "chunk:synthetic-offline-demo" not in state.evidence_store:
                raise RuntimeError("offline MCP server returned no synthetic evidence")
            return state
    finally:
        http_client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-dir", type=Path, default=Path("traces"))
    parser.add_argument("--run-id", default=None)
    arguments = parser.parse_args()
    run_id = arguments.run_id or f"offline-demo-{uuid.uuid4().hex}"
    state = asyncio.run(run_demo(arguments.trace_dir, run_id))
    print(
        json.dumps(
            {
                "run_id": state.run_metadata.run_id,
                "status": state.run_metadata.status,
                "task_statuses": {task.task_id: task.status for task in state.plan},
                "evidence_ids": list(state.evidence_store),
                "trace_path": str(arguments.trace_dir / f"{run_id}.jsonl"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
