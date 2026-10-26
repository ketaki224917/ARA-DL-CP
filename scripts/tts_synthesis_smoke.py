"""Reproducibly verify local Piper synthesis with a controlled narration fixture."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from ara.generative.tts import NarrationScript, synthesize_narration
from ara.logging_setup import configure_logging

logger = logging.getLogger(__name__)

_SMOKE_TEXT = (
    "Today we evaluated ARA's experimental local evidence reranker. The model takes a research "
    "query and a candidate passage, then orders passages after BM25 and dense retrieval. It does "
    "not search the corpus, verify claims, or judge whether a source is credible. The scorer is "
    "based on a pinned MiniLM cross encoder and was fine tuned on a small labeled subset of "
    "SciFact, together with mined training examples. Its credibility head is disabled because no "
    "source quality labels were available. In a held out internal split of thirty queries, the "
    "fine tuned model matched the retrieval baseline on recall at ten and showed slightly higher "
    "mean reciprocal rank and normalized discounted cumulative gain. A random negative control "
    "matched the retrieval baseline. These small differences are descriptive and have no "
    "confidence intervals or significance tests. The internal split is not the official SciFact "
    "test set. Four "
    "queries did not rank a gold passage first, although each gold document was present among "
    "candidates. The researcher integration remains optional and falls back when the scorer is "
    "unavailable. Treat scores as uncalibrated ranking values, not probabilities of truth or "
    "credibility."
)


def run(output_path: Path) -> None:
    """Synthesize the fixed model-card narration and log measured WAV metadata."""
    script = NarrationScript(text=_SMOKE_TEXT)
    artifact = synthesize_narration(script, output_path)
    logger.info(
        "Piper smoke: path=%s duration=%.2fs sample_rate=%d channels=%d words=%d bytes=%d",
        artifact.path,
        artifact.duration_seconds,
        artifact.sample_rate,
        artifact.channels,
        artifact.word_count,
        artifact.path.stat().st_size,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run a local voice synthesis smoke test to the requested output path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/generated/p6_2_voice_smoke.wav"),
        help="WAV destination (default: outputs/generated/p6_2_voice_smoke.wav)",
    )
    args = parser.parse_args(argv)
    configure_logging()
    run(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
