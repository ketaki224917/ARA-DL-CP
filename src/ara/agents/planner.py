"""Validated research planning using the local structured-output LLM client."""

from __future__ import annotations

import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ara.agents.prompts.planner import planner_messages
from ara.agents.state import PlanTask
from ara.llm.client import OllamaClient

_TASK_ID_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}\Z")
_MAX_TOPIC_LENGTH = 1_000


class PlannedTask(BaseModel):
    """LLM-facing task schema; execution status remains owned by AgentState."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=_MAX_TOPIC_LENGTH)
    rationale: str = Field(max_length=_MAX_TOPIC_LENGTH)
    depends_on: list[str] = Field(max_length=8)

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, value: str) -> str:
        normalized = value.strip()
        if not _TASK_ID_PATTERN.fullmatch(normalized):
            raise ValueError("task_id must contain only letters, digits, '_' or '-'.")
        return normalized

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("task question must not be blank")
        return normalized

    @field_validator("rationale")
    @classmethod
    def normalize_rationale(cls, value: str) -> str:
        return value.strip()

    @field_validator("depends_on")
    @classmethod
    def validate_dependencies(cls, value: list[str]) -> list[str]:
        dependencies = [item.strip() for item in value]
        if any(not _TASK_ID_PATTERN.fullmatch(item) for item in dependencies):
            raise ValueError("task dependencies must be valid task IDs")
        if len(set(dependencies)) != len(dependencies):
            raise ValueError("task dependencies must be unique")
        return dependencies


class ResearchPlan(BaseModel):
    """A complete 3-8 task plan with internally consistent dependencies."""

    model_config = ConfigDict(extra="forbid")

    tasks: list[PlannedTask] = Field(min_length=3, max_length=8)

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        task_ids = [task.task_id for task in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("plan task IDs must be unique")
        known_tasks = set(task_ids)
        for task in self.tasks:
            if task.task_id in task.depends_on:
                raise ValueError("a plan task cannot depend on itself")
            if any(dependency not in known_tasks for dependency in task.depends_on):
                raise ValueError("plan dependencies must reference task IDs in the same plan")

        dependencies = {task.task_id: task.depends_on for task in self.tasks}
        visited: set[str] = set()
        active: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in active:
                raise ValueError("plan dependencies must not contain cycles")
            if task_id in visited:
                return
            active.add(task_id)
            for dependency in dependencies[task_id]:
                visit(dependency)
            active.remove(task_id)
            visited.add(task_id)

        for task_id in task_ids:
            visit(task_id)
        return self


class Planner:
    """Generate validated research subtasks without executing any tools."""

    def __init__(
        self,
        llm_client: OllamaClient | None = None,
        *,
        max_retries: int = 3,
    ) -> None:
        if not 0 <= max_retries <= 3:
            raise ValueError("max_retries must be between 0 and 3")
        self._llm = llm_client if llm_client is not None else OllamaClient()
        self.max_retries = max_retries

    def plan(self, topic: str) -> list[PlanTask]:
        """Return 3-8 pending tasks after structured-output validation and retries."""
        normalized_topic = topic.strip()
        if not normalized_topic:
            raise ValueError("topic must not be blank")
        if len(normalized_topic) > _MAX_TOPIC_LENGTH:
            raise ValueError(f"topic must be at most {_MAX_TOPIC_LENGTH} characters")

        result = self._llm.structured_output(
            planner_messages(normalized_topic),
            ResearchPlan,
            max_retries=self.max_retries,
        )
        return [
            PlanTask(
                task_id=task.task_id,
                question=task.question,
                rationale=task.rationale,
                depends_on=task.depends_on,
                status="pending",
            )
            for task in result.tasks
        ]


__all__ = ["PlannedTask", "ResearchPlan", "Planner"]
