"""Evidence-only report drafting with structured claims and inline citations."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ara.agents.prompts.writer import REPORT_SECTION_HEADINGS, writer_messages
from ara.agents.state import AgentState, EvidenceItem
from ara.llm.client import ChatMessage, OllamaClient

_MAX_REPORT_LENGTH = 20_000
_MAX_CLAIM_LENGTH = 5_000


class WriterError(RuntimeError):
    """Raised when a structured report cannot be safely produced or rendered."""


class WriterClaim(BaseModel):
    """One factual statement linked to the evidence records that support it."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=_MAX_CLAIM_LENGTH)
    evidence_ids: list[str] = Field(min_length=1, max_length=20)

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("claim text must not be blank")
        return normalized

    @field_validator("evidence_ids")
    @classmethod
    def normalize_evidence_ids(cls, value: list[str]) -> list[str]:
        identifiers = [item.strip() for item in value]
        if any(not item for item in identifiers):
            raise ValueError("claim evidence IDs must not be blank")
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("claim evidence IDs must be unique")
        return identifiers


class WriterSection(BaseModel):
    """One required report section containing cited factual claims."""

    model_config = ConfigDict(extra="forbid")

    heading: Literal[
        "Key findings",
        "Evidence synthesis",
        "Limitations",
        "Conclusion",
    ]
    claims: list[WriterClaim] = Field(min_length=1, max_length=20)


class ReportDraft(BaseModel):
    """Validated report structure returned by the local model."""

    model_config = ConfigDict(extra="forbid")

    abstain: bool
    abstention_reason: str | None = Field(default=None, max_length=1_000)
    title: str = Field(default="", max_length=200)
    summary: list[WriterClaim] = Field(default_factory=list, max_length=10)
    sections: list[WriterSection] = Field(default_factory=list, max_length=4)

    @field_validator("abstention_reason", "title")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("report text must not be blank when provided")
        return normalized

    @model_validator(mode="after")
    def validate_report_shape(self) -> Self:
        if self.abstain:
            if self.summary or self.sections or self.title:
                raise ValueError("abstaining reports must not contain title or report claims")
            if not self.abstention_reason:
                raise ValueError("abstaining reports must include a reason")
            return self

        if not self.title or not self.summary:
            raise ValueError("reports require a title and at least one summary claim")
        headings = [section.heading for section in self.sections]
        if tuple(headings) != REPORT_SECTION_HEADINGS:
            raise ValueError("reports must contain all required sections in the specified order")
        return self


class StructuredWriterLLM(Protocol):
    """Structured-output interface consumed by the report writer."""

    def structured_output(
        self,
        messages: Sequence[ChatMessage],
        schema: type[ReportDraft],
        *,
        max_retries: int = 3,
    ) -> ReportDraft: ...


class WriterResult(BaseModel):
    """Rendered Markdown and citation metadata returned by the writer."""

    model_config = ConfigDict(extra="forbid")

    markdown: str = Field(min_length=1, max_length=_MAX_REPORT_LENGTH)
    cited_evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    abstained: bool
    reason: str | None = Field(default=None, max_length=1_000)


class Writer:
    """Draft a sectioned report using only bounded evidence from `AgentState`."""

    def __init__(
        self,
        llm_client: StructuredWriterLLM | None = None,
        *,
        max_retries: int = 3,
        max_evidence_items: int = 20,
        max_evidence_chars: int = 30_000,
    ) -> None:
        if (
            isinstance(max_retries, bool)
            or not isinstance(max_retries, int)
            or not 0 <= max_retries <= 3
        ):
            raise ValueError("max_retries must be between 0 and 3")
        self._llm = llm_client if llm_client is not None else OllamaClient()
        self.max_retries = max_retries
        self.max_evidence_items = _positive_int(
            max_evidence_items,
            "max_evidence_items",
            100,
        )
        self.max_evidence_chars = _positive_int(
            max_evidence_chars,
            "max_evidence_chars",
            1_000_000,
        )

    def write(self, state: AgentState) -> WriterResult:
        """Create a grounded draft or a deterministic abstention and save it in state."""
        evidence = _select_evidence(
            state.evidence_store.values(),
            max_items=self.max_evidence_items,
            max_chars=self.max_evidence_chars,
        )
        if not evidence:
            result = _abstention_result("No evidence was retrieved for this topic.")
            state.draft = result.markdown
            state.run_metadata.updated_at = datetime.now(UTC)
            return result

        try:
            draft = self._llm.structured_output(
                writer_messages(state.topic, state.plan, evidence),
                ReportDraft,
                max_retries=self.max_retries,
            )
        except Exception as exc:
            raise WriterError("Could not produce a validated evidence-grounded report.") from exc

        if draft.abstain:
            result = _abstention_result(draft.abstention_reason or "The evidence is insufficient.")
        else:
            allowed_ids = {item.chunk_id for item in evidence}
            claims = [
                *draft.summary,
                *(claim for section in draft.sections for claim in section.claims),
            ]
            has_unknown_ids = any(
                evidence_id not in allowed_ids
                for claim in claims
                for evidence_id in claim.evidence_ids
            )
            if has_unknown_ids:
                result = _abstention_result(
                    "The model returned citations outside the supplied evidence."
                )
            else:
                markdown = _render_markdown(draft)
                cited_ids = list(
                    dict.fromkeys(
                        evidence_id
                        for claim in claims
                        for evidence_id in claim.evidence_ids
                    )
                )
                try:
                    result = WriterResult(
                        markdown=markdown,
                        cited_evidence_ids=cited_ids,
                        abstained=False,
                    )
                except ValidationError as exc:
                    raise WriterError(
                        "The rendered report exceeded the supported size limit."
                    ) from exc

        try:
            state.draft = result.markdown
        except ValidationError as exc:
            raise WriterError("The rendered report exceeded the shared state size limit.") from exc
        state.run_metadata.updated_at = datetime.now(UTC)
        return result


def _positive_int(value: int, name: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")
    return value


def _select_evidence(
    items: Iterable[EvidenceItem],
    *,
    max_items: int,
    max_chars: int,
) -> list[EvidenceItem]:
    ordered = sorted(items, key=lambda item: item.score or 0.0, reverse=True)
    selected: list[EvidenceItem] = []
    remaining_chars = max_chars
    for item in ordered:
        if len(selected) >= max_items or remaining_chars <= 0:
            break
        text = item.text[:remaining_chars]
        if not text:
            continue
        selected.append(item.model_copy(update={"text": text}))
        remaining_chars -= len(text)
    return selected


def _render_markdown(draft: ReportDraft) -> str:
    lines = [f"# {draft.title}", "", "## Executive summary", ""]
    lines.extend(_render_claim(claim) for claim in draft.summary)
    for section in draft.sections:
        lines.extend(["", f"## {section.heading}", ""])
        lines.extend(_render_claim(claim) for claim in section.claims)
    return "\n".join(lines).strip()


def _render_claim(claim: WriterClaim) -> str:
    citations = " ".join(f"[{evidence_id}]" for evidence_id in claim.evidence_ids)
    return f"- {claim.text} {citations}"


def _abstention_result(reason: str) -> WriterResult:
    return WriterResult(
        markdown=(
            "# Research report\n\n"
            "## Executive summary\n\n"
            "There is not enough retrieved evidence to draft a supported report."
        ),
        abstained=True,
        reason=reason,
    )


__all__ = [
    "ReportDraft",
    "StructuredWriterLLM",
    "Writer",
    "WriterClaim",
    "WriterError",
    "WriterResult",
    "WriterSection",
]
