"""Consistent application logging setup."""

from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once with a compact, timestamped format."""
    normalized_level = getattr(logging, level.upper(), None)
    if not isinstance(normalized_level, int):
        raise ValueError(f"Unknown logging level: {level}")
    logging.basicConfig(
        level=normalized_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

