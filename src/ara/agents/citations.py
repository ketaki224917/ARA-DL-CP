"""Deterministic citation parsing and evidence-ID validation for report drafts."""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping

from pydantic import BaseModel, ConfigDict, Field

_CITATION_START = re.compile(r"\[(?:chunk|web):")
_CITATION_ID = re.compile(r"(?:chunk|web):[^\s\[\]]{1,120}\Z")
_MAX_MALFORMED_MARKER_LENGTH = 256


class CitationValidationResult(BaseModel):
    """Parsed IDs and deterministic validation issues from one Markdown draft."""

    model_config = ConfigDict(extra="forbid")

    cited_ids: list[str] = Field(default_factory=list)
    unknown_ids: list[str] = Field(default_factory=list)
    malformed_markers: list[str] = Field(default_factory=list)
    is_valid: bool


def validate_citations(
    markdown: str,
    evidence: Collection[str] | Mapping[str, object],
) -> CitationValidationResult:
    """Extract unique citation tokens and check that each ID exists in evidence.

    Recognized citations use `[chunk:<id>]` or `[web:<id>]`, with a non-empty,
    whitespace-free ID of at most 120 characters. Bracketed text that starts
    with either citation prefix but violates that syntax is reported as malformed.
    Ordinary Markdown brackets are ignored.
    """
    if not isinstance(markdown, str):
        raise TypeError("markdown must be a string")
    known_ids = set(evidence.keys() if isinstance(evidence, Mapping) else evidence)
    cited_ids: list[str] = []
    unknown_ids: list[str] = []
    malformed_markers: list[str] = []

    cursor = 0
    while match := _CITATION_START.search(markdown, cursor):
        marker_start = match.start()
        closing_bracket = markdown.find("]", match.end())
        next_opening_bracket = markdown.find("[", match.end())
        malformed_boundary = (
            closing_bracket < 0
            or (next_opening_bracket >= 0 and next_opening_bracket < closing_bracket)
        )
        if malformed_boundary:
            end = min(len(markdown), marker_start + _MAX_MALFORMED_MARKER_LENGTH)
            if closing_bracket >= 0:
                end = min(closing_bracket + 1, end)
            _append_once(
                malformed_markers,
                markdown[marker_start:end],
            )
            if closing_bracket >= 0:
                # Consume the malformed outer marker as one unit so a nested
                # citation-looking string cannot be accepted independently.
                cursor = closing_bracket + 1
            else:
                next_marker = _CITATION_START.search(markdown, match.end())
                if next_marker is None:
                    break
                cursor = next_marker.start()
            continue

        assert closing_bracket >= 0
        marker = markdown[marker_start : closing_bracket + 1]
        citation_id = markdown[marker_start + 1 : closing_bracket]
        if not _CITATION_ID.fullmatch(citation_id):
            _append_once(malformed_markers, marker[:_MAX_MALFORMED_MARKER_LENGTH])
            cursor = closing_bracket + 1
            continue
        _append_once(cited_ids, citation_id)
        if citation_id not in known_ids:
            _append_once(unknown_ids, citation_id)
        cursor = closing_bracket + 1

    return CitationValidationResult(
        cited_ids=cited_ids,
        unknown_ids=unknown_ids,
        malformed_markers=malformed_markers,
        is_valid=not unknown_ids and not malformed_markers,
    )


def _append_once(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


__all__ = ["CitationValidationResult", "validate_citations"]
