# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: Phase 7 / P7.5 - fresh-clone regression | Status: blocked on ENV-002; probe recorded

Last source commit: `e225232 [P7.4] Add reproducible example report bundles`; last committed state checkpoint: `c8cbdf7 [STATE] Record P7.4 example report bundles`. P7.5 state update is pending its state commit.

## Do next (exact)
1. Finalize the P7.5 state record (`docs/state/TODO.md`, `BLOCKERS.md`, `ENVIRONMENT.md`, `PROGRESS.md`, and this handoff) and commit the recorded probe.
2. Handle optional P7.6: append a decision explaining whether to defer LoRA on this CPU-only, no-chat-model host; update TODO/progress/handoff and commit.
3. Audit every final checklist item for P7.7, leave all unrun model/evaluation gates explicit, and request the missing Ollama/Make environment only after the audit.

## Environment state
Windows 11; PowerShell; Python 3.12.15; uv 0.13.4; CPU-only, 18 logical processors, 15.52 GiB RAM; GPU/VRAM details unknown. Workspace-local uv cache and `.tools/reports-venv` are active. A fresh clone/venv at `.tools/p7_5_clone/` installed 137 packages from `uv.lock`, and its CLI help succeeded. Pinned Piper voice and reranker weights are present in the main checkout's ignored `models/`, but absent from the fresh clone. Configured Ollama chat/embed models are not pulled, and no service is running. Poppler, Node, GNU Make, and Ollama were not found.

## WIP / uncommitted
P7.4 code and all three complete report bundles are committed. PDF QA previews and the fresh clone/venv remain ignored under `.tools/` and `outputs/generated/`. Only the P7.5 state update is pending its state commit; no product-code WIP is expected.

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
