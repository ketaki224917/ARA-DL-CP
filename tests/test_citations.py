"""Tests for deterministic citation parsing and evidence membership checks."""

from __future__ import annotations

import pytest

from ara.agents.citations import validate_citations


def test_valid_local_and_web_citations_are_preserved_in_order() -> None:
    evidence = {"chunk:local-a": object(), "web:page-b": object()}

    result = validate_citations(
        "Claim one [chunk:local-a]. Claim two [web:page-b].",
        evidence,
    )

    assert result.is_valid is True
    assert result.cited_ids == ["chunk:local-a", "web:page-b"]
    assert result.unknown_ids == []
    assert result.malformed_markers == []


def test_unknown_citations_are_reported_without_being_marked_malformed() -> None:
    result = validate_citations("Claim [chunk:missing].", {"chunk:known"})

    assert result.is_valid is False
    assert result.cited_ids == ["chunk:missing"]
    assert result.unknown_ids == ["chunk:missing"]
    assert result.malformed_markers == []


@pytest.mark.parametrize(
    "marker",
    [
        "[chunk:]",
        "[web:]",
        "[chunk:has space]",
        "[web:line\nbreak]",
        "[chunk:unfinished",
        "[web:outer[chunk:inner]]",
        f"[chunk:{'x' * 121}]",
    ],
)
def test_malformed_citation_markers_are_reported(marker: str) -> None:
    result = validate_citations(f"Text {marker}.", set())

    assert result.is_valid is False
    assert result.malformed_markers
    assert result.unknown_ids == []


def test_repeated_citations_are_deduplicated_and_normal_markdown_brackets_ignored() -> None:
    result = validate_citations(
        "A [chunk:one], repeated [chunk:one], [ordinary text], and [12].",
        {"chunk:one"},
    )

    assert result.is_valid is True
    assert result.cited_ids == ["chunk:one"]
    assert result.malformed_markers == []


def test_text_without_citations_is_valid_and_returns_no_ids() -> None:
    result = validate_citations("A report without citation tokens.", set())

    assert result.is_valid is True
    assert result.cited_ids == []
    assert result.unknown_ids == []
    assert result.malformed_markers == []


def test_validator_rejects_non_string_markdown() -> None:
    with pytest.raises(TypeError, match="markdown must be a string"):
        validate_citations(None, set())  # type: ignore[arg-type]
