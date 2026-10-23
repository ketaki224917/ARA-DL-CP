"""Validation and serialization tests for shared orchestration state."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from ara.agents.state import AgentState, Critique, EvidenceItem, PlanTask, RunMetadata


def make_evidence(
    chunk_id: str = "chunk:one",
    *,
    text: str = "Reciprocal rank fusion combines ranked result lists.",
) -> EvidenceItem:
    return EvidenceItem(
        chunk_id=chunk_id,
        text=text,
        source="retrieval.md",
        source_type="local",
        score=0.02,
    )


def test_agent_state_serializes_and_restores_all_agent_fields() -> None:
    evidence = make_evidence()
    state = AgentState(
        topic="How hybrid retrieval works",
        plan=[
            PlanTask(task_id="find-dense", question="How does dense retrieval rank evidence?"),
            PlanTask(
                task_id="find-lexical",
                question="How does BM25 rank evidence?",
                depends_on=["find-dense"],
            ),
            PlanTask(task_id="compare", question="How are the rankings fused?"),
        ],
        evidence_store={evidence.chunk_id: evidence},
        draft="Hybrid retrieval uses dense and lexical rankings.",
        critiques=[
            Critique(
                issue="miscited",
                claim="Dense and lexical rankings are combined.",
                details="The citation does not explain the fusion step.",
                evidence_ids=[evidence.chunk_id],
                severity="high",
            )
        ],
        revision_count=1,
        run_metadata=RunMetadata(
            run_id="run-001",
            seed=12,
            max_revisions=3,
            model_names={"planner": "qwen2.5:1.5b"},
        ),
    )

    restored = AgentState.model_validate_json(state.model_dump_json())

    assert restored == state
    assert restored.evidence_store[evidence.chunk_id].is_untrusted is True
    assert restored.run_metadata.started_at.tzinfo is not None
    assert restored.plan[1].depends_on == ["find-dense"]


def test_empty_agent_states_use_independent_mutable_defaults() -> None:
    first = AgentState(topic="First topic")
    second = AgentState(topic="Second topic")
    first.evidence_store["chunk:one"] = make_evidence()
    first.critiques.append(
        Critique(issue="gap", claim="claim", details="Missing evidence.")
    )

    assert first.plan == []
    assert second.evidence_store == {}
    assert second.critiques == []
    assert first.run_metadata.run_id != second.run_metadata.run_id


@pytest.mark.parametrize(
    "payload",
    [
        {"topic": "  "},
        {"topic": "topic", "plan": [{"task_id": "a", "question": "one"}]},
        {
            "topic": "topic",
            "plan": [
                {"task_id": "a", "question": "one"},
                {"task_id": "a", "question": "two"},
                {"task_id": "c", "question": "three"},
            ],
        },
        {
            "topic": "topic",
            "plan": [
                {"task_id": "a", "question": "one", "depends_on": ["missing"]},
                {"task_id": "b", "question": "two"},
                {"task_id": "c", "question": "three"},
            ],
        },
        {"topic": "topic", "draft": "  "},
        {"topic": "topic", "revision_count": -1},
        {
            "topic": "topic",
            "revision_count": 2,
            "run_metadata": {"max_revisions": 1},
        },
    ],
)
def test_agent_state_rejects_invalid_or_inconsistent_payloads(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        AgentState.model_validate(payload)


def test_plan_task_rejects_self_dependencies_and_blank_questions() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        PlanTask(task_id="task-1", question=" ")

    with pytest.raises(ValidationError):
        AgentState(
            topic="topic",
            plan=[
                PlanTask(task_id="one", question="Question one?", depends_on=["one"]),
                PlanTask(task_id="two", question="Question two?"),
                PlanTask(task_id="three", question="Question three?"),
            ],
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"chunk_id": "unknown:one", "text": "text", "source": "source"},
        {
            "chunk_id": "chunk:one",
            "text": "text",
            "source": "source",
            "is_untrusted": False,
        },
        {"chunk_id": "web:one", "text": "text", "source": "site", "source_type": "web"},
        {
            "chunk_id": "web:one",
            "text": "text",
            "source": "site",
            "source_type": "web",
            "url": "file:///etc/passwd",
        },
        {
            "chunk_id": "chunk:one",
            "text": "text",
            "source": "source",
            "retrieved_at": datetime(2025, 1, 1),
        },
        {"chunk_id": "chunk:one", "text": "text", "source": "source", "score": float("nan")},
    ],
)
def test_evidence_item_rejects_invalid_citation_provenance(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EvidenceItem.model_validate(payload)


def test_evidence_store_requires_map_keys_to_match_citation_ids() -> None:
    with pytest.raises(ValidationError, match="keys must match"):
        AgentState(topic="topic", evidence_store={"chunk:wrong": make_evidence()})


def test_add_evidence_deduplicates_by_id_and_rejects_conflicts() -> None:
    state = AgentState(topic="topic")
    original = make_evidence()
    duplicate = original.model_copy(update={"score": 0.5})

    assert state.add_evidence(original) is True
    assert state.add_evidence(duplicate) is False
    assert list(state.evidence_store) == [original.chunk_id]
    assert state.evidence_store[original.chunk_id].score == original.score
    with pytest.raises(ValueError, match="different evidence"):
        state.add_evidence(make_evidence(text="Conflicting passage for the same ID."))


def test_add_evidence_many_is_atomic_and_returns_new_ids() -> None:
    state = AgentState(topic="topic")
    existing = make_evidence()
    state.add_evidence(existing)
    added = make_evidence("chunk:two", text="A second grounded passage.")
    conflicting = make_evidence(text="Different evidence reuses the first ID.")

    with pytest.raises(ValueError, match="different evidence"):
        state.add_evidence_many([added, conflicting])
    assert "chunk:two" not in state.evidence_store

    assert state.add_evidence_many([existing, added, added]) == ["chunk:two"]
    assert set(state.evidence_store) == {"chunk:one", "chunk:two"}


def test_revision_count_respects_run_limit() -> None:
    state = AgentState(
        topic="topic",
        run_metadata=RunMetadata(max_revisions=1),
    )

    assert state.increment_revision() == 1
    with pytest.raises(ValueError, match="limit"):
        state.increment_revision()
