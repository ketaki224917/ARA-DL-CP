"""Load supported source files into plain-text documents with provenance."""

from __future__ import annotations

import logging
from pathlib import Path

from bs4 import BeautifulSoup
from docx import Document as WordDocument
from pypdf import PdfReader

from ara.rag.types import LoadedDocument

logger = logging.getLogger(__name__)
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".markdown", ".txt", ".html", ".htm"}


class IngestionError(RuntimeError):
    """Raised when a supported source cannot be read or decoded."""


def load_file(path: Path | str, *, source: str | None = None) -> list[LoadedDocument]:
    """Load one supported file, returning one document per PDF page where applicable.

    Args:
        path: File to load.
        source: Stable source label stored in metadata. Defaults to the given path string.
    """
    file_path = Path(path)
    extension = file_path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise IngestionError(f"Unsupported file type {extension or '<none>'!r}: {file_path}")
    source_name = source or file_path.as_posix()
    try:
        if extension == ".pdf":
            reader = PdfReader(str(file_path))
            documents = [
                LoadedDocument(source=source_name, text=page.extract_text() or "", page=number)
                for number, page in enumerate(reader.pages, start=1)
            ]
        elif extension == ".docx":
            word_doc = WordDocument(str(file_path))
            blocks = [paragraph.text for paragraph in word_doc.paragraphs if paragraph.text.strip()]
            blocks.extend(
                "\t".join(cell.text for cell in row.cells)
                for table in word_doc.tables
                for row in table.rows
            )
            documents = [LoadedDocument(source=source_name, text="\n".join(blocks))]
        else:
            text = file_path.read_text(encoding="utf-8")
            if extension in {".html", ".htm"}:
                text = _html_to_text(text)
            documents = [LoadedDocument(source=source_name, text=text)]
    except Exception as exc:
        logger.exception("Failed to ingest source %s", file_path)
        raise IngestionError(f"Could not read {file_path}: {exc}") from exc
    logger.debug("Loaded %s as %d text document(s)", file_path, len(documents))
    return documents


def load_directory(directory: Path | str) -> list[LoadedDocument]:
    """Load all supported files in a directory tree in deterministic path order."""
    root = Path(directory)
    if not root.is_dir():
        raise IngestionError(f"Input directory does not exist or is not a directory: {root}")
    documents: list[LoadedDocument] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        source = path.relative_to(root).as_posix()
        documents.extend(load_file(path, source=source))
    logger.info("Loaded %d document(s) from %s", len(documents), root)
    return documents


def _html_to_text(html: str) -> str:
    """Remove non-content elements and return readable HTML text."""
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript", "template"]):
        element.decompose()
    return soup.get_text(separator="\n", strip=True)

