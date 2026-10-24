"""Orchestrator lifecycle and JSONL trace tests."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from ara.agents.orchestrator import Orchestrator, TraceCallback
from ara.agents.researcher import ResearchSummary
from ara.agents.state import AgentState, PlanTask, RunMetadata
from ara.agents.trace import JSONLTraceWriter, TraceEvent, make_trace_event


class FakePlanner:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.topics: list[str] = []

    def plan(self, topic: str) -> list[PlanTask]:
        self.topics.append(topic)
        if self.error is not None:
            raise self.error
        return [
            PlanTask(task_id="one", question="Question one."),
            PlanTask(task_id="two", question="Question two."),
            PlanTask(task_id="three", question="Question three."),
        ]


class FakeResearcher:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.called = False

    async def research(
        self,
        state: AgentState,
        *,
        trace_callback: TraceCallback | None = None,
    ) -> ResearchSummary:
        self.called = True
        assert state.run_metadata.status == "running"
        if self.error is not None:
            raise self.error
        if trace_callback is not None:
            trace_callback(
                make_trace_event(
                    state.run_metadata.run_id,
                    agent="researcher",
                    event="tool_call",
                    task_id="one",
                    tool_name="web_search",
                    server_name="web",
                    tool_arguments={"query": "Question one"},
                    result_summary="results=2; evidence_added=0",
                    latency_ms=2.5,
                    is_untrusted=True,
                )
            )
        return ResearchSummary(
            tool_calls_made=1,
            evidence_ids_added=["chunk:one"],
            completed_task_ids=["one", "two", "three"],
        )


def _read_events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_orchestrator_runs_planner_and_researcher_and_writes_jsonl(
    tmp_path: Path,
) -> None:
    planner = FakePlanner()
    researcher = FakeResearcher()
    state = AgentState(
        topic="A topic with evidence",
        run_metadata=RunMetadata(run_id="test-run-1"),
    )

    result = asyncio.run(Orchestrator(planner, researcher, trace_dir=tmp_path).run(state))

    assert result is state
    assert state.run_metadata.status == "completed"
    assert [task.status for task in state.plan] == ["pending", "pending", "pending"]
    assert planner.topics == ["A topic with evidence"]
    assert researcher.called
    events = _read_events(tmp_path / "test-run-1.jsonl")
    assert [event["event"] for event in events] == [
        "run_started",
        "plan_created",
        "tool_call",
        "research_completed",
        "run_completed",
    ]
    assert events[2]["tool_name"] == "web_search"
    assert events[2]["tool_arguments"] == {"query": "Question one"}
    assert events[2]["is_untrusted"] is True
    assert events[2]["latency_ms"] == 2.5
    assert all(event["run_id"] == "test-run-1" for event in events)
    assert all(event["timestamp"].endswith("Z") for event in events)


def test_orchestrator_reuses_existing_plan_without_calling_planner(tmp_path: Path) -> None:
    planner = FakePlanner()
    researcher = FakeResearcher()
    state = AgentState(
        topic="A topic",
        plan=[
            PlanTask(task_id="one", question="Question one."),
            PlanTask(task_id="two", question="Question two."),
            PlanTask(task_id="three", question="Question three."),
        ],
        run_metadata=RunMetadata(run_id="resumed-run"),
    )

    asyncio.run(Orchestrator(planner, researcher, trace_dir=tmp_path).run(state))

    assert planner.topics == []
    events = _read_events(tmp_path / "resumed-run.jsonl")
    assert events[1]["event"] == "plan_reused"


def test_orchestrator_marks_failed_runs_and_writes_failure_event(
    tmp_path: Path,
) -> None:
    planner = FakePlanner()
    researcher = FakeResearcher(error=RuntimeError("private failure detail"))
    state = AgentState(
        topic="A topic",
        run_metadata=RunMetadata(run_id="failed-run"),
    )

    with pytest.raises(RuntimeError, match="private failure detail"):
        asyncio.run(Orchestrator(planner, researcher, trace_dir=tmp_path).run(state))

    assert state.run_metadata.status == "failed"
    events = _read_events(tmp_path / "failed-run.jsonl")
    assert events[-1]["event"] == "run_failed"
    assert events[-1]["result_summary"] == "error_type=RuntimeError"
    assert "private failure detail" not in json.dumps(events)


def test_trace_writer_appends_and_bounds_arguments(tmp_path: Path) -> None:
    writer = JSONLTraceWriter("append-run", tmp_path)
    for index in range(2):
        writer.write(
            make_trace_event(
                "append-run",
                agent="researcher",
                event="tool_call",
                tool_name="web_search",
                tool_arguments={"query": "x" * 600, "max_results": 5},
                result_summary=f"results={index}",
            )
        )

    events = _read_events(tmp_path / "append-run.jsonl")
    assert len(events) == 2
    assert len(events[0]["tool_arguments"]["query"]) == 500
    assert events[1]["result_summary"] == "results=1"


@pytest.mark.parametrize("run_id", ["../outside", "with space", "", "a" * 65])
def test_trace_writer_rejects_unsafe_run_ids(run_id: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        JSONLTraceWriter(run_id, tmp_path)


def test_trace_writer_rejects_events_from_another_run(tmp_path: Path) -> None:
    writer = JSONLTraceWriter("first-run", tmp_path)
    wrong_run = TraceEvent(run_id="other-run", agent="planner", event="plan_created")

    with pytest.raises(ValueError, match="does not match"):
        writer.write(wrong_run)

    assert not (tmp_path / "first-run.jsonl").exists()
