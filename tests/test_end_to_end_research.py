"""Offline end-to-end gate through Planner, Researcher, stdio MCP, and traces."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from ara.agents.trace import TraceEvent

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEMO = _PROJECT_ROOT / "scripts" / "offline_e2e_demo.py"
_SAMPLE_TRACE = _PROJECT_ROOT / "traces" / "sample_research_run.jsonl"


def test_offline_plan_research_run_saves_a_valid_jsonl_trace(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(_DEMO),
            "--trace-dir",
            str(tmp_path),
            "--run-id",
            "test-e2e-run",
        ],
        cwd=_PROJECT_ROOT,
        capture_output=True,
        check=True,
        text=True,
        timeout=60,
    )
    summary: dict[str, Any] = json.loads(completed.stdout)

    assert summary["run_id"] == "test-e2e-run"
    assert summary["status"] == "completed"
    assert set(summary["task_statuses"].values()) == {"completed"}
    assert summary["evidence_ids"] == ["chunk:synthetic-offline-demo"]
    trace_path = Path(summary["trace_path"])
    assert trace_path == tmp_path / "test-e2e-run.jsonl"
    events = [TraceEvent.model_validate_json(line) for line in trace_path.read_text().splitlines()]
    assert [event.event for event in events][0] == "run_started"
    assert "plan_created" in [event.event for event in events]
    assert "tool_selected" in [event.event for event in events]
    tool_events = [event for event in events if event.event == "tool_call"]
    assert len(tool_events) == 1
    assert tool_events[0].server_name == "rag"
    assert tool_events[0].tool_name == "search_knowledge_base"
    assert tool_events[0].is_untrusted is True
    assert tool_events[0].result_summary is not None
    assert "chunk:synthetic-offline-demo" in tool_events[0].result_summary
    assert events[-1].event == "run_completed"


def test_committed_sample_trace_is_valid_and_identifies_fixture_evidence() -> None:
    trace_text = _SAMPLE_TRACE.read_text(encoding="utf-8")
    events = [TraceEvent.model_validate_json(line) for line in trace_text.splitlines()]

    assert events[0].run_id == "sample_research_run"
    assert any(event.event == "plan_created" for event in events)
    tool_events = [event for event in events if event.event == "tool_call"]
    assert len(tool_events) == 1
    assert tool_events[0].result_summary is not None
    assert "chunk:synthetic-offline-demo" in tool_events[0].result_summary
    assert "Synthetic fixture evidence" not in trace_text
    assert events[-1].event == "run_completed"
