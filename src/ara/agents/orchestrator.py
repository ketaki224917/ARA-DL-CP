"""Hand-rolled Planner → Researcher orchestration with JSONL tracing."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from ara.agents.researcher import ResearchSummary
from ara.agents.state import AgentState, PlanTask
from ara.agents.trace import JSONLTraceWriter, TraceEvent, make_trace_event

TraceCallback = Callable[[TraceEvent], None]


class PlannerComponent(Protocol):
    """Planning operation needed by the orchestration state machine."""

    def plan(self, topic: str) -> list[PlanTask]: ...


class ResearcherComponent(Protocol):
    """Research operation needed by the orchestration state machine."""

    async def research(
        self,
        state: AgentState,
        *,
        trace_callback: TraceCallback | None = None,
    ) -> ResearchSummary: ...


class Orchestrator:
    """Run planning and research sequentially while keeping a per-run JSONL trace."""

    def __init__(
        self,
        planner: PlannerComponent,
        researcher: ResearcherComponent,
        *,
        trace_dir: Path | str = Path("traces"),
    ) -> None:
        self._planner = planner
        self._researcher = researcher
        self._trace_dir = Path(trace_dir)

    async def run(self, state: AgentState) -> AgentState:
        """Plan when needed, research eligible tasks, and update run lifecycle state."""
        if state.run_metadata.status in {"completed", "failed"}:
            raise ValueError("orchestrator requires a pending or running AgentState")
        writer = JSONLTraceWriter(state.run_metadata.run_id, self._trace_dir)
        started = time.perf_counter()
        state.run_metadata.status = "running"
        state.run_metadata.updated_at = datetime.now(UTC)

        try:
            writer.write(
                make_trace_event(
                    state.run_metadata.run_id,
                    agent="orchestrator",
                    event="run_started",
                    result_summary=f"topic_length={len(state.topic)}",
                )
            )
            if state.plan:
                writer.write(
                    make_trace_event(
                        state.run_metadata.run_id,
                        agent="planner",
                        event="plan_reused",
                        result_summary=f"tasks={len(state.plan)}",
                    )
                )
            else:
                plan_started = time.perf_counter()
                plan = self._planner.plan(state.topic)
                state.plan = plan
                writer.write(
                    make_trace_event(
                        state.run_metadata.run_id,
                        agent="planner",
                        event="plan_created",
                        result_summary=(
                            f"tasks={len(plan)}; task_ids="
                            + ",".join(task.task_id for task in plan)
                        ),
                        latency_ms=(time.perf_counter() - plan_started) * 1_000,
                    )
                )

            research_started = time.perf_counter()
            summary = await self._researcher.research(
                state,
                trace_callback=writer.write,
            )
            state.run_metadata.status = "completed"
            state.run_metadata.updated_at = datetime.now(UTC)
            writer.write(
                make_trace_event(
                    state.run_metadata.run_id,
                    agent="researcher",
                    event="research_completed",
                    result_summary=(
                        f"tool_calls={summary.tool_calls_made}; "
                        f"budget_exhausted="
                        f"{summary.tool_budget_exhausted or summary.evidence_budget_exhausted}"
                    ),
                    latency_ms=(time.perf_counter() - research_started) * 1_000,
                )
            )
            writer.write(
                make_trace_event(
                    state.run_metadata.run_id,
                    agent="orchestrator",
                    event="run_completed",
                    result_summary=(
                        f"tasks_completed={len(summary.completed_task_ids)}; "
                        f"tasks_blocked={len(summary.blocked_task_ids)}; "
                        f"tool_calls={summary.tool_calls_made}; "
                        f"evidence_added={len(summary.evidence_ids_added)}"
                    ),
                    latency_ms=(time.perf_counter() - started) * 1_000,
                )
            )
            return state
        except Exception as exc:
            state.run_metadata.status = "failed"
            state.run_metadata.updated_at = datetime.now(UTC)
            writer.write(
                make_trace_event(
                    state.run_metadata.run_id,
                    agent="orchestrator",
                    event="run_failed",
                    result_summary=f"error_type={type(exc).__name__}",
                    latency_ms=(time.perf_counter() - started) * 1_000,
                )
            )
            raise


__all__ = ["Orchestrator", "PlannerComponent", "ResearcherComponent", "TraceCallback"]
