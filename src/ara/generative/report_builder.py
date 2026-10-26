"""Assemble a cited Markdown report and its HTML/PDF versions and local assets."""

from __future__ import annotations

import html
import logging
import os
import re
import shutil
import tempfile
import wave
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

from ara.agents.citations import validate_citations
from ara.agents.state import EvidenceItem
from ara.generative.diagrams import DiagramArtifact

logger = logging.getLogger(__name__)

_MAX_REPORT_CHARS = 20_000
_MAX_SVG_BYTES = 2_000_000
_REPORT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_UNSAFE_SVG_ELEMENTS = {"script", "foreignobject", "iframe", "image", "audio", "video"}
_PDF_DASHES = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
    }
)
_SVG_NAMESPACE = "http://www.w3.org/2000/svg"


class ReportBuildError(RuntimeError):
    """Raised when a cited report cannot be safely assembled or rendered."""


@dataclass(frozen=True, slots=True)
class ReportArtifacts:
    """Paths to the assembled report formats and copied local assets."""

    markdown_path: Path
    html_path: Path
    pdf_path: Path
    figure_paths: tuple[Path, ...]
    audio_path: Path | None
    citations: tuple[str, ...]


def build_report(
    report_markdown: str,
    evidence: Mapping[str, EvidenceItem],
    output_dir: str | Path,
    *,
    diagrams: Sequence[DiagramArtifact | str | Path] = (),
    audio_path: str | Path | None = None,
    basename: str = "report",
) -> ReportArtifacts:
    """Validate report citations, copy local assets, and write Markdown, HTML, and PDF.

    The input draft's citation markers are preserved verbatim. Every cited ID must
    have an `EvidenceItem`, and the references section is derived from that evidence.
    Local source paths are reduced to their final filename in published references.
    """
    if not isinstance(report_markdown, str) or not report_markdown.strip():
        raise ValueError("report_markdown must contain report text")
    if len(report_markdown) > _MAX_REPORT_CHARS:
        raise ValueError(f"report_markdown must be at most {_MAX_REPORT_CHARS} characters")
    if not _REPORT_NAME.fullmatch(basename) or basename in {".", ".."}:
        raise ValueError("basename must use 1-64 letters, digits, dots, underscores, or hyphens")
    if any(key != item.chunk_id for key, item in evidence.items()):
        raise ValueError("evidence mapping keys must match their citation IDs")

    citation_result = validate_citations(report_markdown, evidence)
    if not citation_result.is_valid:
        problems = [
            *(f"unknown citation {item}" for item in citation_result.unknown_ids),
            *(f"malformed marker {item}" for item in citation_result.malformed_markers),
        ]
        raise ReportBuildError("Report citations are invalid: " + "; ".join(problems))

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    copied_figures = _copy_figures(diagrams, destination)
    copied_audio, audio_duration = _copy_audio(audio_path, destination)
    references = [evidence[citation_id] for citation_id in citation_result.cited_ids]
    final_markdown = _compose_markdown(
        report_markdown,
        references,
        copied_figures,
        copied_audio,
        audio_duration,
    )

    markdown_file = destination / f"{basename}.md"
    html_file = destination / f"{basename}.html"
    pdf_file = destination / f"{basename}.pdf"
    title = _report_title(report_markdown)
    rendered_html = _render_html(final_markdown, title, include_audio=copied_audio is not None)
    _write_text_atomically(markdown_file, final_markdown)
    _write_text_atomically(html_file, rendered_html)
    _write_pdf_atomically(pdf_file, final_markdown, title, destination)
    return ReportArtifacts(
        markdown_path=markdown_file,
        html_path=html_file,
        pdf_path=pdf_file,
        figure_paths=tuple(copied_figures),
        audio_path=copied_audio,
        citations=tuple(citation_result.cited_ids),
    )


def _copy_figures(diagrams: Sequence[DiagramArtifact | str | Path], output_dir: Path) -> list[Path]:
    figures: list[Path] = []
    for index, diagram in enumerate(diagrams, start=1):
        if isinstance(diagram, DiagramArtifact):
            svg_text = diagram.svg
        else:
            source_path = Path(diagram)
            try:
                if source_path.stat().st_size > _MAX_SVG_BYTES:
                    raise ReportBuildError(f"Diagram is larger than {_MAX_SVG_BYTES} bytes")
                svg_text = source_path.read_text(encoding="utf-8")
            except OSError as exc:
                raise ReportBuildError(f"Could not read diagram asset {source_path}.") from exc
        svg_text = re.sub(r"<!DOCTYPE[^>]*>", "", svg_text, count=1, flags=re.IGNORECASE)
        _validate_svg(svg_text)
        figure_path = output_dir / "figures" / f"diagram-{index:02d}.svg"
        _write_text_atomically(figure_path, svg_text)
        figures.append(figure_path)
    return figures


