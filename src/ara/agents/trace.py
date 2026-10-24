"""Typed append-only JSONL traces for orchestration runs."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_RUN_ID_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}\Z")
TraceScalar = str | int | float | bool | None
TraceAgent = Literal["orchestrator", "planner", "researcher"]


class TraceEvent(BaseModel):
    """One bounded, serializable decision or tool event."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    run_id: str = Field(min_length=1, max_length=64)
    agent: TraceAgent
    event: str = Field(min_length=1, max_length=64)
    task_id: str | None = Field(default=None, max_length=64)
    tool_name: str | None = Field(default=None, max_length=128)
    server_name: str | None = Field(default=None, max_length=64)
    tool_arguments: dict[str, TraceScalar] | None = None
    result_summary: str | None = Field(default=None, max_length=1_000)
    latency_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    tokens_in: int | None = Field(default=None, ge=0)
    tokens_out: int | None = Field(default=None, ge=0)
    is_untrusted: bool | None = None

    @field_validator("timestamp")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("trace timestamps must include a timezone")
        return value

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        normalized = value.strip()
        if not _RUN_ID_PATTERN.fullmatch(normalized):
            raise ValueError("run_id must contain only letters, digits, '_' or '-'.")
        return normalized

    @field_validator("tool_arguments")
    @classmethod
    def bound_tool_arguments(
        cls,
        value: dict[str, TraceScalar] | None,
    ) -> dict[str, TraceScalar] | None:
        if value is None:
            return None
        if len(value) > 20:
            raise ValueError("trace tool arguments may contain at most 20 fields")
        bounded: dict[str, TraceScalar] = {}
        for key, item in value.items():
            if len(key) > 128:
                raise ValueError("trace argument names must be at most 128 characters")
            if isinstance(item, str):
                bounded[key] = item[:500]
            elif item is None or isinstance(item, (bool, int)):
                bounded[key] = item
            elif isinstance(item, float) and math.isfinite(item):
                bounded[key] = item
            else:
                raise ValueError("trace arguments must contain only scalar values")
        return bounded


class JSONLTraceWriter:
    """Append validated events to `trace_dir/<run_id>.jsonl`."""

    def __init__(self, run_id: str, trace_dir: Path | str = Path("traces")) -> None:
        validated_id = TraceEvent(run_id=run_id, agent="orchestrator", event="writer_init").run_id
        self.run_id = validated_id
        self.trace_dir = Path(trace_dir)
        self.path = self.trace_dir / f"{validated_id}.jsonl"

    def write(self, event: TraceEvent) -> None:
        """Append one event after verifying it belongs to this run."""
        if event.run_id != self.run_id:
            raise ValueError("trace event run_id does not match this writer")
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as trace_file:
            trace_file.write(event.model_dump_json())
            trace_file.write("\n")


def make_trace_event(
    run_id: str,
    *,
    agent: TraceAgent,
    event: str,
    task_id: str | None = None,
    tool_name: str | None = None,
    server_name: str | None = None,
    tool_arguments: Mapping[str, TraceScalar] | None = None,
    result_summary: str | None = None,
    latency_ms: float | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    is_untrusted: bool | None = None,
) -> TraceEvent:
    """Build an event with the current UTC timestamp."""
    return TraceEvent(
        run_id=run_id,
        agent=agent,
        event=event,
        task_id=task_id,
        tool_name=tool_name,
        server_name=server_name,
        tool_arguments=dict(tool_arguments) if tool_arguments is not None else None,
        result_summary=result_summary,
        latency_ms=latency_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        is_untrusted=is_untrusted,
    )


__all__ = [
    "JSONLTraceWriter",
    "TraceAgent",
    "TraceEvent",
    "TraceScalar",
    "make_trace_event",
]
