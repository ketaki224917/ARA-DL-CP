# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: Phase 7 / P7.6 - optional LoRA stretch | Status: dropped under ADR-044; next is P7.7

Last source commit: `e225232 [P7.4] Add reproducible example report bundles`; last state commit: `d3beada [P7.5] Record fresh-clone regression blocker`. P7.6 state update is pending its state commit.

## Do next (exact)
1. Commit the P7.6 decision and status in `docs/state/DECISIONS.md`, `TODO.md`, `PROGRESS.md`, `SESSIONS.md`, and this handoff.
2. For P7.7, compare each final acceptance item with its recorded command/artifact and add an explicit `[x]` or `[!]` result to `docs/state/PROGRESS.md`.
3. Record the incomplete project status in `docs/state/HANDOFF.md`; ask for the missing Ollama/Make host only after the audit is concrete.

## Environment state
Windows 11; PowerShell; Python 3.12.15; uv 0.13.4; CPU-only, 18 logical processors, 15.52 GiB RAM; GPU/VRAM details unknown. Workspace-local uv cache and `.tools/reports-venv` are active. A fresh clone/venv at `.tools/p7_5_clone/` installed 137 packages from `uv.lock`, and its CLI help succeeded. Pinned Piper voice and reranker weights are present in the main checkout's ignored `models/`, but absent from the fresh clone. Configured Ollama chat/embed models are not pulled, and no service is running. Poppler, Node, GNU Make, and Ollama were not found.

## WIP / uncommitted
P7.4 code and all three complete report bundles are committed. PDF QA previews and the fresh clone/venv remain ignored under `.tools/` and `outputs/generated/`. P7.5 blocker evidence is committed; only the P7.6 state update is pending its state commit. No product-code WIP is expected.

## Known failing tests / issues
No known pytest, Ruff, or MyPy failures. Latest full suite: 295 passed in 62.19s; focused report tests: 12 passed; Ruff clean; MyPy clean for 61 source files. Fresh-clone `uv sync` and `ara --help` passed; direct `ara ingest` and `ara run --topic ... --until research` both failed because the local Ollama endpoint refused connections. P7.5 and the four-way 52-question RAG metrics remain NOT RUN. DL results are descriptive metrics from a 30-query internal SciFact split. Claude Desktop UI was not launched.

## Gotchas learned
- Use `.tools/uv/uv.exe`; set `UV_SYSTEM_CERTS=true`, `UV_CACHE_DIR=.tools/uv-cache`, and `UV_PROJECT_ENVIRONMENT=.tools/reports-venv` in PowerShell. In `.tools/p7_5_clone/`, the uv executable and cache are one parent directory up.
- GNU Make is absent; invoke corresponding uv commands directly where possible, but do not mark the literal `make` acceptance steps passed.
- The configured `embeddinggemma` model page requires Ollama 0.11.10 or newer.
- Hugging Face downloads need `truststore` before Transformers; keep TLS verification enabled. Symlinks are unavailable, so the cache uses copies.
- Recreate the ignored reranker checkpoint/export with `python -m ara.dl.train` and `python -m ara.dl.export`.
- Re-download the ignored Piper model with `python -m ara.generative.tts --download-voice`; reproduce controlled audio with `python scripts/tts_synthesis_smoke.py`.
- `scripts/generate_example_reports.py` regenerates the checked-in curated report examples from production-chunked sample notes; it does not run Planner/Researcher/Writer or call Ollama. The untrusted-text note yields two chunks at the configured size, and both IDs are cited.
- Poppler is absent; the example PDFs were rendered with the existing ignored QA-only `pypdfium2` install and visually inspected.
- A fresh clone does not include ignored model files; download Ollama weights and the pinned Piper voice before claiming the complete output path.