def _validate_svg(svg_text: str) -> None:
    if not svg_text or len(svg_text.encode("utf-8")) > _MAX_SVG_BYTES:
        raise ReportBuildError("SVG diagram is empty or exceeds the size limit")
    if "<!ENTITY" in svg_text.upper():
        raise ReportBuildError("SVG entity declarations are not allowed")
    if re.search(r"<\?xml-stylesheet\b", svg_text, re.IGNORECASE):
        raise ReportBuildError("SVG external stylesheets are not allowed")
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as exc:
        raise ReportBuildError("Diagram asset is not valid SVG/XML.") from exc
    if root.tag.rsplit("}", 1)[-1].lower() != "svg":
        raise ReportBuildError("Diagram asset root must be an SVG element")
    for element in root.iter():
        name = element.tag.rsplit("}", 1)[-1]
        if name.lower() in _UNSAFE_SVG_ELEMENTS:
            raise ReportBuildError(f"SVG element {name!r} is not allowed")
        if name.lower() == "style":
            css = "".join(element.itertext())
            if re.search(r"@import\b", css, re.IGNORECASE) or _has_external_url(css):
                raise ReportBuildError("SVG external CSS references are not allowed")
        for raw_name, value in element.attrib.items():
            attribute = raw_name.rsplit("}", 1)[-1].lower()
            normalized = value.strip().lower()
            if attribute.startswith("on"):
                raise ReportBuildError("SVG event-handler attributes are not allowed")
            if attribute in {"href", "src"} and normalized and not normalized.startswith("#"):
                raise ReportBuildError("SVG external references are not allowed")
            if _has_external_url(normalized):
                raise ReportBuildError("SVG external URL references are not allowed")


def _has_external_url(value: str) -> bool:
    return any(
        not match.group(1).strip().startswith("#")
        for match in re.finditer(r"url\(\s*['\"]?([^)'\"]+)", value, re.IGNORECASE)
    )


def _copy_audio(
    audio_path: str | Path | None, output_dir: Path
) -> tuple[Path | None, float | None]:
    if audio_path is None:
        return None, None
    source = Path(audio_path)
    try:
        with wave.open(str(source), "rb") as wav_file:
            frame_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            if frame_rate <= 0 or frame_count <= 0:
                raise ReportBuildError("Narration audio is empty or invalid")
            duration = frame_count / frame_rate
    except (OSError, EOFError, wave.Error) as exc:
        raise ReportBuildError(f"Narration asset {source} is not a valid WAV file.") from exc

    destination = output_dir / "audio" / "narration.wav"
    if source.resolve() != destination.resolve():
        _copy_atomically(source, destination)
    return destination, duration


def _compose_markdown(
    report_markdown: str,
    references: Sequence[EvidenceItem],
    figures: Sequence[Path],
    audio_path: Path | None,
    audio_duration: float | None,
) -> str:
    sections = [report_markdown.strip()]
    if figures:
        sections.extend(["", "## Diagrams", ""])
        sections.extend(
            f"![Diagram {index}](figures/{path.name})"
            for index, path in enumerate(figures, start=1)
        )
    if audio_path is not None and audio_duration is not None:
        seconds = round(audio_duration)
        sections.extend(
            [
                "",
                "## Audio summary",
                "",
                f"[Listen to the {seconds}-second narrated summary](audio/{audio_path.name})",
            ]
        )
    if references:
        sections.extend(["", "## References", ""])
        sections.extend(_reference_markdown(item) for item in references)
    return "\n".join(sections).strip() + "\n"


def _reference_markdown(item: EvidenceItem) -> str:
    citation = item.chunk_id.replace("`", "\\`")
    source_name = Path(item.source).name if item.source_type == "local" else item.source
    detail = f"Citation ID: `{citation}` - Source: {_escape_markdown(source_name)}"
    if item.page is not None:
        detail += f" - Page: {item.page}"
    if item.url is not None:
        safe_url = quote(item.url, safe=":/?#[]@!$&'()*+,;=%")
        detail += f" - URL: <{safe_url}>"
    return f"- {detail}"


def _escape_markdown(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+.!|>])", r"\\\1", value)


def _report_title(report_markdown: str) -> str:
    for line in report_markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip() or "Research report"
    return "Research report"


