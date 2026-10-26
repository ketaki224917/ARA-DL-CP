"""Build three reproducible, evidence-grounded example report bundles."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from ara.agents.citations import validate_citations
from ara.agents.state import EvidenceItem
from ara.config import Settings, load_settings
from ara.generative.diagrams import DiagramResponse, generate_diagram
from ara.generative.report_builder import build_report
from ara.generative.tts import NarrationScript, synthesize_narration
from ara.llm.client import ChatMessage
from ara.rag.chunking import DocumentChunk, chunk_documents
from ara.rag.ingest import load_file

logger = logging.getLogger(__name__)

_T = TypeVar("_T", bound=DiagramResponse)


@dataclass(frozen=True, slots=True)
class ExampleSpec:
    """Curated report content grounded in one original sample-corpus note."""

    slug: str
    title: str
    source: str
    required_phrases: tuple[str, ...]
    body: str
    mermaid: str
    narration: str


EXAMPLES = (
    ExampleSpec(
        slug="hybrid-retrieval",
        title="Hybrid Retrieval: Complementary Signals Need Evaluation",
        source="03_hybrid_retrieval.md",
        required_phrases=(
            "dense search can surface a paraphrase",
            "lexical search can preserve a rare token",
            "fusion cannot recover a passage",
            "evaluate the full pipeline on labeled questions",
        ),
        body=(
            "## Summary\n\n"
            "Hybrid retrieval combines dense semantic search with sparse lexical search, then "
            "orders the combined candidates with a fusion rule. [CITATION]\n\n"
            "Dense search can surface a paraphrase, while lexical search can retain a rare token "
            "or exact code. [CITATION]\n\n"
            "## Evaluation considerations\n\n"
            "Fusion cannot recover a passage that neither component retrieved, so candidate depth "
            "sets a limit on the evidence available to later stages. [CITATION]\n\n"
            "The source recommends evaluating the complete pipeline on labeled questions; calling "
            "a method hybrid does not itself show that retrieval improved. [CITATION]\n\n"
            "## Scope\n\n"
            "This example summarizes one ARA corpus note. It reports no retrieval benchmark "
            "measurements. [CITATION]"
        ),
        mermaid=(
            'flowchart TD\nA["Dense semantic search"]\nB["Sparse lexical search"]\n'
            'C["Candidate pool"]\nD["Fusion ranking"]\nE["Labeled evaluation"]\n'
            "A --> C\nB --> C\nC --> D\nD --> E"
        ),
        narration=(
            "This report describes hybrid retrieval using one ARA sample corpus note. Hybrid "
            "retrieval combines dense semantic search and sparse lexical search, then orders the "
            "combined candidates with a fusion rule. Dense search can surface a paraphrase. "
            "Lexical "
            "search can preserve a rare token or an exact code. Those signals can complement one "
            "another, but the combination has a clear limit: fusion cannot recover a passage that "
            "neither component search returned. Candidate depth therefore matters because each "
            "retrieval leg must pass plausible results into fusion. The source note recommends "
            "evaluating the full pipeline on labeled questions. A hybrid label alone does not "
            "demonstrate better retrieval. This example contains no measured benchmark results and "
            "does not claim that one fusion strategy wins. Its diagram shows the described path "
            "from two retrieval signals through a candidate pool and fusion to evaluation. The "
            "report's reference section identifies the exact source chunks behind each cited "
            "claim. "
            "The chunk identifiers are generated from the repository's configured ingestion and "
            "chunking process, so a reader can reproduce it from the sample corpus. The main "
            "practical takeaway is to measure candidate coverage and end-to-end ranking on labeled "
            "questions before drawing conclusions about a hybrid system."
        ),
    ),
    ExampleSpec(
        slug="citation-provenance",
        title="Citation Provenance: Stable IDs Connect Claims to Evidence",
        source="11_chunk_citation_metadata.md",
        required_phrases=(
            "stable identifier that connects it to its source text",
            "source path or URL",
            "character offsets",
            "validate that the ID exists in the evidence store",
        ),
        body=(
            "## Summary\n\n"
            "A citation-ready passage needs a stable identifier that connects the indexed text to "
            "its source. [CITATION]\n\n"
            "## Provenance metadata\n\n"
            "Useful metadata includes the source path or URL, a page when available, and character "
            "offsets in the extracted document. [CITATION]\n\n"
            "The source note says an identifier should be deterministic for the same source and "
            "chunking settings, allowing evaluation records to keep pointing to the same evidence. "
            "[CITATION]\n\n"
            "## Validation\n\n"
            "When a report cites a chunk, validate that its ID exists in the evidence store, then "
            "resolve the ID to stored text and metadata before review. [CITATION]\n\n"
            "That process makes a citation a verifiable connection between a claim and its offered "
            "passage. [CITATION]\n\n"
            "## Scope\n\n"
            "This example explains the corpus note's provenance guidance; it does not claim that "
            "all identifiers remain stable after source or chunking changes. [CITATION]"
        ),
        mermaid=(
            'flowchart TD\nA["Source and metadata"]\nB["Chunk with stable ID"]\n'
            'C["Evidence store"]\nD["Validate claim"]\nA --> B\nB --> C\nC --> D'
        ),
        narration=(
            "This report focuses on citation provenance: the connection between a report claim and "
            "the passage offered to support it. The ARA corpus note says each indexed passage "
            "needs a stable identifier that connects it to its source text. Useful metadata "
            "includes "
            "a source path or URL, a page when one is available, and character offsets in the "
            "extracted document. The identifier should be deterministic for the same source and "
            "chunking settings, so evaluation records can continue to point to the same evidence. "
            "That condition is scoped: changing the source or the chunking settings may produce a "
            "different identifier. Before a citation is accepted, the application should validate "
            "that the identifier exists in the evidence store. It should then resolve that ID to "
            "the stored text and metadata before a critic reviews the claim. This turns citation "
            "checking into a concrete lookup instead of a visual check of bracketed text. The "
            "diagram follows the path from a source document through chunk text, offsets, and a "
            "stable ID to evidence storage, citation validation, and claim review. The report "
            "includes the actual chunk reference and source filename used for this example. It "
            "does not promise identifier stability when the underlying source or its processing "
            "configuration changes."
        ),
    ),
    ExampleSpec(
        slug="untrusted-evidence",
        title="Retrieved Text Is Evidence, Not an Instruction Channel",
        source="19_untrusted_retrieved_text.md",
        required_phrases=(
            "text that looks like a command to the model",
            "mark retrieved content as untrusted source material",
            "restrict which tools may be called",
            "does not make prompt injection impossible",
        ),
        body=(
            "## Summary\n\n"
            "Retrieved documents and web pages can contain text that looks like a command to the "
            "model. [CITATION]\n\n"
            "## Instruction boundary\n\n"
            "The source note recommends marking retrieved content as untrusted source material, "
            "keeping application instructions separate, and telling the model not to follow "
            "instructions embedded in evidence. [CITATION]\n\n"
            "It also recommends restricting which tools may be called and validating tool "
            "arguments independently. [CITATION]\n\n"
            "## Limits and tests\n\n"
            "This boundary does not make prompt injection impossible; the note describes it as a "
            "way to reduce confusion between the question, instructions, and analyzed material. "
            "[CITATION]\n\n"
            "The note recommends hostile-document tests that check whether the researcher "
            "summarizes factual content without carrying out embedded requests. [CITATION]\n\n"
            "## Scope\n\n"
            "This example reports the documented design guidance and makes no claim of complete "
            "protection. [CITATION]"
        ),
        mermaid=(
            'flowchart TD\nA["Question and instructions"]\nB["Untrusted retrieved text"]\n'
            'C["Validate tool arguments"]\nD["Summarize and test"]\n'
            "A --> B\nB --> C\nC --> D"
        ),
        narration=(
            "Retrieved documents and web pages may contain text that looks like a command to a "
            "model. The ARA corpus note treats those passages as source material, not as a second "
            "instruction channel. It recommends marking retrieved content as untrusted, keeping "
            "the application's instructions separate, and telling the model not to follow commands "
            "embedded in the evidence. The application also has a role: restrict which tools may "
            "be called and validate tool arguments independently. These boundaries reduce "
            "confusion between the research question, the agent's instructions, and the content "
            "being analyzed. They do not make prompt injection impossible, and this report does "
            "not claim complete protection. The source note recommends testing with documents that "
            "contain hostile instructions. A useful check is whether the researcher summarizes "
            "factual content while refusing to carry out the document's embedded requests. The "
            "diagram sketches that boundary from a research question and separated instructions "
            "to untrusted text, argument validation, evidence summarization, and a "
            "hostile-document "
            "test. The cited source chunk provides the specific design guidance summarized here. "
            "A deployed system still needs independent testing of its tools, prompts, and "
            "failure behavior."
        ),
    ),
)


class _FixedDiagramClient:
    """Return a pre-reviewed flowchart through the production structured-output interface."""

    def __init__(self, mermaid: str) -> None:
        self._mermaid = mermaid

    def structured_output(
        self,
        messages: Sequence[ChatMessage],
        schema: type[_T],
        *,
        max_retries: int = 3,
    ) -> _T:
        del messages, max_retries
        return schema(mermaid=self._mermaid)


def load_example_evidence(
    repo_root: Path, settings: Settings | None = None
) -> dict[str, EvidenceItem]:
    """Derive the cited evidence from the sample notes with the production chunker."""
    resolved_settings = settings or load_settings(repo_root / "config.yaml", repo_root / ".env")
    sources = {spec.source for spec in EXAMPLES}
    documents = [
        document
        for source in sorted(sources)
        for document in load_file(
            repo_root / "data" / "sample_corpus" / source,
            source=Path("data/sample_corpus").joinpath(source).as_posix(),
        )
    ]
    chunks = chunk_documents(
        documents,
        chunk_size=resolved_settings.retrieval_chunk_size,
        overlap=resolved_settings.retrieval_chunk_overlap,
    )
    by_source: dict[str, list[DocumentChunk]] = {}
    for chunk in chunks:
        by_source.setdefault(Path(chunk.source).name, []).append(chunk)

    evidence: dict[str, EvidenceItem] = {}
    for spec in EXAMPLES:
        matches = by_source.get(spec.source, [])
        if not matches:
            raise ValueError(
                f"Expected evidence chunks for {spec.source}; found none. "
                "Review the sample note and configured chunk size."
            )
        normalized_text = " ".join(chunk.text for chunk in matches).casefold()
        missing = [
            phrase for phrase in spec.required_phrases if phrase.casefold() not in normalized_text
        ]
        if missing:
            raise ValueError(f"{spec.source} is missing required evidence phrases: {missing}")
        for chunk in matches:
            evidence[chunk.chunk_id] = EvidenceItem(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                source=chunk.source,
                page=chunk.page,
            )
    return evidence


def _source_evidence(evidence: Mapping[str, EvidenceItem], spec: ExampleSpec) -> list[EvidenceItem]:
    return [item for item in evidence.values() if Path(item.source).name == spec.source]


def _render_markdown(spec: ExampleSpec, citations: str) -> str:
    return f"# {spec.title}\n\n" + spec.body.replace("[CITATION]", citations)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate_examples(repo_root: Path, output_dir: Path) -> None:
    """Generate cited MD/HTML/PDF reports, constrained SVG diagrams, and Piper audio."""
    settings = load_settings(repo_root / "config.yaml", repo_root / ".env")
    evidence = load_example_evidence(repo_root, settings)
    output_dir.mkdir(parents=True, exist_ok=True)
    voice_path = settings.tts_voice_model_path
    if not voice_path.is_absolute():
        voice_path = repo_root / voice_path

    for spec in EXAMPLES:
        source_items = _source_evidence(evidence, spec)
        if not source_items:
            raise ValueError(f"No derived evidence chunks for {spec.source}")
        source_ids = [item.chunk_id for item in source_items]
        citations = " ".join(f"[{citation_id}]" for citation_id in source_ids)
        markdown = _render_markdown(spec, citations)
        validation = validate_citations(markdown, evidence)
        if not validation.is_valid or validation.cited_ids != source_ids:
            raise ValueError(f"Citation validation failed for {spec.slug}: {validation}")

        bundle_dir = output_dir / spec.slug
        bundle_dir.mkdir(parents=True, exist_ok=True)
        diagram = generate_diagram(markdown, llm_client=_FixedDiagramClient(spec.mermaid))
        (bundle_dir / "figures").mkdir(parents=True, exist_ok=True)
        (bundle_dir / "figures" / "diagram-01.mmd").write_text(
            diagram.mermaid + "\n", encoding="utf-8"
        )
        audio_temp = bundle_dir / ".narration-source.wav"
        try:
            synthesize_narration(
                NarrationScript(text=spec.narration),
                audio_temp,
                voice_model_path=voice_path,
            )
            artifacts = build_report(
                markdown,
                evidence,
                bundle_dir,
                diagrams=[diagram],
                audio_path=audio_temp,
                basename="report",
            )
        finally:
            audio_temp.unlink(missing_ok=True)

        _write_json(
            bundle_dir / "evidence.json",
            {
                "chunk_size": settings.retrieval_chunk_size,
                "chunk_overlap": settings.retrieval_chunk_overlap,
                "license": "CC BY 4.0",
                "evidence": [
                    item.model_dump(mode="json", exclude={"retrieved_at"})
                    for item in source_items
                ],
            },
        )
        final_markdown = artifacts.markdown_path.read_text(encoding="utf-8")
        validation = validate_citations(final_markdown, evidence)
        if not validation.is_valid or set(validation.cited_ids) != set(artifacts.citations):
            raise ValueError(
                f"Generated report failed citation validation: {artifacts.markdown_path}"
            )
        logger.info(
            "Generated %s with %d citation ID(s), %d figure(s), audio=%s",
            spec.slug,
            len(artifacts.citations),
            len(artifacts.figure_paths),
            artifacts.audio_path is not None,
        )


def validate_examples(repo_root: Path, output_dir: Path) -> int:
    """Validate citations, linked assets, PDF readability, and stored evidence metadata."""
    evidence = load_example_evidence(repo_root)
    total_citations = 0
    for spec in EXAMPLES:
        bundle_dir = output_dir / spec.slug
        markdown_path = bundle_dir / "report.md"
        if not markdown_path.is_file():
            raise FileNotFoundError(f"Missing report Markdown: {markdown_path}")
        result = validate_citations(markdown_path.read_text(encoding="utf-8"), evidence)
        expected = [item.chunk_id for item in _source_evidence(evidence, spec)]
        if not result.is_valid or result.cited_ids != expected:
            raise ValueError(f"Citation validation failed for {markdown_path}: {result}")
        if not (bundle_dir / "report.html").is_file():
            raise FileNotFoundError(f"Missing HTML report in {bundle_dir}")
        pdf_path = bundle_dir / "report.pdf"
        from pypdf import PdfReader

        if not PdfReader(str(pdf_path)).pages:
            raise ValueError(f"PDF has no pages: {pdf_path}")
        svg_path = bundle_dir / "figures" / "diagram-01.svg"
        if not svg_path.is_file():
            raise FileNotFoundError(f"Missing rendered SVG: {svg_path}")
        audio_path = bundle_dir / "audio" / "narration.wav"
        if not audio_path.is_file() or audio_path.stat().st_size == 0:
            raise FileNotFoundError(f"Missing narration audio: {audio_path}")
        stored = json.loads((bundle_dir / "evidence.json").read_text(encoding="utf-8"))
        stored_ids = [item["chunk_id"] for item in stored["evidence"]]
        if stored_ids != expected:
            raise ValueError(f"Stored evidence IDs do not match source chunks: {bundle_dir}")
        if any("retrieved_at" in item for item in stored["evidence"]):
            raise ValueError("Static example evidence must not have a generated retrieval time")
        total_citations += len(result.cited_ids)
        logger.info("Validated %s: %d source chunk(s)", spec.slug, len(expected))
    return total_citations


def main() -> None:
    """Run generation and deterministic validation from the repository root."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Report output directory (defaults to outputs/examples).",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate existing bundles without regenerating the PDFs and narration.",
    )
    arguments = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[3]
    output_dir = arguments.output_dir or repo_root / "outputs" / "examples"
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir
    output_dir = output_dir.resolve()
    if not arguments.validate_only:
        generate_examples(repo_root, output_dir)
    citation_count = validate_examples(repo_root, output_dir)
    logger.info(
        "Validated %d example report citation(s) across %d bundles",
        citation_count,
        len(EXAMPLES),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
