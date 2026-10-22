"""Tests for command parsing and the ingestion command dispatch."""

from pathlib import Path

from ara import cli
from ara.config import Settings
from ara.rag.indexing import IngestionSummary


def test_parser_accepts_ingest_source_and_ask_limits() -> None:
    ingest = cli._build_parser().parse_args(["ingest", "--source", "private_docs"])
    ask = cli._build_parser().parse_args(
        ["ask", "compare", "retrievers", "--top-k", "5", "--candidate-k", "24"]
    )

    assert ingest.command == "ingest"
    assert ingest.source == Path("private_docs")
    assert ask.command == "ask"
    assert ask.query == ["compare", "retrievers"]
    assert ask.top_k == 5
    assert ask.candidate_k == 24
    assert ask.rerank is False

    reranked_ask = cli._build_parser().parse_args(["ask", "question", "--rerank"])
    assert reranked_ask.rerank is True


def test_main_dispatches_ingest_with_loaded_settings(monkeypatch) -> None:
    settings = Settings(_env_file=None)
    calls: list[tuple[Path | None, Settings]] = []

    def fake_ingest(source: Path | None, *, settings: Settings) -> IngestionSummary:
        calls.append((source, settings))
        return IngestionSummary(1, 1, 1, 1, 0, 0, False)

    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "ingest_corpus", fake_ingest)
    monkeypatch.setattr("ara.logging_setup.configure_logging", lambda: None)

    assert cli.main(["ingest", "--source", "private_docs"]) == 0
    assert calls == [(Path("private_docs"), settings)]


def test_main_without_subcommand_shows_help(monkeypatch, capsys) -> None:
    monkeypatch.setattr("ara.logging_setup.configure_logging", lambda: None)

    assert cli.main([]) == 2
    assert "usage: ara" in capsys.readouterr().out
