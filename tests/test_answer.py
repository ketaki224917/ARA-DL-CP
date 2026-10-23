"""Tests for evidence-grounded answer generation and citation validation."""

from collections.abc import Mapping, Sequence

import pytest

from ara.rag.answer import AnswerDraft, AnswerGenerationError, ClaimDraft, EvidenceAnswerer
from ara.rag.chunking import DocumentChunk
from ara.rag.retriever import HybridSearchResult


def result(
    chunk_id: str = "chunk:one",
    score: float = 0.03,
    text: str = "The sky is blue.",
) -> HybridSearchResult:
    chunk = DocumentChunk(
        chunk_id=chunk_id,
        text=text,
        source="notes.md",
        page=None,
        char_start=0,
        char_end=len(text),
    )
    return HybridSearchResult(chunk, score, 1, 1, 0.8, 3.2)


class FakeLLM:
    def __init__(self, draft: AnswerDraft | None = None, error: Exception | None = None) -> None:
        self.draft = draft
        self.error = error
        self.calls: list[tuple[Sequence[Mapping[str, str]], type[AnswerDraft], int]] = []

    def structured_output(
        self,
        messages: Sequence[Mapping[str, str]],
        schema: type[AnswerDraft],
        *,
        max_retries: int = 3,
    ) -> AnswerDraft:
        self.calls.append((messages, schema, max_retries))
        if self.error is not None:
            raise self.error
        assert self.draft is not None
        return self.draft


def answerable_draft() -> AnswerDraft:
    return AnswerDraft(
        abstain=False,
        claims=[ClaimDraft(text="The sky appears blue.", evidence_ids=["chunk:one"])],
    )


def test_answer_renders_one_citation_per_claim_and_returns_chunk_ids() -> None:
    llm = FakeLLM(answerable_draft())
    answerer = EvidenceAnswerer(llm, min_evidence_score=0.01)

    answer = answerer.answer("What color is the sky?", [result()])

    assert answer.text == "The sky appears blue. [chunk:one]"
    assert answer.cited_chunk_ids == ("chunk:one",)
    assert answer.abstained is False
    assert answer.claims[0].evidence_ids == ("chunk:one",)
    messages, schema, retries = llm.calls[0]
    assert schema is AnswerDraft
    assert retries == 3
    assert "untrusted data" in messages[0]["content"]
    assert "The sky is blue." in messages[1]["content"]


def test_empty_or_below_threshold_evidence_abstains_without_calling_llm() -> None:
    llm = FakeLLM(answerable_draft())
    answerer = EvidenceAnswerer(llm, min_evidence_score=0.02)

    empty = answerer.answer("question", [])
    weak = answerer.answer("question", [result(score=0.019)])

    assert empty.abstained and weak.abstained
    assert empty.cited_chunk_ids == weak.cited_chunk_ids == ()
    assert llm.calls == []


def test_model_abstention_is_returned_without_claims() -> None:
    llm = FakeLLM(AnswerDraft(abstain=True, abstention_reason="The source does not say."))
    answerer = EvidenceAnswerer(llm, min_evidence_score=0)

    answer = answerer.answer("question", [result(score=0.03)])

    assert answer.abstained is True
    assert answer.reason == "The source does not say."
    assert answer.claims == ()
    assert answer.cited_chunk_ids == ()


def test_unknown_citation_fails_closed_as_abstention() -> None:
    llm = FakeLLM(
        AnswerDraft(
            abstain=False,
            claims=[ClaimDraft(text="Unsupported statement.", evidence_ids=["chunk:unknown"])],
        )
    )
    answerer = EvidenceAnswerer(llm, min_evidence_score=0)

    answer = answerer.answer("question", [result()])

    assert answer.abstained is True
    assert "not in the retrieved evidence" in (answer.reason or "")
    assert answer.claims == ()


def test_llm_failure_is_wrapped_and_invalid_inputs_are_rejected() -> None:
    answerer = EvidenceAnswerer(FakeLLM(error=RuntimeError("offline")), min_evidence_score=0)

    with pytest.raises(AnswerGenerationError, match="validated answer"):
        answerer.answer("question", [result()])
    with pytest.raises(ValueError, match="query"):
        answerer.answer(" ", [])
    with pytest.raises(ValueError, match="finite"):
        answerer.answer("question", [result(score=float("nan"))])
    with pytest.raises(ValueError, match="max_evidence_chunks"):
        EvidenceAnswerer(FakeLLM(), max_evidence_chunks=0)
