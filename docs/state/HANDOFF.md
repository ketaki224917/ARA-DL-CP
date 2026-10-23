# HANDOFF (overwritten after every task)

Updated: 2026-10-23 | Session #: 1  
Current phase/task: Phase 1 / P1.11 — idempotent ingestion and ask CLI | Status: implementation and dependency-free smoke checks complete; pytest/ruff/mypy and real local service checks blocked by unavailable dependencies/services

Last task commit: `cdcba25` — [P1.11] Add idempotent ingest and ask commands.

## Do next (exact)
1. When official PyPI access is responsive, retry `$env:UV_SYSTEM_CERTS='true'; .tools/uv/uv.exe lock --verbose`; the user confirmed no trusted internal mirror is available.
2. If lock resolution succeeds, run `.tools/uv/uv.exe sync --extra dev`, then `.tools/uv/uv.exe run pytest`, `.tools/uv/uv.exe run ruff check .`, and `.tools/uv/uv.exe run mypy src`; fix findings and update blocked task statuses.
3. Start Phase 2 / P2.1 by adding `src/ara/mcp_servers/common.py` for MCP input validation, errors, and logging, with focused tests.

## Environment state
Windows 10; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are installed under ignored `.tools/`. Python project dependencies, pytest, Ruff, and mypy are not installed because PyPI timed out. `make` and Ollama are unavailable. CPU identifier is Intel64 Family 6 Model 170 Stepping 4 with 18 logical processors; RAM and GPU/VRAM queries were denied by WMI. No models are pulled and no services are running. Git is on `master`; writing `.git` requires approved escalation.

## WIP / uncommitted
P1.11 code, tests, config/docs, and state updates are committed as `cdcba25`: idempotent `ingest_corpus`, Chroma ID/delete methods, BM25 chunk ID listing, `ara ingest`, `ara ask`, and opt-in `--rerank`. Dependency-free smoke checks passed. P0.5-P0.7 implementations/tests and P1.3 embeddings are uncommitted from earlier work and must not be mixed into later tasks. `docs/state/ENVIRONMENT.md` has a separate uncommitted update; review and commit it with its hardware task. P0.2/P0.3/P0.8 and P1.1/P1.2/P1.4-P1.10 have task commits through `ab9e175`; P1.11 is `cdcba25`.

## Known failing tests / issues
No pytest, Ruff, or mypy runs are available yet; their packages are absent and there is no trusted internal mirror. `python -m compileall -q src tests`, TOML parsing, diff whitespace checks, and dependency-free ingestion/Chroma adapter smoke checks passed. The real Ollama/Chroma CLI run and all four retrieval evaluation comparisons remain NOT RUN because Ollama, Chroma packages, and model weights are unavailable. RAM/VRAM remain unknown.

## Gotchas learned
- Use PowerShell commands or install/use a compatible `make` implementation in this Windows environment.
- Preserve the supplied prompt's UTF-8 punctuation by reading text with explicit UTF-8 encoding.
- Retry package resolution only when official PyPI access is responsive; there is no trusted internal mirror.
