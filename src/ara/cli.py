"""Command-line entry point for indexing, local MCP servers, and cited reports."""

from __future__ import annotations

import argparse
import asyncio
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
    args, passthrough = parser.parse_known_args(argv)
    if args.command is None:
        parser.print_help()
        return 2

    try:
        if args.command == "eval":
            return _delegate_dl_command("ara.dl.evaluate", passthrough)
        if args.command == "train":
            return _delegate_dl_command("ara.dl.train", passthrough)
        if args.command == "rag-eval":
            if passthrough:
                parser.error(f"unrecognized arguments: {' '.join(passthrough)}")
            from ara.rag.evaluation_runner import run_retrieval_evaluation

            result = run_retrieval_evaluation(
                load_settings(),
                evaluation_path=args.evaluation_set,
                output_dir=args.output_dir,
                candidate_k=args.candidate_k,
                k=args.k,
                resume=not args.fresh,
            )
            logger.info(
                "RAG retrieval evaluation complete: queries=%d resumed=%d table=%s",
                result.total_queries,
                result.resumed_queries,
                result.table_path,
            )
            return 0
        if passthrough:
            parser.error(f"unrecognized arguments: {' '.join(passthrough)}")

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
        if args.command == "serve-mcp":
            return _serve_mcp_server(args.server)
        if args.command == "run":
            report_path = asyncio.run(
                _run_pipeline(
                    args.topic,
                    until=args.until,
                    max_revisions=args.max_revisions,
                    settings=settings,
                )
            )
            if report_path is not None:
                logger.info("Report written to %s", report_path)
            return 0
        parser.error("select an ARA command")
    except Exception:
        logger.exception("ARA %s failed", args.command)
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


async def _run_pipeline(
    topic: str,
    *,
    until: str,
    max_revisions: int,
    settings: Settings,
) -> Path | None:
    """Research through MCP and optionally write a complete local report bundle."""
    from mcp import StdioServerParameters

    from ara.agents.critic import Critic
    from ara.agents.orchestrator import Orchestrator
    from ara.agents.planner import Planner
    from ara.agents.researcher import Researcher
    from ara.agents.revision import RevisionLoop
    from ara.agents.state import AgentState, RunMetadata
    from ara.agents.trace import JSONLTraceWriter
    from ara.agents.writer import Writer
    from ara.generative.diagrams import generate_diagram
    from ara.generative.report_builder import build_report
    from ara.generative.tts import build_narration_script, synthesize_narration
    from ara.llm.client import OllamaClient
    from ara.mcp_client.client import MCPClient

    state = AgentState(
        topic=topic,
        run_metadata=RunMetadata(max_revisions=max_revisions),
    )
    async with MCPClient() as mcp_client:
        await mcp_client.connect(
            "rag",
            StdioServerParameters(
                command=sys.executable, args=["-m", "ara.mcp_servers.rag_server"]
            ),
        )
        await mcp_client.connect(
            "web",
            StdioServerParameters(
                command=sys.executable,
                args=["-m", "ara.mcp_servers.web_search_server"],
            ),
        )
        if settings.dl_use_scorer:
            await mcp_client.connect(
                "dl-model",
                StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "ara.mcp_servers.dl_model_server"],
                ),
            )

        with OllamaClient(settings) as llm:
            orchestrator = Orchestrator(
                Planner(llm),
                Researcher(mcp_client, llm, use_dl_scorer=settings.dl_use_scorer),
                trace_dir=settings.trace_dir,
            )
            await orchestrator.run(state)
            if until == "research":
                logger.info(
                    "Research complete: tasks=%d evidence=%d trace=%s",
                    len(state.plan),
                    len(state.evidence_store),
                    settings.trace_dir / f"{state.run_metadata.run_id}.jsonl",
                )
                return None

            trace_writer = JSONLTraceWriter(state.run_metadata.run_id, settings.trace_dir)
            revision = RevisionLoop(
                Writer(llm, num_predict=settings.llm_writer_num_predict),
                Critic(llm),
                trace_callback=trace_writer.write,
            ).run(state)

            run_output_dir = settings.output_dir / state.run_metadata.run_id
            diagrams = []
            audio_path: Path | None = None
            if not revision.abstained:
                diagram = generate_diagram(revision.final_draft, llm_client=llm)
                diagrams.append(diagram)
                narration = build_narration_script(revision.final_draft, llm_client=llm)
                audio_path = synthesize_narration(
                    narration,
                    run_output_dir / "audio" / "narration.wav",
                    settings=settings,
                ).path

            artifacts = build_report(
                revision.final_draft,
                state.evidence_store,
                run_output_dir,
                diagrams=diagrams,
                audio_path=audio_path,
                basename="report",
            )
            return artifacts.pdf_path


def _serve_mcp_server(server_name: str) -> int:
    """Start one named MCP server over stdio in the current process."""
    if server_name == "rag":
        from ara.mcp_servers.rag_server import main as serve
    elif server_name == "web-search":
        from ara.mcp_servers.web_search_server import main as serve
    elif server_name == "dl-model":
        from ara.mcp_servers.dl_model_server import main as serve
    else:
        raise ValueError(f"unsupported MCP server {server_name!r}")
    serve()
    return 0


def _delegate_dl_command(module_name: str, argv: Sequence[str]) -> int:
    """Pass arguments to the existing custom-model train/evaluation entry point."""
    if module_name == "ara.dl.evaluate":
        from ara.dl.evaluate import main as command_main
    elif module_name == "ara.dl.train":
        from ara.dl.train import main as command_main
    else:
        raise ValueError(f"unsupported delegated command {module_name!r}")
    return command_main(argv)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ara",
        description="Research, retrieve, and build reports from cited evidence.",
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

    serve = commands.add_parser("serve-mcp", help="start one MCP server over stdio")
    serve.add_argument(
        "--server",
        choices=("rag", "web-search", "dl-model"),
        default="rag",
        help="server to start (default: rag)",
    )

    run = commands.add_parser("run", help="research a topic and build a cited report")
    run.add_argument("--topic", required=True, help="research topic")
    run.add_argument(
        "--until",
        choices=("research", "report"),
        default="report",
        help="stop after research or continue through report generation",
    )
    run.add_argument(
        "--max-revisions",
        type=int,
        choices=range(21),
        default=3,
        help="maximum writer revisions (0-20; default: 3)",
    )

    commands.add_parser(
        "eval",
        help="evaluate the custom cross-encoder against retrieval baselines",
        add_help=False,
    )
    rag_eval = commands.add_parser(
        "rag-eval",
        help="compare dense, BM25, hybrid, and hybrid-plus-rerank retrieval",
    )
    rag_eval.add_argument("--evaluation-set", type=Path, default=None)
    rag_eval.add_argument("--output-dir", type=Path, default=None)
    rag_eval.add_argument("--candidate-k", type=int, default=20)
    rag_eval.add_argument("--k", type=int, default=5)
    rag_eval.add_argument(
        "--fresh", action="store_true", help="restart instead of resuming query checkpoints"
    )
    commands.add_parser(
        "train",
        help="train the custom evidence cross-encoder",
        add_help=False,
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
