"""Shared retrieval document types that do not depend on parser libraries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoadedDocument:
    """Text and source location extracted from one file or PDF page."""

    source: str
    text: str
    page: int | None = None

