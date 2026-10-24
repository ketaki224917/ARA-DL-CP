"""Evidence-based critique of report claims, citations, gaps, and contradictions."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Literal, Protocol, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from ara.agents.citations import validate_citations
from ara.agents.prompts.critic import critic_messages
from ara.agents.state import AgentState, Critique, EvidenceItem, PlanTask
from ara.llm.client import ChatMessage, OllamaClient

_CLAIM_ID_PATTERN = re.compile(r"claim-[0-9]{3,6}\Z")
_CITATION_TOKEN = re.compile(r"\[((?:chunk|web):[^\s\[\]]{1,120})\]")
_BULLET_PREFIX = re.compile(r"^(?:[-*+]\s+|[0-9]+\.\s+)")
_ABSTENTION_DRAFT = (
    "# Research report\n\n## Executive summary\n\n"
    "There is not enough retrieved evidence to draft a supported report."
)
_MAX_CRITIQUE_FINDINGS = 100


class CriticError(RuntimeError):
    """Raised when the critic cannot safely review or validate a report draft."""


class ClaimForReview(BaseModel):
    """One Markdown report claim and its syntactically valid citation IDs."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    text: str = Field(min_length=1, max_length=5_000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=50)
    line_number: int = Field(ge=1)

    @field_validator("claim_id")
    @classmethod
    def validate_claim_id(cls, value: str) -> str:
        if not _CLAIM_ID_PATTERN.fullmatch(value):
            raise ValueError("claim_id must use the claim-NNN format")
        return value

    @field_validator("text")
    @classmethod
    def normalize_claim_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("claim text must not be blank")
        return normalized