def _render_html(markdown: str, title: str, *, include_audio: bool) -> str:
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:
        raise ReportBuildError(
            "Markdown rendering dependencies are missing; run `uv sync --locked`."
        ) from exc
    body = MarkdownIt("commonmark", {"html": False, "linkify": False}).render(markdown)
    audio_control = ""
    if include_audio:
        audio_control = (
            '<section class="audio-player" aria-label="Narrated summary">'
            '<audio controls preload="metadata"><source src="audio/narration.wav" '
            'type="audio/wav">Your browser does not support audio playback.</audio>'
            '<p><a href="audio/narration.wav">Download the narration</a></p></section>'
        )
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n<meta name="viewport" '
        'content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n<style>{_REPORT_CSS}</style>\n</head>\n"
        f'<body><main class="report">{body}{audio_control}</main></body>\n</html>\n'
    )


_REPORT_CSS = """
:root { color-scheme: light; font-family: Arial, Helvetica, sans-serif; color: #172033; }
body { margin: 0; background: #f4f6f9; line-height: 1.62; }
.report { max-width: 860px; margin: 32px auto; padding: 48px 58px; background: #fff;
          box-shadow: 0 8px 30px #17203318; }
h1, h2, h3 { color: #183454; line-height: 1.25; }
h1 { font-size: 2.1rem; margin-top: 0; }
h2 { margin-top: 2.2em; border-bottom: 1px solid #d9e1e9; padding-bottom: .35em; }
p, li { font-size: 1rem; }
li { margin: .35em 0; }
img { display: block; max-width: 100%; height: auto; margin: 1.25em auto; }
.audio-player { margin: 1.5em 0; padding: 1em; background: #f1f5f9; border-radius: 8px; }
audio { width: 100%; }
code { color: #155e75; overflow-wrap: anywhere; }
@media print { body { background: #fff; } .report { margin: 0; padding: 1.5cm;
  max-width: none; box-shadow: none; } }
"""


def _write_pdf_atomically(path: Path, markdown: str, title: str, output_dir: Path) -> None:
    try:
        from bs4 import BeautifulSoup, Tag
        from markdown_it import MarkdownIt
        from pypdf import PdfReader
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer
        from svglib.svglib import svg2rlg
    except ImportError as exc:
        raise ReportBuildError(
            "PDF dependencies are missing; run `uv sync --locked` to install ReportLab and svglib."
        ) from exc

    font_name = _register_pdf_font(pdfmetrics, TTFont)
    sample_styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "ARABody",
        parent=sample_styles["BodyText"],
        fontName=font_name,
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#233247"),
        spaceAfter=8,
        splitLongWords=True,
    )
    styles = {
        "h1": ParagraphStyle(
            "ARATitle",
            parent=sample_styles["Title"],
            fontName=font_name,
            fontSize=22,
            leading=27,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#183454"),
            spaceAfter=22,
        ),
        "h2": ParagraphStyle(
            "ARASection",
            parent=sample_styles["Heading2"],
            fontName=font_name,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e4d71"),
            spaceBefore=16,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "ARASubsection",
            parent=sample_styles["Heading3"],
            fontName=font_name,
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#315a79"),
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "body": body_style,
        "caption": ParagraphStyle(
            "ARACaption",
            parent=body_style,
            fontSize=8,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#536579"),
            spaceAfter=12,
        ),
    }
    soup = BeautifulSoup(MarkdownIt("commonmark", {"html": False}).render(markdown), "html.parser")
    story: list[Any] = []
    page_width, page_height = A4
    available_width = page_width - 108
    available_height = page_height - 126
    for element in soup.contents:
        if not isinstance(element, Tag):
            continue
        if element.name in {"h1", "h2", "h3"}:
            text = _pdf_safe_text(element.get_text(" ", strip=True))
            style = styles[element.name]
            story.append(Paragraph(html.escape(text), style))
        elif element.name == "p":
            image = element.find("img")
            if isinstance(image, Tag):
                source = image.get("src")
                alt = _pdf_safe_text(str(image.get("alt", "Diagram")))
                figure_path = _resolve_local_asset(str(source), output_dir)
                try:
                    drawing = svg2rlg(str(figure_path))
                except Exception as exc:
                    raise ReportBuildError(
                        f"Could not render diagram {figure_path} in PDF."
                    ) from exc
                if drawing is None or drawing.width <= 0 or drawing.height <= 0:
                    raise ReportBuildError(f"Diagram {figure_path} has no renderable dimensions.")
                scale = min(available_width / drawing.width, available_height / drawing.height, 1.0)
                drawing.scale(scale, scale)
                drawing.width *= scale
                drawing.height *= scale
                story.extend(
                    [Spacer(1, 8), drawing, Paragraph(html.escape(alt), styles["caption"])]
                )
            else:
                story.append(Paragraph(_pdf_paragraph_text(element), styles["body"]))
        elif element.name in {"ul", "ol"}:
            for index, item in enumerate(element.find_all("li", recursive=False), start=1):
                text = html.escape(_pdf_safe_text(item.get_text(" ", strip=True)))
                bullet = f"{index}." if element.name == "ol" else "-"
                story.append(Paragraph(text, styles["body"], bulletText=bullet))
        elif element.name == "blockquote":
            text = html.escape(_pdf_safe_text(element.get_text(" ", strip=True)))
            quote_style = ParagraphStyle(
                "ARAQuote",
                parent=styles["body"],
                leftIndent=18,
                textColor=colors.HexColor("#536579"),
            )
            story.append(Paragraph(text, quote_style))
        elif element.name == "hr":
            story.extend([Spacer(1, 4), HRFlowable(width="100%", color=colors.HexColor("#cbd5e1"))])

    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.stem}.", suffix=".pdf.tmp", delete=False
        ) as temporary:
            temporary_path = temporary.name
        document = SimpleDocTemplate(
            temporary_path,
            pagesize=A4,
            leftMargin=54,
            rightMargin=54,
            topMargin=52,
            bottomMargin=50,
            title=_pdf_safe_text(title),
            author="ARA Research Agent",
        )
        document.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
        reader = PdfReader(temporary_path)
        if not reader.pages:
            raise ReportBuildError("PDF renderer returned a document without pages")
        os.replace(temporary_path, path)
        temporary_path = None
    except ReportBuildError:
        raise
    except Exception as exc:
        logger.exception("Could not render report PDF at %s", path)
        raise ReportBuildError(f"Could not render report PDF at {path}.") from exc
    finally:
        if temporary_path is not None:
            Path(temporary_path).unlink(missing_ok=True)


