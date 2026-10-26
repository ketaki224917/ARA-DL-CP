"""Fast checks for the curated, source-grounded sample reports."""

from pathlib import Path

from ara.agents.citations import validate_citations
from ara.generative.diagrams import validate_mermaid
from ara.generative.example_reports import (
    EXAMPLES,
    _render_markdown,
    _source_evidence,
    load_example_evidence,
)
from ara.generative.tts import NarrationScript

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_each_example_has_only_resolvable_citations_and_cited_claim_lines() -> None:
    evidence = load_example_evidence(REPO_ROOT)

    for spec in EXAMPLES:
        items = _source_evidence(evidence, spec)
        citations = " ".join(f"[{item.chunk_id}]" for item in items)
        markdown = _render_markdown(spec, citations)
        validation = validate_citations(markdown, evidence)
        assert validation.is_valid
        assert validation.cited_ids == [item.chunk_id for item in items]
        claim_lines = [
            line
            for line in spec.body.splitlines()
            if line.strip() and not line.startswith("## ")
        ]
        assert claim_lines
        assert all(line.endswith("[CITATION]") for line in claim_lines)
        combined_text = " ".join(item.text for item in items).casefold()
        assert all(phrase.casefold() in combined_text for phrase in spec.required_phrases)


def test_each_example_diagram_and_narration_meet_production_constraints() -> None:
    for spec in EXAMPLES:
        validate_mermaid(spec.mermaid)
        narration = NarrationScript(text=spec.narration)
        assert 170 <= narration.word_count <= 260
