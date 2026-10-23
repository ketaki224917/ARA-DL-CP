"""Typed, serializable state shared by ARA's research and report agents."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

_CHUNK_ID_PATTERN = re.compile(r"(?:chunk|web):[^\s]{1,120}\Z")
_TASK_ID_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}\Z")
_MAX_PLAN_TASKS = 8
_MIN_PLAN_TASKS = 3
_MAX_TEXT_LENGTH = 20_000
_MAX_TOPIC_LENGTH = 1_000
_MAX_SOURCE_LENGTH = 2_048


class PlanTask(BaseModel):
    """One bounded research subtask emitted by the planner."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    task_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=_MAX_TOPIC_LENGTH)
    rationale: str = Field(default="", max_length=_MAX_TOPIC_LENGTH)
    depends_on: list[str] = Field(default_factory=list)
    status: Literal["pending", "in_progress", "completed", "blocked"] = "pending"

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, value: str) -> str:
        normalized = value.strip()
        if not _TASK_ID_PATTERN.fullmatch(normalized):
            raise ValueError("task_id must contain only letters, digits, '_' or '-'.")
        return normalized

    @field_validator("question", "rationale")
    @classmethod
    def normalize_task_text(cls, value: str, info: ValidationInfo) -> str:
        normalized = value.strip()
        if not normalized and getattr(info, "field_name", "") == "question":
            raise ValueError("task question must not be blank")
        return normalized

    @field_validator("depends_on")
    @classmethod
    def validate_dependencies(cls, value: list[str]) -> list[str]:
        dependencies = [item.strip() for item in value]
        if any(not _TASK_ID_PATTERN.fullmatch(item) for item in dependencies):
            raise ValueError("task dependencies must be valid task IDs")
        if len(set(dependencies)) != len(dependencies):
            raise ValueError("task dependencies must be unique")
        return dependencies


class EvidenceItem(BaseModel):
    """Citation-ready passage returned by a local or web retrieval tool."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    chunk_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=_MAX_TEXT_LENGTH)
    source: str = Field(min_length=1, max_length=_MAX_SOURCE_LENGTH)
    source_type: Literal["local", "web"] = "local"
    page: int | None = Field(default=None, ge=1)
    url: str | None = Field(default=None, max_length=_MAX_SOURCE_LENGTH)
    score: float | None = Field(default=None, allow_inf_nan=False)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_untrusted: Literal[True] = True

    @field_validator("chunk_id")
    @classmethod
    def validate_chunk_id(cls, value: str) -> str:
        normalized = value.strip()
        if not _CHUNK_ID_PATTERN.fullmatch(normalized):
            raise ValueError("chunk_id must use the chunk: or web: citation format")
        return normalized

    @field_validator("text", "source")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("evidence text and source must not be blank")
        return normalized

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        parts = urlsplit(normalized)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            raise ValueError("evidence URL must use HTTP or HTTPS")
        if parts.username is not None or parts.password is not None:
            raise ValueError("evidence URL must not include credentials")
        return normalized

    @field_validator("retrieved_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieved_at must include a timezone")
        return value

    @model_validator(mode="after")
    def citation_matches_source_type(self) -> EvidenceItem:
        expected_prefix = "web:" if self.source_type == "web" else "chunk:"
        if not self.chunk_id.startswith(expected_prefix):
            raise ValueError(f"{self.source_type} evidence must use {expected_prefix} IDs")
        if self.source_type == "web" and self.url is None:
            raise ValueError("web evidence must include its source URL")
        return self


class Critique(BaseModel):
    """Structured issue from a critic pass, tied to claims and evidence IDs."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    issue: Literal["unsupported", "miscited", "gap", "contradiction", "clarity"]
    claim: str = Field(min_length=1, max_length=_MAX_TEXT_LENGTH)
    details: str = Field(min_length=1, max_length=_MAX_TEXT_LENGTH)
    evidence_ids: list[str] = Field(default_factory=list, max_length=50)
    severity: Literal["low", "medium", "high"] = "medium"
    suggested_revision: str | None = Field(default=None, max_length=_MAX_TEXT_LENGTH)

    @field_validator("claim", "details", "suggested_revision")
    @classmethod
    def normalize_critique_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("critique text must not be blank")
        return normalized

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, value: list[str]) -> list[str]:
        identifiers = [item.strip() for item in value]
        if any(not _CHUNK_ID_PATTERN.fullmatch(item) for item in identifiers):
            raise ValueError("critique evidence IDs must use chunk: or web: citation format")
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("critique evidence IDs must be unique")
        return identifiers


