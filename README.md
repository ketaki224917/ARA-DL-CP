# ARA — Autonomous Research & Report Agent

ARA is a local-first research assistant that builds reports from retrieved evidence and attaches chunk-level citations to factual claims. The implementation is being built in phases; current scope and resume instructions are tracked in [`docs/state/HANDOFF.md`](docs/state/HANDOFF.md).

## Development

Python 3.11+ and `uv` are required. Once dependencies are locked, use `make setup` to create the environment and `make test` to run the test suite.

See [`AGENTS.md`](AGENTS.md) for the project specification and [`docs/state/TODO.md`](docs/state/TODO.md) for implementation status.

## Local retrieval commands

After installing the project dependencies and starting Ollama with the configured chat and embedding models:

```powershell
uv run ara ingest
uv run ara ingest --source path\to\your\documents
uv run ara ask "How does reciprocal rank fusion combine results?"
uv run ara ask "How does reciprocal rank fusion combine results?" --rerank
uv run ara-rag-mcp
```

The default ingestion source and index paths are in `config.yaml`. Repeating `ara ingest` with unchanged sources, chunk settings, and embedding model skips indexing work. Changed chunks replace old IDs in the dense collection and BM25 index. `--rerank` requires the optional `rerank` extra and locally available model weights. `ara-rag-mcp` starts the RAG MCP server over stdio.

