"""Command-line entry point for ARA ingestion and evidence-grounded questions."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from ara.config import Settings, load_settings
from ara.rag.indexing import ingest_corpus

logger = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Run an ARA command and return its process exit code."""
    from ara.logging_setup import configure_logging

    configure_logging()
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    try:
        settings = load_settings()
        if args.command == "ingest":
            summary = ingest_corpus(args.source, settings=settings)
            logger.info(
                "Ingested %d sources, %d documents, %d chunks "
                "(added=%d updated=%d removed=%d skipped=%s)",
                summary.source_count,
                summary.document_count,
                summary.chunk_count,
                summary.added_count,
                summary.updated_count,
                summary.removed_count,
                summary.skipped,
            )
            return 0
        if args.command == "ask":
            return _ask(
                " ".join(args.query),
                settings,
                args.top_k,
                args.candidate_k,
                args.rerank,
            )
        parser.error("select an ingest or ask command")
    except Exception as exc:
        logger.error("ARA %s failed: %s", args.command, exc)
        return 1


def _ask(
    query: str,
    settings: Settings,
    top_k: int | None,
    candidate_k: int,
    use_reranker: bool,
) -> int:
    """Run hybrid retrieval, then answer from validated retrieved chunks."""
    from ara.llm.client import OllamaClient
    from ara.rag.answer import EvidenceAnswerer
    from ara.rag.bm25 import BM25Index
    from ara.rag.embeddings import OllamaEmbeddings
    from ara.rag.retriever import HybridRetriever
    from ara.rag.vectorstore import ChromaVectorStore

    result_limit = settings.retrieval_top_k if top_k is None else top_k
    if result_limit < 1:
        raise ValueError("top_k must be at least 1")
    if candidate_k < 1:
        raise ValueError("candidate_k must be at least 1")
    candidate_limit = max(candidate_k, result_limit)
    lexical = BM25Index.load(settings.bm25_index_path)
    vector_store = ChromaVectorStore(settings.vector_store_dir)
    with OllamaEmbeddings(settings) as embedder:
        retriever = HybridRetriever(vector_store, lexical, embedder)
        candidates = retriever.search(
            query,
            top_k=candidate_limit,
            candidate_k=candidate_limit,
        )
    if use_reranker and candidates:
        from ara.rag.reranker import CrossEncoderReranker

        reranked = CrossEncoderReranker(settings.reranker_model).rerank(
            query,
            candidates,
            top_k=result_limit,
        )
        candidates_by_id = {item.chunk.chunk_id: item for item in candidates}
        candidates = [candidates_by_id[item.chunk.chunk_id] for item in reranked]
    else:
        candidates = candidates[:result_limit]
    with OllamaClient(settings) as llm:
        answer = EvidenceAnswerer(llm, settings=settings).answer(query, candidates)
    if answer.abstained:
        logger.info("Abstained: %s", answer.reason)
    sys.stdout.write(answer.text + "\n")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ara",
        description="Research answers grounded in local sources.",
    )
    commands = parser.add_subparsers(dest="command")

    ingest = commands.add_parser("ingest", help="build or update the local retrieval indexes")
    ingest.add_argument(
        "--source",
        type=Path,
        default=None,
        help="source folder (defaults to config)",
    )

    ask = commands.add_parser("ask", help="answer a question from the indexed corpus")
    ask.add_argument("query", nargs="+", help="research question")
    ask.add_argument("--top-k", type=int, default=None, help="number of fused results to use")
    ask.add_argument(
        "--candidate-k",
        type=int,
        default=32,
        help="candidate count requested from each retrieval index",
    )
    ask.add_argument(
        "--rerank",
        action="store_true",
        help="use the optional local cross-encoder reranker",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())

