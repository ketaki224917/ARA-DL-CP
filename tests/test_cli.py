"""Tests for command parsing and the ingestion command dispatch."""

from dataclasses import dataclass
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


def test_parser_accepts_mcp_run_eval_and_train_commands() -> None:
    serve = cli._build_parser().parse_args(["serve-mcp", "--server", "web-search"])
    run = cli._build_parser().parse_args(
        ["run", "--topic", "grid storage", "--until", "research", "--max-revisions", "2"]
    )
    evaluate, evaluate_args = cli._build_parser().parse_known_args(
        ["eval", "--no-random-negative-ablation"]
    )
    train, train_args = cli._build_parser().parse_known_args(["train", "--epochs", "1"])
    rag_eval = cli._build_parser().parse_args(
        ["rag-eval", "--candidate-k", "24", "--k", "5", "--fresh"]
    )

    assert serve.command == "serve-mcp"
    assert serve.server == "web-search"
    assert run.command == "run"
    assert run.topic == "grid storage"
    assert run.until == "research"
    assert run.max_revisions == 2
    assert evaluate.command == "eval"
    assert evaluate_args == ["--no-random-negative-ablation"]
    assert train.command == "train"
    assert train_args == ["--epochs", "1"]
    assert rag_eval.command == "rag-eval"
    assert rag_eval.candidate_k == 24
    assert rag_eval.k == 5
    assert rag_eval.fresh is True


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


def test_main_delegates_eval_and_train_arguments(monkeypatch) -> None:
    calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr("ara.logging_setup.configure_logging", lambda: None)
    monkeypatch.setattr(
        cli,
        "_delegate_dl_command",
        lambda module, argv: calls.append((module, list(argv))) or 0,
    )

    assert cli.main(["eval", "--no-random-negative-ablation"]) == 0
    assert cli.main(["train", "--epochs", "1"]) == 0
    assert calls == [
        ("ara.dl.evaluate", ["--no-random-negative-ablation"]),
        ("ara.dl.train", ["--epochs", "1"]),
    ]


def test_main_dispatches_rag_evaluation(monkeypatch) -> None:
    settings = Settings(_env_file=None)
    calls: list[tuple[Settings, dict[str, object]]] = []

    @dataclass(frozen=True)
    class Result:
        table_path: Path
        total_queries: int
        resumed_queries: int

    monkeypatch.setattr("ara.logging_setup.configure_logging", lambda: None)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(
        "ara.rag.evaluation_runner.run_retrieval_evaluation",
        lambda received, **kwargs: calls.append((received, kwargs))
        or Result(Path("outputs/rag_eval/metrics.md"), total_queries=52, resumed_queries=0),
    )

    assert (
        cli.main(
            [
                "rag-eval",
                "--candidate-k",
                "24",
                "--k",
                "5",
                "--fresh",
            ]
        )
        == 0
    )
    assert calls == [
        (
            settings,
            {
                "evaluation_path": None,
                "output_dir": None,
                "candidate_k": 24,
                "k": 5,
                "resume": False,
            },
        )
    ]


def test_main_dispatches_selected_mcp_server(monkeypatch) -> None:
    settings = Settings(_env_file=None)
    servers: list[str] = []
    monkeypatch.setattr("ara.logging_setup.configure_logging", lambda: None)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "_serve_mcp_server", lambda server: servers.append(server) or 0)

    assert cli.main(["serve-mcp", "--server", "dl-model"]) == 0
    assert servers == ["dl-model"]


def test_main_dispatches_run_options_to_pipeline(monkeypatch) -> None:
    settings = Settings(_env_file=None)
    calls: list[tuple[str, str, int, Settings]] = []

    async def fake_run(
        topic: str,
        *,
        until: str,
        max_revisions: int,
        settings: Settings,
    ) -> Path:
        calls.append((topic, until, max_revisions, settings))
        return Path("outputs/run/report.pdf")

    monkeypatch.setattr("ara.logging_setup.configure_logging", lambda: None)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "_run_pipeline", fake_run)

    assert (
        cli.main(["run", "--topic", "grid storage", "--until", "research", "--max-revisions", "1"])
        == 0
    )
    assert calls == [("grid storage", "research", 1, settings)]
