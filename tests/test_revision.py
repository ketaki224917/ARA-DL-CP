"""Tests for capped report revision and stopping behavior."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal

import pytest

from ara.agents.critic import ClaimAssessment, Critic, CriticResponse, CriticResult
from ara.agents.prompts.writer import REPORT_SECTION_HEADINGS
from ara.agents.revision import RevisionLoop, RevisionLoopError
from ara.agents.state import AgentState, Critique, EvidenceItem
from ara.agents.trace import TraceEvent
from ara.agents.writer import (
    ReportDraft,
    Writer,
    WriterClaim,
    WriterResult,
    WriterSection,
    WriterSummaryClaim,
)
from ara.llm.client import ChatMessage


def issue() -> Critique:
    return Critique(
        issue="unsupported",
        claim="The report makes an unsupported claim.",
        details="The cited evidence does not support the statement.",
        evidence_ids=["chunk:one"],
        severity="high",
    )


def reviewed_issue() -> CriticResult:
    return CriticResult(
        critiques=[issue()],
        reviewed_claim_count=1,
        supported_claim_count=0,
        unsupported_claim_count=1,
        gap_count=0,
        contradiction_count=0,
    )


def clean_review() -> CriticResult:
    return CriticResult(
        critiques=[],
        reviewed_claim_count=1,
        supported_claim_count=1,
        unsupported_claim_count=0,
        gap_count=0,
        contradiction_count=0,
    )


def make_state(*, max_revisions: int = 3) -> AgentState:
    return AgentState(
        topic="Test topic",
        run_metadata={"max_revisions": max_revisions},
    )


class FakeWriter:
    def __init__(self, results: Sequence[WriterResult | Exception]) -> None:
        self.results = list(results)
        self.calls = 0
        self.feedback: list[list[Critique]] = []

    def write(self, state: AgentState) -> WriterResult:
        self.calls += 1
        self.feedback.append(list(state.critiques))
        if not self.results:
            raise AssertionError("unexpected additional writer call")
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        state.draft = result.markdown
        return result


class FakeCritic:
    def __init__(self, results: Sequence[CriticResult | Exception]) -> None:
        self.results = list(results)
        self.calls = 0

    def review(self, state: AgentState) -> CriticResult:
        self.calls += 1
        if not self.results:
            raise AssertionError("unexpected additional critic call")
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        state.critiques = result.critiques
        return result


def writer_result(markdown: str, *, abstained: bool = False) -> WriterResult:
    return WriterResult(markdown=markdown, abstained=abstained)


def test_loop_revises_with_prior_feedback_and_stops_when_clean() -> None:
    writer = FakeWriter([writer_result("Draft v1"), writer_result("Draft v2")])
    critic = FakeCritic([reviewed_issue(), clean_review()])
    state = make_state()

    result = RevisionLoop(writer, critic).run(state)

    assert result.final_draft == "Draft v2"
    assert result.stop_reason == "clean"
    assert result.revision_count == 1
    assert [item.unsupported_claim_count for item in result.iterations] == [1, 0]
    assert [item.revision_count for item in result.iterations] == [0, 1]
    assert writer.calls == 2
    assert critic.calls == 2
    assert writer.feedback == [[], [issue()]]
    assert state.revision_count == 1
    assert state.critiques == []


def test_loop_stops_without_revising_a_clean_initial_draft() -> None:
    writer = FakeWriter([writer_result("Clean draft")])
    critic = FakeCritic([clean_review()])

    result = RevisionLoop(writer, critic).run(make_state())

    assert result.stop_reason == "clean"
    assert result.revision_count == 0
    assert len(result.iterations) == 1
    assert writer.calls == 1
    assert critic.calls == 1


def test_loop_emits_bounded_iteration_counts_and_stopping_trace_events() -> None:
    writer = FakeWriter([writer_result("Draft v1"), writer_result("Draft v2")])
    critic = FakeCritic([reviewed_issue(), clean_review()])
    events: list[TraceEvent] = []

    RevisionLoop(writer, critic, trace_callback=events.append).run(make_state())

    assert [event.event for event in events] == [
        "iteration_reviewed",
        "iteration_reviewed",
        "loop_stopped",
    ]
    assert events[0].agent == "revision_loop"
    assert "unsupported=1" in (events[0].result_summary or "")
    assert "reason=clean" in (events[-1].result_summary or "")
    assert "Draft v1" not in " ".join(event.model_dump_json() for event in events)


def test_loop_stops_at_configured_revision_cap() -> None:
    writer = FakeWriter(
        [writer_result("Draft v1"), writer_result("Draft v2"), writer_result("Draft v3")]
    )
    critic = FakeCritic([reviewed_issue(), reviewed_issue(), reviewed_issue()])

    result = RevisionLoop(writer, critic).run(make_state(max_revisions=2))

    assert result.stop_reason == "revision_cap"
    assert result.revision_count == 2
    assert len(result.iterations) == 3
    assert writer.calls == 3
    assert critic.calls == 3
    assert result.iterations[-1].unsupported_claim_count == 1


def test_loop_stops_when_writer_repeats_the_same_draft() -> None:
    writer = FakeWriter([writer_result("Same draft"), writer_result("Same draft")])
    critic = FakeCritic([reviewed_issue()])
    state = make_state()

    result = RevisionLoop(writer, critic).run(state)

    assert result.stop_reason == "unchanged_draft"
    assert result.revision_count == 1
    assert result.final_draft == "Same draft"
    assert len(result.iterations) == 1
    assert writer.calls == 2
    assert critic.calls == 1
    assert state.critiques == [issue()]


def test_loop_stops_on_abstention_without_attempting_a_revision() -> None:
    abstention = "# Research report\n\n## Executive summary\n\nNo evidence available."
    writer = FakeWriter([writer_result(abstention, abstained=True)])
    critic = FakeCritic([clean_review()])

    result = RevisionLoop(writer, critic).run(make_state())

    assert result.abstained is True
    assert result.stop_reason == "abstained"
    assert result.revision_count == 0
    assert writer.calls == 1
    assert critic.calls == 1


def test_revision_abstention_drops_only_critic_flagged_claims() -> None:
    evidence = EvidenceItem(
        chunk_id="chunk:one",
        text="The source supports the remaining report claim.",
        source="sample.txt",
    )
    state = make_state()
    state.evidence_store[evidence.chunk_id] = evidence
    initial = (
        "# Grounded report\n\n"
        "## Executive summary\n\n"
        "The report makes an unsupported claim. [chunk:one]\n"
        "The remaining report claim is supported. [chunk:one]"
    )
    abstention = "# Research report\n\n## Executive summary\n\nInsufficient evidence."
    critique = Critique(
        issue="unsupported",
        claim="The report makes an unsupported claim.",
        details="The source does not support this statement.",
        evidence_ids=["chunk:one"],
        severity="high",
    )
    critic = FakeCritic(
        [
            CriticResult(
                critiques=[critique],
                reviewed_claim_count=2,
                supported_claim_count=1,
                unsupported_claim_count=1,
                gap_count=0,
                contradiction_count=0,
            ),
            clean_review(),
        ]
    )
    events: list[TraceEvent] = []

    result = RevisionLoop(
        FakeWriter([writer_result(initial), writer_result(abstention, abstained=True)]),
        critic,
        trace_callback=events.append,
    ).run(state)

    assert result.abstained is False
    assert result.stop_reason == "clean"
    assert "The report makes an unsupported claim" not in result.final_draft
    assert "The remaining report claim is supported. [chunk:one]" in result.final_draft
    assert [item.unsupported_claim_count for item in result.iterations] == [1, 0]
    assert any(event.event == "revision_recovered" for event in events)


def test_writer_error_during_revision_raises_and_preserves_last_draft_and_critiques() -> None:
    writer = FakeWriter([writer_result("Draft v1"), RuntimeError("writer offline")])
    critic = FakeCritic([reviewed_issue()])
    state = make_state()

    with pytest.raises(RevisionLoopError, match="Could not generate report revision 1"):
        RevisionLoop(writer, critic).run(state)

    assert state.draft == "Draft v1"
    assert state.revision_count == 1
    assert state.critiques == [issue()]
    assert critic.calls == 1


def test_critic_error_is_wrapped_and_prevents_any_revision() -> None:
    writer = FakeWriter([writer_result("Draft v1")])
    critic = FakeCritic([RuntimeError("critic offline")])
    state = make_state()

    with pytest.raises(RevisionLoopError, match="Could not review report revision 0"):
        RevisionLoop(writer, critic).run(state)

    assert state.draft == "Draft v1"
    assert state.revision_count == 0
    assert writer.calls == 1


def test_loop_requires_a_fresh_agent_state() -> None:
    state = make_state()
    state.draft = "Already drafted"
    writer = FakeWriter([])
    critic = FakeCritic([])

    with pytest.raises(RevisionLoopError, match="must start without a draft"):
        RevisionLoop(writer, critic).run(state)

    assert writer.calls == critic.calls == 0


class QueueWriterLLM:
    def __init__(self, *drafts: ReportDraft) -> None:
        self.drafts = list(drafts)
        self.messages: list[Sequence[ChatMessage]] = []

    def structured_output(
        self,
        messages: Sequence[ChatMessage],
        schema: type[ReportDraft],
        *,
        max_retries: int = 3,
        json_schema: Mapping[str, Any] | None = None,
        num_predict: int | None = None,
    ) -> ReportDraft:
        assert schema is ReportDraft
        self.messages.append(messages)
        return self.drafts.pop(0)


class QueueCriticLLM:
    def __init__(self, *responses: CriticResponse) -> None:
        self.responses = list(responses)

    def structured_output(
        self,
        messages: Sequence[ChatMessage],
        schema: type[CriticResponse],
        *,
        max_retries: int = 3,
    ) -> CriticResponse:
        assert schema is CriticResponse
        assert messages[0]["role"] == "system"
        return self.responses.pop(0)


def report_draft(claim_text: str) -> ReportDraft:
    def claim(text: str) -> WriterClaim:
        return WriterClaim(text=text, evidence_ids=["chunk:one"])

    def summary_claim(text: str) -> WriterSummaryClaim:
        return WriterSummaryClaim(text=text, evidence_ids=["chunk:one"])

    return ReportDraft(
        abstain=False,
        title="A grounded report",
        summary=[summary_claim(claim_text)],
        sections=[
            WriterSection(heading=heading, claims=[claim(f"{claim_text} ({heading}).")])
            for heading in REPORT_SECTION_HEADINGS
        ],
    )


def critic_response(verdict: Literal["supported", "unsupported", "uncertain"]) -> CriticResponse:
    return CriticResponse(
        assessments=[
            ClaimAssessment(
                claim_id=f"claim-{index:03d}",
                verdict=verdict,
                details=f"Review result {index}.",
                evidence_ids=["chunk:one"],
                suggested_revision="Use the source's exact supported statement."
                if verdict != "supported"
                else None,
            )
            for index in range(1, 6)
        ]
    )


def test_real_writer_and_critic_share_feedback_through_the_revision_loop() -> None:
    evidence = EvidenceItem(
        chunk_id="chunk:one",
        text="The source states that the sample contains 40 observations.",
        source="sample.txt",
    )
    state = AgentState(topic="Sample size reporting", evidence_store={"chunk:one": evidence})
    writer_llm = QueueWriterLLM(
        report_draft("The sample contains 400 observations."),
        report_draft("The sample contains 40 observations."),
    )
    critic_llm = QueueCriticLLM(critic_response("unsupported"), critic_response("supported"))

    result = RevisionLoop(Writer(writer_llm), Critic(critic_llm)).run(state)

    second_request = json.loads(writer_llm.messages[1][1]["content"].partition("\n")[2])
    assert result.stop_reason == "clean"
    assert result.final_draft.count("40 observations") == 5
    assert result.revision_count == 1
    assert [item.unsupported_claim_count for item in result.iterations] == [5, 0]
    assert "400 observations" in second_request["current_draft"]
    assert len(second_request["critic_feedback"]) == 5
    assert second_request["critic_feedback"][0]["issue"] == "unsupported"
