# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: Phase 7 / P7.4 - example reports | Status: complete; next is P7.5

Last source commit: `e225232 [P7.4] Add reproducible example report bundles`. State update is being committed separately.

## Do next (exact)
1. Inspect `docs/state/BLOCKERS.md`, `Makefile`, and the host commands with `Get-Command make,ollama -ErrorAction SilentlyContinue` to establish the P7.5 prerequisites.
2. Verify the locked environment and direct CLI entry point with `.tools/uv/uv.exe sync --locked --extra dev --extra dl --extra tts` and `.tools/uv/uv.exe run --locked ara --help`; GNU Make and Ollama were unavailable at the last probe.
3. Run each P7.5 acceptance step that the host supports, record missing prerequisites and actual command output, then continue to the stretch/final checklist without claiming the live report path works.

## Environment state
Windows 11; PowerShell; Python 3.12.15; uv 0.13.4; CPU-only, 18 logical processors, 15.52 GiB RAM; GPU/VRAM details unknown. Workspace-local uv cache and `.tools/reports-venv` are active. Locked `dev`, `dl`, and `tts` extras include CPU PyTorch, Piper 1.8.0, ReportLab 5.1.0, svglib 2.3.2, and Markdown-it 4.2.0. Pinned Piper voice and reranker weights are present under ignored `models/`; configured Ollama chat/embed models are not pulled. Poppler, Node, GNU Make, and Ollama were not found. No services are running.

## WIP / uncommitted
P7.4 code and all three complete report bundles are committed. PDF QA previews remain ignored under `outputs/generated/p7_4_pdf_qa/`. Only the P7.4 state update is pending its state commit; no product-code WIP is expected.

## Known failing tests / issues
No known pytest, Ruff, or MyPy failures. Latest full suite: 295 passed in 62.19s; focused report tests: 12 passed; Ruff clean; MyPy clean for 61 source files. P7.5's requested GNU Make setup/ingest/run sequence and a live Ollama report run remain unverified because those executables/models are unavailable under ENV-002. The four-way 52-question RAG metrics remain NOT RUN. DL results are descriptive metrics from a 30-query internal SciFact split. Claude Desktop UI was not launched.

## Gotchas learned
- Use `.tools/uv/uv.exe`; set `UV_SYSTEM_CERTS=true`, `UV_CACHE_DIR=.tools/uv-cache`, and `UV_PROJECT_ENVIRONMENT=.tools/reports-venv` in PowerShell.
- GNU Make is absent; invoke corresponding uv commands directly where possible.
- The configured `embeddinggemma` model page requires Ollama 0.11.10 or newer.
- Hugging Face downloads need `truststore` before Transformers; keep TLS verification enabled. Symlinks are unavailable, so the cache uses copies.
- Recreate the ignored reranker checkpoint/export with `python -m ara.dl.train` and `python -m ara.dl.export`.
- Re-download the ignored Piper model with `python -m ara.generative.tts --download-voice`; reproduce controlled audio with `python scripts/tts_synthesis_smoke.py`.
- `scripts/generate_example_reports.py` regenerates the checked-in curated report examples from production-chunked sample notes; it does not run Planner/Researcher/Writer or call Ollama. The untrusted-text note yields two chunks at the configured size, and both IDs are cited.
- Poppler is absent; the example PDFs were rendered with the existing ignored QA-only `pypdfium2` install and visually inspected.
