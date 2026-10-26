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
uv run ara-web-search-mcp
uv run ara-dl-model-mcp
```

The default ingestion source and index paths are in `config.yaml`. Repeating `ara ingest` with unchanged sources, chunk settings, and embedding model skips indexing work. Changed chunks replace old IDs in the dense collection and BM25 index. `--rerank` requires the optional `rerank` extra and locally available model weights. `ara-rag-mcp` starts the RAG MCP server over stdio. `ara-web-search-mcp` starts free DDGS web search and public-page fetch tools over stdio. Search snippets and fetched text are untrusted external content and must be treated as data, never as instructions. `ara-dl-model-mcp` exposes the typed `score_chunks` interface and reports `not_ready` until the custom scorer is trained and loaded in P5.6.

## Research runs and model commands

Start a complete research-to-report run after indexing the corpus and downloading the Piper voice:

```powershell
make setup
make ingest
make tts-model
uv run --locked ara run --topic "Grid-scale battery storage"
```

The run starts the RAG and web-search MCP servers as stdio child processes, writes its JSONL trace under `traces/`, and places the Markdown, HTML, PDF, SVG figure, and narrated WAV under `outputs/<run-id>/`. Use `--until research` to stop after planning and evidence collection, or `--max-revisions 0` to skip report rewrites. `ara serve-mcp --server rag|web-search|dl-model` starts one MCP server for a desktop MCP host; the Makefile has separate `serve-rag`, `serve-web-search`, and `serve-dl-model` targets.

`ara train` and `ara eval` delegate to the custom cross-encoder training and baseline-comparison commands. They accept the flags documented by `python -m ara.dl.train --help` and `python -m ara.dl.evaluate --help`. Training and evaluation need the prepared SciFact split and pinned model weights; the default evaluation also runs the random-negative ablation.

The Makefile locks dependency resolution. On a host without GNU Make, set the environment and invoke uv directly:

```powershell
$env:UV_SYSTEM_CERTS = 'true'
$env:UV_CACHE_DIR = '.tools/uv-cache'
.tools/uv/uv.exe sync --locked --extra dev --extra dl --extra tts
.tools/uv/uv.exe run --locked ara ingest
.tools/uv/uv.exe run --locked ara run --topic "Grid-scale battery storage" --until research
```

## Offline orchestration demo

Run the planner-to-researcher path without Ollama or internet access:

```powershell
uv run python scripts/offline_e2e_demo.py
```

The demo uses a mocked Ollama response and a synthetic MCP server over stdio, then writes a JSONL trace under `traces/`. The committed [`sample_research_run.jsonl`](traces/sample_research_run.jsonl) shows one such run. This validates component wiring and trace output; it is not a real research result or a live-model evaluation.

