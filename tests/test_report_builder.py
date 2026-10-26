"""Tests for cited Markdown, HTML, PDF, and asset assembly."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest
from pypdf import PdfReader

from ara.agents.state import EvidenceItem
from ara.generative.diagrams import DiagramArtifact
from ara.generative.report_builder import ReportBuildError, build_report

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="90" viewBox="0 0 320 90">'
    '<rect x="4" y="4" width="312" height="82" rx="8" fill="#eaf2f8"/>'
    '<text x="160" y="52" text-anchor="middle" font-size="20">Evidence flow</text>'
    "</svg>"
)


def _write_wav(path: Path, *, frames: int = 22_050) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22_050)
        wav_file.writeframes(b"\0\0" * frames)


def _evidence() -> dict[str, EvidenceItem]:
    items = [
        EvidenceItem(
            chunk_id="chunk:storage-1",
            text="Grid-scale batteries can shift electricity between hours.",
            source="papers/grid-storage.pdf",
            page=7,
        ),
        EvidenceItem(
            chunk_id="web:policy-2",
            text="Public policy can affect deployment timelines.",
            source="Energy Office",
            source_type="web",
            url="https://example.org/policy?region=north&year=2026",
        ),
    ]
    return {item.chunk_id: item for item in items}


def test_build_report_writes_cited_md_html_pdf_and_local_assets(tmp_path: Path) -> None:
    evidence = _evidence()
    audio_source = tmp_path / "narration.wav"
    _write_wav(audio_source)
    diagram = DiagramArtifact(
        mermaid='flowchart TD\nA["Evidence"] --> B["Report"]',
        svg=SVG,
        renderer="builtin-svg",
    )
    markdown = (
        "# Grid storage \u2014 findings\n\n"
        "Batteries shift electricity between hours [chunk:storage-1].\n\n"
        "Policy affects deployments [web:policy-2]."
    )

    result = build_report(
        markdown,
        evidence,
        tmp_path / "bundle",
        diagrams=[diagram],
        audio_path=audio_source,
    )

    assert result.citations == ("chunk:storage-1", "web:policy-2")
    assert result.markdown_path.is_file()
    assert result.html_path.is_file()
    assert result.pdf_path.is_file()
    assert result.figure_paths == (tmp_path / "bundle" / "figures" / "diagram-01.svg",)
    assert result.audio_path == tmp_path / "bundle" / "audio" / "narration.wav"

    report_md = result.markdown_path.read_text(encoding="utf-8")
    assert "Grid storage \u2014 findings" in report_md
    assert "[chunk:storage-1]" in report_md
    assert "[web:policy-2]" in report_md
    assert "grid-storage\\.pdf" in report_md
    assert "Page: 7" in report_md
    assert "https://example.org/policy?region=north&year=2026" in report_md
    assert "1-second narrated summary" in report_md

    report_html = result.html_path.read_text(encoding="utf-8")
    assert "<audio controls" in report_html
    assert 'src="figures/diagram-01.svg"' in report_html
    assert "References" in report_html

    pdf = PdfReader(result.pdf_path)
    assert len(pdf.pages) >= 1
    pdf_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    assert "Grid storage - findings" in pdf_text
    assert "[chunk:storage-1]" in pdf_text
    assert "grid-storage.pdf" in pdf_text
    assert "https://example.org/policy?region=north&year=2026" in pdf_text
    assert "Page 1" in pdf_text


@pytest.mark.parametrize(
    ("draft", "message"),
    [
        ("A claim [chunk:missing].", "unknown citation"),
        ("A claim [chunk:].", "malformed marker"),
    ],
)
def test_build_report_rejects_unknown_and_malformed_citations_before_writing(
    tmp_path: Path, draft: str, message: str
) -> None:
    output_dir = tmp_path / "bundle"

    with pytest.raises(ReportBuildError, match=message):
        build_report(draft, _evidence(), output_dir)

    assert not output_dir.exists()


@pytest.mark.parametrize(
    "unsafe_svg",
    [
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://bad.example/x"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><rect onclick="alert(1)"/></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><style>@import url(https://bad.example/x);</style></svg>',
        '<?xml-stylesheet href="https://bad.example/style.css"?><svg xmlns="http://www.w3.org/2000/svg"/>',
    ],
)
def test_build_report_rejects_active_or_external_svg(tmp_path: Path, unsafe_svg: str) -> None:
    diagram = DiagramArtifact(mermaid="flowchart TD", svg=unsafe_svg, renderer="builtin-svg")

    with pytest.raises(ReportBuildError, match="SVG"):
        build_report("# A report", {}, tmp_path, diagrams=[diagram])


def test_build_report_rejects_invalid_audio_and_unsafe_basename(tmp_path: Path) -> None:
    audio_path = tmp_path / "bad.wav"
    audio_path.write_bytes(b"not a wave")

    with pytest.raises(ReportBuildError, match="valid WAV"):
        build_report("# A report", {}, tmp_path / "audio-case", audio_path=audio_path)

    with pytest.raises(ValueError, match="basename"):
        build_report("# A report", {}, tmp_path / "name-case", basename="../report")


def test_build_report_escapes_raw_html_in_the_html_version(tmp_path: Path) -> None:
    result = build_report("# A report\n\n<script>alert('unsafe')</script>", {}, tmp_path)

    rendered = result.html_path.read_text(encoding="utf-8")
    assert "&lt;script&gt;" in rendered
    assert "<script>alert('unsafe')</script>" not in rendered
