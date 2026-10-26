"""Capped report revision loop with deterministic stopping and iteration metrics."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from ara.agents.citations import validate_citations
from ara.agents.critic import CriticResult
from ara.agents.state import AgentState, Critique, EvidenceItem
from ara.agents.trace import TraceEvent, make_trace_event
from ara.agents.writer import WriterResult

logger = logging.getLogger(__name__)
_CITATION_MARKER = re.compile(r"\[(?:chunk|web):[^\s\[\]]{1,120}\]")
_BULLET_PREFIX = re.compile(r"^(?:[-*+]\s+|[0-9]+\.\s+)")

RevisionTraceCallback = Callable[[TraceEvent], None]


class RevisionLoopError(RuntimeError):
    """Raised when drafting or critique fails during a revision run."""


class RevisionWriter(Protocol):
    """Writer interface consumed by the revision loop."""

    def write(self, state: AgentState) -> WriterResult: ...


class RevisionCritic(Protocol):
    """Critic interface consumed by the revision loop."""

    def review(self, state: AgentState) -> CriticResult: ...


class RevisionIterationStats(BaseModel):
    """Counts from reviewing one draft at a specific revision number."""

    model_config = ConfigDict(extra="forbid")

    iteration: int = Field(ge=0)
    revision_count: int = Field(ge=0)
    reviewed_claim_count: int = Field(ge=0)
    supported_claim_count: int = Field(ge=0)
    unsupported_claim_count: int = Field(ge=0)
    gap_count: int = Field(ge=0)
    contradiction_count: int = Field(ge=0)
    finding_count: int = Field(ge=0)


class RevisionLoopResult(BaseModel):
    """Final report, stopping reason, and per-draft critique statistics."""

    model_config = ConfigDict(extra="forbid")

    final_draft: str = Field(min_length=1, max_length=20_000)
    abstained: bool
    stop_reason: Literal["clean", "abstained", "revision_cap", "unchanged_draft"]
    revision_count: int = Field(ge=0, le=20)
    iterations: list[RevisionIterationStats] = Field(min_length=1, max_length=21)


class RevisionLoop:
    """Generate and critique reports until clean, abstained, unchanged, or capped."""

    def __init__(
        self,
        writer: RevisionWriter,
        critic: RevisionCritic,
        *,
        trace_callback: RevisionTraceCallback | None = None,
    ) -> None:
        self._writer = writer
        self._critic = critic
        self._trace_callback = trace_callback

    def run(self, state: AgentState) -> RevisionLoopResult:
        """Run one new report cycle using the revision cap in `RunMetadata`."""
        if state.draft is not None or state.critiques or state.revision_count != 0:
            raise RevisionLoopError(
                "A revision loop must start without a draft, critiques, or prior revisions."
            )

        try:
            writer_result = self._writer.write(state)
        except Exception as exc:
            raise RevisionLoopError("Could not generate the initial report draft.") from exc
        state.draft = writer_result.markdown
        iterations: list[RevisionIterationStats] = []

        while True:
            try:
                critique_result = self._critic.review(state)
            except Exception as exc:
                raise RevisionLoopError(
                    f"Could not review report revision {state.revision_count}."
                ) from exc
            state.critiques = critique_result.critiques
            iterations.append(
                RevisionIterationStats(
                    iteration=len(iterations),
                    revision_count=state.revision_count,
                    reviewed_claim_count=critique_result.reviewed_claim_count,
                    supported_claim_count=critique_result.supported_claim_count,
                    unsupported_claim_count=critique_result.unsupported_claim_count,
                    gap_count=critique_result.gap_count,
                    contradiction_count=critique_result.contradiction_count,
                    finding_count=len(critique_result.critiques),
                )
            )
            self._emit_iteration_trace(state, iterations[-1])

            if writer_result.abstained:
                stop_reason: Literal[
                    "clean", "abstained", "revision_cap", "unchanged_draft"
                ] = "abstained"
                break
            if not critique_result.critiques:
                stop_reason = "clean"
                break
            if state.revision_count >= state.run_metadata.max_revisions:
                stop_reason = "revision_cap"
                break

            previous_draft = state.draft
            state.increment_revision()
            try:
                writer_result = self._writer.write(state)
            except Exception as exc:
                raise RevisionLoopError(
                    f"Could not generate report revision {state.revision_count}."
                ) from exc
            if writer_result.abstained:
                recovery = _recover_supported_draft(
                    previous_draft,
                    state.critiques,
                    state.evidence_store,
                )
                if recovery is not None:
                    writer_result, removed_count = recovery
                    logger.warning(
                        "Revision writer abstained; removed %d critic-flagged claims "
                        "and retained %d cited claims",
                        removed_count,
                        len(writer_result.cited_evidence_ids),
                    )
                    self._emit_recovery_trace(state, removed_count, writer_result)
            state.draft = writer_result.markdown
            if state.draft == previous_draft:
                stop_reason = "unchanged_draft"
                break

        if state.draft is None:
            raise RevisionLoopError("The report writer did not leave a final draft in state.")
        self._emit_stop_trace(state, stop_reason, len(iterations))
        return RevisionLoopResult(
            final_draft=state.draft,
            abstained=writer_result.abstained,
            stop_reason=stop_reason,
            revision_count=state.revision_count,
            iterations=iterations,
        )

    def _emit_recovery_trace(
        self,
        state: AgentState,
        removed_count: int,
        result: WriterResult,
    ) -> None:
        if self._trace_callback is None:
            return
        self._trace_callback(
            make_trace_event(
                state.run_metadata.run_id,
                agent="revision_loop",
                event="revision_recovered",
                result_summary=(
                    f"removed_claims={removed_count}; "
                    f"retained_citations={len(result.cited_evidence_ids)}; "
                    "method=critic-filter"
                ),
            )
        )

    def _emit_iteration_trace(
        self,
        state: AgentState,
        stats: RevisionIterationStats,
    ) -> None:
        if self._trace_callback is None:
            return
        self._trace_callback(
            make_trace_event(
                state.run_metadata.run_id,
                agent="revision_loop",
                event="iteration_reviewed",
                result_summary=(
                    f"iteration={stats.iteration}; revision={stats.revision_count}; "
                    f"reviewed={stats.reviewed_claim_count}; "
                    f"supported={stats.supported_claim_count}; "
                    f"unsupported={stats.unsupported_claim_count}; "
                    f"gaps={stats.gap_count}; contradictions={stats.contradiction_count}; "
                    f"findings={stats.finding_count}"
                ),
            )
        )

    def _emit_stop_trace(
        self,
        state: AgentState,
        reason: Literal["clean", "abstained", "revision_cap", "unchanged_draft"],
        iterations: int,
    ) -> None:
        if self._trace_callback is None:
            return
        self._trace_callback(
            make_trace_event(
                state.run_metadata.run_id,
                agent="revision_loop",
                event="loop_stopped",
                result_summary=(
                    f"reason={reason}; revisions={state.revision_count}; iterations={iterations}"
                ),
            )
        )


def _recover_supported_draft(
    previous_draft: str,
    critiques: list[Critique],
    evidence: dict[str, EvidenceItem],
) -> tuple[WriterResult, int] | None:
    """Drop critic-flagged claims while preserving the remaining cited draft."""
    removable_claims = {
        _normalize_claim(critique.claim)
        for critique in critiques
        if critique.issue in {"unsupported", "miscited", "contradiction", "clarity"}
    }
    if not removable_claims:
        return None

    retained_lines: list[str] = []
    removed_count = 0
    for line in previous_draft.splitlines():
        claim_text = _normalize_claim(_CITATION_MARKER.sub("", line))
        if claim_text in removable_claims:
            removed_count += 1
            continue
        retained_lines.append(line)
    if removed_count == 0:
        return None

    markdown = "\n".join(retained_lines).strip()
    citations = validate_citations(markdown, evidence)
    if not citations.is_valid or not citations.cited_ids:
        return None
    remaining_claims = [
        line
        for line in markdown.splitlines()
        if line.strip()
        and not line.lstrip().startswith("#")
        and _CITATION_MARKER.search(line)
    ]
    if not remaining_claims:
        return None
    return (
        WriterResult(
            markdown=markdown,
            cited_evidence_ids=citations.cited_ids,
            abstained=False,
        ),
        removed_count,
    )


def _normalize_claim(value: str) -> str:
    """Normalize a draft line or critic claim for exact matching."""
    value = _BULLET_PREFIX.sub("", value)
    return " ".join(value.split()).strip(" \t,;")


__all__ = [
    "RevisionCritic",
    "RevisionIterationStats",
    "RevisionLoop",
    "RevisionLoopError",
    "RevisionLoopResult",
    "RevisionTraceCallback",
    "RevisionWriter",
]