class RunMetadata(BaseModel):
    """Identity and lifecycle settings for one orchestration run."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex, min_length=1, max_length=64)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    seed: int | None = None
    max_revisions: int = Field(default=3, ge=0, le=20)
    model_names: dict[str, str] = Field(default_factory=dict)

    @field_validator("run_id")
    @classmethod
    def normalize_run_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("run_id must not be blank")
        return normalized

    @field_validator("started_at", "updated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("run timestamps must include a timezone")
        return value


class AgentState(BaseModel):
    """Validated shared state for planning, research, drafting, and critique."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    topic: str = Field(min_length=1, max_length=_MAX_TOPIC_LENGTH)
    plan: list[PlanTask] = Field(default_factory=list, max_length=_MAX_PLAN_TASKS)
    evidence_store: dict[str, EvidenceItem] = Field(default_factory=dict)
    draft: str | None = Field(default=None, max_length=_MAX_TEXT_LENGTH)
    critiques: list[Critique] = Field(default_factory=list, max_length=100)
    revision_count: int = Field(default=0, ge=0)
    run_metadata: RunMetadata = Field(default_factory=RunMetadata)

    @field_validator("topic")
    @classmethod
    def normalize_topic(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("topic must not be blank")
        return normalized

    @field_validator("draft")
    @classmethod
    def normalize_draft(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("draft must be absent or non-blank")
        return normalized

    @model_validator(mode="after")
    def validate_state_consistency(self) -> AgentState:
        if self.plan and not _MIN_PLAN_TASKS <= len(self.plan) <= _MAX_PLAN_TASKS:
            raise ValueError(
                f"a populated plan must contain {_MIN_PLAN_TASKS}-{_MAX_PLAN_TASKS} tasks"
            )
        task_ids = [task.task_id for task in self.plan]
        if len(set(task_ids)) != len(task_ids):
            raise ValueError("plan task IDs must be unique")
        known_tasks = set(task_ids)
        if any(
            dependency not in known_tasks
            for task in self.plan
            for dependency in task.depends_on
        ):
            raise ValueError("plan dependencies must reference task IDs in the same plan")
        if any(task.task_id in task.depends_on for task in self.plan):
            raise ValueError("a plan task cannot depend on itself")
        for chunk_id, item in self.evidence_store.items():
            if chunk_id != item.chunk_id:
                raise ValueError("evidence_store keys must match each item's chunk_id")
        if self.revision_count > self.run_metadata.max_revisions:
            raise ValueError("revision_count cannot exceed run_metadata.max_revisions")
        return self

    def add_evidence(self, item: EvidenceItem) -> bool:
        """Store evidence once by stable chunk ID; reject conflicting ID reuse.

        Returns `True` when the item is new, and `False` for a duplicate with
        matching source identity and text.
        """
        existing = self.evidence_store.get(item.chunk_id)
        if existing is None:
            self.evidence_store[item.chunk_id] = item
            return True
        if _same_evidence_identity(existing, item):
            return False
        raise ValueError(f"chunk ID {item.chunk_id!r} already refers to different evidence")

    def add_evidence_many(self, items: list[EvidenceItem]) -> list[str]:
        """Add a batch atomically and return IDs that were newly stored."""
        pending: dict[str, EvidenceItem] = {}
        for item in items:
            existing = pending.get(item.chunk_id) or self.evidence_store.get(item.chunk_id)
            if existing is None:
                pending[item.chunk_id] = item
            elif not _same_evidence_identity(existing, item):
                raise ValueError(f"chunk ID {item.chunk_id!r} already refers to different evidence")
        self.evidence_store.update(pending)
        return list(pending)

    def increment_revision(self) -> int:
        """Advance the revision count unless the configured cap was reached."""
        if self.revision_count >= self.run_metadata.max_revisions:
            raise ValueError("revision limit has been reached")
        self.revision_count += 1
        self.run_metadata.updated_at = datetime.now(UTC)
        return self.revision_count


def _same_evidence_identity(first: EvidenceItem, second: EvidenceItem) -> bool:
    return (
        first.chunk_id == second.chunk_id
        and first.text == second.text
        and first.source == second.source
        and first.source_type == second.source_type
        and first.page == second.page
        and first.url == second.url
    )