def _register_pdf_font(pdfmetrics: Any, font_type: Any) -> str:
    font_name = "ARA-Vera"
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name
    try:
        import reportlab

        font_path = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
        if font_path.is_file():
            pdfmetrics.registerFont(font_type(font_name, str(font_path)))
            return font_name
    except Exception:
        logger.warning("Bundled Vera font unavailable; using built-in Helvetica")
    return "Helvetica"


def _pdf_paragraph_text(element: Any) -> str:
    from bs4 import Tag

    anchor = element.find("a")
    if isinstance(anchor, Tag) and str(anchor.get("href", "")).startswith("audio/"):
        href = html.escape(str(anchor.get("href")), quote=True)
        label = html.escape(_pdf_safe_text(anchor.get_text(" ", strip=True)))
        return f'<link href="{href}" color="#0f766e">{label}</link>'
    return html.escape(_pdf_safe_text(element.get_text(" ", strip=True)))


def _pdf_safe_text(value: str) -> str:
    return value.translate(_PDF_DASHES)


def _resolve_local_asset(relative_path: str, output_dir: Path) -> Path:
    parsed = PurePosixPath(relative_path)
    if parsed.is_absolute() or ".." in parsed.parts:
        raise ReportBuildError("Report asset paths must remain inside the output directory")
    resolved_root = output_dir.resolve()
    resolved_path = (output_dir / Path(*parsed.parts)).resolve()
    if not resolved_path.is_relative_to(resolved_root) or not resolved_path.is_file():
        raise ReportBuildError(
            f"Report references a missing or unsafe local asset: {relative_path}"
        )
    return resolved_path


def _draw_footer(canvas: Any, document: Any) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics

    font_name = "ARA-Vera" if "ARA-Vera" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d4dde6"))
    canvas.line(document.leftMargin, 38, A4[0] - document.rightMargin, 38)
    canvas.setFont(font_name, 8)
    canvas.setFillColor(colors.HexColor("#65758a"))
    canvas.drawString(document.leftMargin, 25, "ARA Research Report")
    canvas.drawRightString(A4[0] - document.rightMargin, 25, f"Page {document.page}")
    canvas.restoreState()


def _write_text_atomically(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary_path = temporary.name
        os.replace(temporary_path, path)
    except OSError as exc:
        raise ReportBuildError(f"Could not write report file {path}.") from exc
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _copy_atomically(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with (
            source.open("rb") as source_file,
            tempfile.NamedTemporaryFile(
                mode="wb", dir=destination.parent, prefix=f".{destination.name}.", delete=False
            ) as temporary,
        ):
            shutil.copyfileobj(source_file, temporary)
            temporary_path = temporary.name
        os.replace(temporary_path, destination)
    except OSError as exc:
        raise ReportBuildError(f"Could not copy report asset from {source}.") from exc
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


__all__ = ["ReportArtifacts", "ReportBuildError", "build_report"]
