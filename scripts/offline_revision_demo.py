"""Run a scripted three-topic demonstration of the report revision loop."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from ara.agents.critic import ClaimAssessment, Critic, CriticResponse
from ara.agents.prompts.writer import REPORT_SECTION_HEADINGS
from ara.agents.revision import RevisionLoop, RevisionLoopResult
from ara.agents.state import AgentState, EvidenceItem
from ara.agents.trace import TraceEvent
from ara.agents.writer import ReportDraft, Writer, WriterClaim, WriterSection
from ara.llm.client import ChatMessage

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
SectionHeading = Literal[
    "Key findings",
    "Evidence synthesis",
    "Limitations",
    "Conclusion",
]
_TYPED_SECTION_HEADINGS = cast(
    tuple[SectionHeading, SectionHeading, SectionHeading, SectionHeading],
    REPORT_SECTION_HEADINGS,
)


class RevisionDemoRow(BaseModel):
    """Measured counts for one scripted topic run."""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1)
    initial_unsupported: int = Field(ge=0)
    final_unsupported: int = Field(ge=0)
    revisions: int = Field(ge=0)
    stop_reason: Literal["clean", "abstained", "revision_cap", "unchanged_draft"]

    @property
    def reduction_percent(self) -> int | None:
        if self.initial_unsupported == 0:
            return None
        reduction = (
            self.initial_unsupported - self.final_unsupported
        ) / self.initial_unsupported
        return round(reduction * 100)


class _Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    topic: str
    source_path: str
    evidence_id: str
    initial_summary: str
    revised_summary: str
    section_claims: list[str] = Field(min_length=4, max_length=4)


_SCENARIOS = (
    _Scenario(
        key="hybrid",
        topic="What can hybrid retrieval do, and what should be evaluated?",
        source_path="data/sample_corpus/03_hybrid_retrieval.md",
        evidence_id="chunk:demo_hybrid_retrieval",
        initial_summary="Hybrid retrieval always beats dense and lexical baselines.",
        revised_summary=(
            "Hybrid retrieval combines dense and lexical search, but its performance "
            "must be evaluated on labeled questions."
        ),
        section_claims=[
            "Hybrid retrieval can combine dense semantic and sparse lexical search.",
            "Fusion cannot recover passages missed by all component searches.",
            "A hybrid label alone does not demonstrate better retrieval.",
            "The full pipeline should be evaluated on labeled questions.",
        ],
    ),
    _Scenario(
        key="citations",
        topic="How should report citations preserve and verify provenance?",
        source_path="data/sample_corpus/11_chunk_citation_metadata.md",
        evidence_id="chunk:demo_citation_provenance",
        initial_summary="A citation ID is enough even if it cannot resolve to source text.",
        revised_summary=(
            "A citation ID should resolve to stored source text and metadata before "
            "a claim is reviewed."
        ),
        section_claims=[
            "Stable passage IDs connect claims to their source text.",
            "Useful citation metadata can include source, page, and character offsets.",
            "IDs should be deterministic for the same source and chunking settings.",
            "Resolve each cited ID to stored text before checking claim support.",
        ],
    ),
    _Scenario(
        key="untrusted-text",
        topic="How should a research agent handle instructions inside retrieved text?",
        source_path="data/sample_corpus/19_untrusted_retrieved_text.md",
        evidence_id="chunk:demo_untrusted_text",
        initial_summary="Marking retrieved text untrusted makes prompt injection impossible.",
        revised_summary=(
            "Treat retrieved text as data; isolation reduces confusion but cannot "
            "eliminate prompt injection."
        ),
        section_claims=[
            "Retrieved documents can contain text that looks like model instructions.",
            "Keep system instructions separate from retrieved source material.",
            "Validate tool arguments independently of retrieved content.",
            "Untrusted-data boundaries reduce confusion but do not eliminate injection risk.",
        ],
    ),
)


class _ScriptedWriterLLM:
    def __init__(self, drafts: Sequence[ReportDraft]) -> None:
        self._drafts = list(drafts)
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
        if schema is not ReportDraft or max_retries != 3 or not self._drafts:
            raise ValueError("unexpected scripted writer request")
        self.messages.append(messages)
        return self._drafts.pop(0)


class _ScriptedCriticLLM:
    def __init__(self, responses: Sequence[CriticResponse]) -> None:
        self._responses = list(responses)

    def structured_output(
        self,
        messages: Sequence[ChatMessage],
        schema: type[CriticResponse],
        *,
        max_retries: int = 3,
    ) -> CriticResponse:
        if schema is not CriticResponse or max_retries != 3 or not self._responses:
            raise ValueError("unexpected scripted critic request")
        return self._responses.pop(0)


def run_experiment() -> list[RevisionDemoRow]:
    """Run actual writer/critic/loop code with local corpus notes and scripted judgments."""
    rows: list[RevisionDemoRow] = []
    for scenario in _SCENARIOS:
        source_path = _PROJECT_ROOT / scenario.source_path
        evidence = EvidenceItem(
            chunk_id=scenario.evidence_id,
            text=source_path.read_text(encoding="utf-8"),
            source=scenario.source_path,
        )
        state = AgentState(
            topic=scenario.topic,
            evidence_store={scenario.evidence_id: evidence},
        )
        writer_llm = _ScriptedWriterLLM(
            [
                _report_draft(scenario, scenario.initial_summary),
                _report_draft(scenario, scenario.revised_summary),
            ]
        )
        critic_llm = _ScriptedCriticLLM(
            [
                _critic_response(scenario, initially_unsupported=True),
                _critic_response(scenario, initially_unsupported=False),
            ]
        )
        trace_events: list[TraceEvent] = []
        result = RevisionLoop(
            Writer(writer_llm),
            Critic(critic_llm),
            trace_callback=trace_events.append,
        ).run(state)
        _validate_run(scenario, result, writer_llm.messages, trace_events)
        rows.append(
            RevisionDemoRow(
                topic=scenario.topic,
                initial_unsupported=result.iterations[0].unsupported_claim_count,
                final_unsupported=result.iterations[-1].unsupported_claim_count,
                revisions=result.revision_count,
                stop_reason=result.stop_reason,
            )
        )
    return rows


def _report_draft(scenario: _Scenario, summary: str) -> ReportDraft:
    def cited_claim(text: str) -> WriterClaim:
        return WriterClaim(text=text, evidence_ids=[scenario.evidence_id])

    return ReportDraft(
        abstain=False,
        title=scenario.topic,
        summary=[cited_claim(summary)],
        sections=[
            WriterSection(heading=cast(SectionHeading, heading), claims=[cited_claim(text)])
            for heading, text in zip(_TYPED_SECTION_HEADINGS, scenario.section_claims, strict=True)
        ],
    )


def _critic_response(
    scenario: _Scenario,
    *,
    initially_unsupported: bool,
) -> CriticResponse:
    statuses: list[Literal["supported", "unsupported"]] = [
        "unsupported" if initially_unsupported else "supported",
        "supported",
        "supported",
        "supported",
        "supported",
    ]
    assessments = [
        ClaimAssessment(
            claim_id=f"claim-{index:03d}",
            verdict=status,
            details=(
                "The evidence contradicts the draft's guarantee."
                if status == "unsupported"
                else "The cited sample-corpus passage supports this statement."
            ),
            evidence_ids=[scenario.evidence_id],
            suggested_revision=(scenario.revised_summary if status == "unsupported" else None),
        )
        for index, status in enumerate(statuses, start=1)
    ]
    return CriticResponse(assessments=assessments)


def _validate_run(
    scenario: _Scenario,
    result: RevisionLoopResult,
    writer_messages: Sequence[Sequence[ChatMessage]],
    trace_events: Sequence[TraceEvent],
) -> None:
    if (
        result.stop_reason != "clean"
        or result.abstained
        or result.revision_count != 1
        or len(result.iterations) != 2
        or result.iterations[0].unsupported_claim_count != 1
        or result.iterations[-1].unsupported_claim_count != 0
        or len(writer_messages) != 2
        or len(trace_events) != 3
    ):
        raise RuntimeError(f"scripted revision expectations failed for {scenario.key}")
    request = json.loads(writer_messages[1][1]["content"].partition("\n")[2])
    if scenario.initial_summary not in request["current_draft"]:
        raise RuntimeError(f"revision prompt omitted the prior draft for {scenario.key}")
    if (
        not request["critic_feedback"]
        or request["critic_feedback_truncated"] is not False
    ):
        raise RuntimeError(f"revision prompt omitted critic feedback for {scenario.key}")


def _format_table(rows: Sequence[RevisionDemoRow]) -> str:
    lines = [
        "| Topic | Unsupported before | Unsupported after | Reduction | Revisions | Stop reason |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        reduction = (
            f"{row.reduction_percent}%" if row.reduction_percent is not None else "n/a"
        )
        lines.append(
            f"| {row.topic} | {row.initial_unsupported} | {row.final_unsupported} | "
            f"{reduction} | {row.revisions} | {row.stop_reason} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the run results as JSON instead of a Markdown table",
    )
    args = parser.parse_args()
    rows = run_experiment()
    if args.json:
        print(json.dumps([row.model_dump() for row in rows], ensure_ascii=False, indent=2))
    else:
        print("Scripted offline demonstration; not a live-model quality measurement.\n")
        print(_format_table(rows))


if __name__ == "__main__":
    main()