class ClaimAssessment(BaseModel):
    """LLM-facing judgment for one claim against its cited evidence."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    verdict: Literal["supported", "unsupported", "uncertain"]
    details: str = Field(min_length=1, max_length=2_000)
    evidence_ids: list[str] = Field(min_length=1, max_length=50)
    suggested_revision: str | None = Field(default=None, max_length=2_000)

    @field_validator("claim_id")
    @classmethod
    def validate_claim_id(cls, value: str) -> str:
        if not _CLAIM_ID_PATTERN.fullmatch(value):
            raise ValueError("claim_id must use the claim-NNN format")
        return value

    @field_validator("details", "suggested_revision")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("review text must not be blank when provided")
        return normalized

    @field_validator("evidence_ids")
    @classmethod
    def require_unique_evidence_ids(cls, value: list[str]) -> list[str]:
        identifiers = [item.strip() for item in value]
        if any(not item for item in identifiers):
            raise ValueError("assessment evidence IDs must not be blank")
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("assessment evidence IDs must be unique")
        return identifiers


class CriticFinding(BaseModel):
    """Additional plan-gap, contradiction, or clarity finding from the critic."""

    model_config = ConfigDict(extra="forbid")

    issue: Literal["gap", "contradiction", "clarity"]
    claim_id: str | None = None
    task_id: str | None = None
    details: str = Field(min_length=1, max_length=2_000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=50)
    severity: Literal["low", "medium", "high"] = "medium"
    suggested_revision: str | None = Field(default=None, max_length=2_000)

    @field_validator("claim_id")
    @classmethod
    def validate_claim_id(cls, value: str | None) -> str | None:
        if value is not None and not _CLAIM_ID_PATTERN.fullmatch(value):
            raise ValueError("claim_id must use the claim-NNN format")
        return value

    @field_validator("task_id")
    @classmethod
    def normalize_task_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("task_id must not be blank when provided")
        return normalized

    @field_validator("details", "suggested_revision")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("finding text must not be blank when provided")
        return normalized

    @field_validator("evidence_ids")
    @classmethod
    def require_unique_evidence_ids(cls, value: list[str]) -> list[str]:
        identifiers = [item.strip() for item in value]
        if any(not item for item in identifiers):
            raise ValueError("finding evidence IDs must not be blank")
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("finding evidence IDs must be unique")
        return identifiers

    @model_validator(mode="after")
    def validate_target(self) -> Self:
        if self.issue == "gap":
            if self.task_id is None or self.claim_id is not None:
                raise ValueError("gap findings must target one task_id")
        elif self.claim_id is None or self.task_id is not None:
            raise ValueError("claim findings must target one claim_id")
        if self.issue == "contradiction" and len(self.evidence_ids) < 2:
            raise ValueError("contradiction findings must cite at least two evidence IDs")
        return self


class CriticResponse(BaseModel):
    """Strict structured response required from the LLM critic."""

    model_config = ConfigDict(extra="forbid")

    assessments: list[ClaimAssessment] = Field(max_length=100)
    findings: list[CriticFinding] = Field(default_factory=list, max_length=_MAX_CRITIQUE_FINDINGS)


class StructuredCriticLLM(Protocol):
    """Structured-output interface consumed by the critic."""

    def structured_output(
        self,
        messages: Sequence[ChatMessage],
        schema: type[CriticResponse],
        *,
        max_retries: int = 3,
    ) -> CriticResponse: ...


class CriticResult(BaseModel):
    """Validated critique and summary counts for one report draft."""

    model_config = ConfigDict(extra="forbid")

    critiques: list[Critique] = Field(default_factory=list, max_length=_MAX_CRITIQUE_FINDINGS)
    reviewed_claim_count: int = Field(ge=0)
    supported_claim_count: int = Field(ge=0)
    unsupported_claim_count: int = Field(ge=0)
    gap_count: int = Field(ge=0)
    contradiction_count: int = Field(ge=0)


class Critic:
    """Review report claims against cited evidence and persist structured issues."""

    def __init__(
        self,
        llm_client: StructuredCriticLLM | None = None,
        *,
        max_retries: int = 3,
        max_evidence_items: int = 50,
        max_evidence_chars: int = 60_000,
    ) -> None:
        if (
            isinstance(max_retries, bool)
            or not isinstance(max_retries, int)
            or not 0 <= max_retries <= 3
        ):
            raise ValueError("max_retries must be between 0 and 3")
        self._llm = llm_client if llm_client is not None else OllamaClient()
        self.max_retries = max_retries
        self.max_evidence_items = _positive_int(max_evidence_items, "max_evidence_items", 500)
        self.max_evidence_chars = _positive_int(max_evidence_chars, "max_evidence_chars", 2_000_000)

    def review(self, state: AgentState) -> CriticResult:
        """Critique the current draft and replace `state.critiques` with its findings."""
        if state.draft is None:
            raise CriticError("AgentState has no report draft to review.")
        if state.draft.strip() == _ABSTENTION_DRAFT:
            result = _result_from_issues([], 0, 0, 0)
            _store_result(state, result)
            return result

        claims = _extract_claims(state.draft)
        if not claims:
            raise CriticError("The report draft contains no reviewable claims.")

        evidence_by_id = state.evidence_store
        selected, omitted_ids = _select_evidence(
            evidence_by_id.values(),
            required_ids=[identifier for claim in claims for identifier in claim.evidence_ids],
            max_items=self.max_evidence_items,
            max_chars=self.max_evidence_chars,
        )
        selected_ids = {item.chunk_id for item in selected}
        local_issues: list[Critique] = []
        reviewable: list[ClaimForReview] = []
        unsupported_claim_ids: set[str] = set()

        for claim in claims:
            line = state.draft.splitlines()[claim.line_number - 1]
            check = validate_citations(line, evidence_by_id)
            problems: list[str] = []
            if not claim.evidence_ids:
                problems.append("The claim has no citation.")
            if check.unknown_ids:
                problems.append("Unknown evidence IDs: " + ", ".join(check.unknown_ids) + ".")
            if check.malformed_markers:
                problems.append(
                    "Malformed citation markers: " + ", ".join(check.malformed_markers) + "."
                )
            omitted = [identifier for identifier in claim.evidence_ids if identifier in omitted_ids]
            if omitted:
                problems.append(
                    "Cited evidence exceeded the critic context budget: "
                    + ", ".join(omitted)
                    + "."
                )
            if problems:
                local_issues.append(
                    Critique(
                        issue="miscited",
                        claim=claim.text,
                        details=" ".join(problems),
                        evidence_ids=claim.evidence_ids,
                        severity="high",
                        suggested_revision="Add valid citations to evidence that can be reviewed.",
                    )
                )
                unsupported_claim_ids.add(claim.claim_id)
            else:
                reviewable.append(claim)

        response: CriticResponse | None = None
        if reviewable:
            context = [item for item in selected if item.chunk_id in selected_ids]
            try:
                response = self._llm.structured_output(
                    critic_messages(state.topic, state.plan, reviewable, context),
                    CriticResponse,
                    max_retries=self.max_retries,
                )
            except Exception as exc:
                raise CriticError("Could not produce a validated report critique.") from exc

        if response is None:
            result = _result_from_issues(
                local_issues,
                len(claims),
                0,
                len(unsupported_claim_ids),
            )
            _store_result(state, result)
            return result

        try:
            result = _validate_and_convert_response(
                response,
                claims=reviewable,
                plan=state.plan,
                known_evidence_ids=selected_ids,
                local_issues=local_issues,
                total_claim_count=len(claims),
                local_unsupported_count=len(unsupported_claim_ids),
            )
        except (ValueError, ValidationError) as exc:
            raise CriticError(
                "The critic returned references outside the supplied review data."
            ) from exc
        _store_result(state, result)
        return result


def _extract_claims(markdown: str) -> list[ClaimForReview]:
    claims: list[ClaimForReview] = []
    for line_number, raw_line in enumerate(markdown.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#") or line in {"---", "***", "___"}:
            continue
        content = _BULLET_PREFIX.sub("", line, count=1)
        citation_ids = [match.group(1) for match in _CITATION_TOKEN.finditer(content)]
        text = _CITATION_TOKEN.sub("", content)
        text = re.sub(r"\s+", " ", text).strip(" \t,;")
        if not text:
            continue
        claims.append(
            ClaimForReview(
                claim_id=f"claim-{len(claims) + 1:03d}",
                text=text,
                evidence_ids=list(dict.fromkeys(citation_ids)),
                line_number=line_number,
            )
        )
    return claims


def _select_evidence(
    evidence: Iterable[EvidenceItem],
    *,
    required_ids: Sequence[str],
    max_items: int,
    max_chars: int,
) -> tuple[list[EvidenceItem], set[str]]:
    """Prioritize report-cited evidence and keep complete records within limits."""
    by_id = {item.chunk_id: item for item in evidence}
    ordered_ids = list(dict.fromkeys(required_ids))
    ordered_items = [by_id[item_id] for item_id in ordered_ids if item_id in by_id]
    required_count = len(ordered_items)
    extras = sorted(
        (item for item in by_id.values() if item.chunk_id not in set(ordered_ids)),
        key=lambda item: item.score or 0.0,
        reverse=True,
    )
    selected: list[EvidenceItem] = []
    omitted: set[str] = set()
    remaining_chars = max_chars
    for item in [*ordered_items, *extras]:
        if len(selected) >= max_items or len(item.text) > remaining_chars:
            if len(selected) < required_count:
                omitted.add(item.chunk_id)
            continue
        selected.append(item)
        remaining_chars -= len(item.text)
    return selected, omitted


def _validate_and_convert_response(
    response: CriticResponse,
    *,
    claims: Sequence[ClaimForReview],
    plan: Sequence[PlanTask],
    known_evidence_ids: set[str],
    local_issues: Sequence[Critique],
    total_claim_count: int,
    local_unsupported_count: int,
) -> CriticResult:
    claim_by_id = {claim.claim_id: claim for claim in claims}
    task_by_id = {task.task_id: task for task in plan}
    review_by_id = {review.claim_id: review for review in response.assessments}
    if set(review_by_id) != set(claim_by_id) or len(review_by_id) != len(response.assessments):
        raise ValueError("critic assessments must cover each supplied claim exactly once")

    issues = list(local_issues)
    unsupported_review_ids: set[str] = set()
    supported_review_ids: set[str] = set()
    contradicted_review_ids: set[str] = set()
    supported_count = 0
    for claim_id, claim in claim_by_id.items():
        review = review_by_id[claim_id]
        if set(review.evidence_ids) != set(claim.evidence_ids):
            raise ValueError("claim assessments must inspect all and only that claim's cited IDs")
        if not set(review.evidence_ids) <= known_evidence_ids:
            raise ValueError("claim assessment references unknown evidence")
        if review.verdict == "supported":
            supported_count += 1
            supported_review_ids.add(claim_id)
            continue
        unsupported_review_ids.add(claim_id)
        issues.append(
            Critique(
                issue="unsupported",
                claim=claim.text,
                details=review.details,
                evidence_ids=review.evidence_ids,
                severity="high" if review.verdict == "unsupported" else "medium",
                suggested_revision=review.suggested_revision,
            )
        )

    for finding in response.findings:
        if finding.claim_id is not None:
            target = claim_by_id.get(finding.claim_id)
            if target is None:
                raise ValueError("finding references an unknown claim")
            claim_text = target.text
            if finding.issue == "contradiction":
                contradicted_review_ids.add(finding.claim_id)
        else:
            assert finding.task_id is not None
            target_task = task_by_id.get(finding.task_id)
            if target_task is None:
                raise ValueError("gap finding references an unknown plan task")
            claim_text = target_task.question
        if not set(finding.evidence_ids) <= known_evidence_ids:
            raise ValueError("finding references evidence outside the critic context")
        issues.append(
            Critique(
                issue=finding.issue,
                claim=claim_text,
                details=finding.details,
                evidence_ids=finding.evidence_ids,
                severity=finding.severity,
                suggested_revision=finding.suggested_revision,
            )
        )

    if len(issues) > _MAX_CRITIQUE_FINDINGS:
        raise ValueError("critic returned too many findings")
    unsupported_count = local_unsupported_count + len(
        unsupported_review_ids | contradicted_review_ids
    )
    return _result_from_issues(
        issues,
        total_claim_count,
        supported_count - len(supported_review_ids & contradicted_review_ids),
        unsupported_count,
    )


def _result_from_issues(
    issues: Sequence[Critique],
    reviewed_claim_count: int,
    supported_claim_count: int,
    unsupported_claim_count: int,
) -> CriticResult:
    return CriticResult(
        critiques=list(issues),
        reviewed_claim_count=reviewed_claim_count,
        supported_claim_count=supported_claim_count,
        unsupported_claim_count=unsupported_claim_count,
        gap_count=sum(issue.issue == "gap" for issue in issues),
        contradiction_count=sum(issue.issue == "contradiction" for issue in issues),
    )


def _store_result(state: AgentState, result: CriticResult) -> None:
    state.critiques = result.critiques
    state.run_metadata.updated_at = datetime.now(UTC)


def _positive_int(value: int, name: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")
    return value


__all__ = [
    "ClaimAssessment",
    "ClaimForReview",
    "Critic",
    "CriticError",
    "CriticFinding",
    "CriticResponse",
    "CriticResult",
    "StructuredCriticLLM",
]
