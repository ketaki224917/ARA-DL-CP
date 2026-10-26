# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: Phase 7 / P7.1 - CLI and Makefile polish | Status: next

Last completed commits: `4079d02 [P6.3] Build cited report bundles`, `5b80f46 [STATE] Record P6.3 report builder`; P6.4 scope decision is pending commit.

## Do next (exact)
1. Inspect `src/ara/cli.py`, `Makefile`, `README.md`, and current console entry points; compare them with P7.1 commands.
2. Implement missing `setup|ingest|serve|run|eval|train|test` CLI/Makefile coverage with focused tests and document host-specific direct `uv` commands.
3. Run the full suite, Ruff, MyPy, and `git diff --check`; update TODO/PROGRESS/DECISIONS/HANDOFF and commit P7.1.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are under ignored `.tools/`. Use `$env:UV_SYSTEM_CERTS='true'`, `$env:UV_CACHE_DIR='.tools/uv-cache'`, `$env:UV_PROJECT_ENVIRONMENT='.tools/reports-venv'`, and `.tools/uv/uv.exe`. The locked report environment has `dev`, `dl`, and `tts` extras: CPU PyTorch `2.14.1+cpu`, Transformers 4.57.6, Matplotlib 3.11.2, Piper 1.8.0, ReportLab 5.1.0, svglib 2.3.2, and Markdown-it 4.2.0. `pypdfium2 5.14.0` is an ignored QA-only install; Poppler, Node, GNU Make, and Ollama are unavailable. CPU-only, 18 logical processors, 15.52 GiB RAM; exact display adapter/VRAM unknown. Pinned Piper voice and reranker model weights are present under ignored `models/`; configured Ollama chat and embedding models are not pulled. No services are running.

## WIP / uncommitted
P6.3 source is committed as `4079d02`; P6.3 state is committed as `5b80f46`. P6.4 scope decision is updated in state files and pending this task's commit. The ignored cited report bundle is under `outputs/generated/p6_3_demo/`, with a PDFium-rendered QA image at `rendered/page-1.png`.

## Known failing tests / issues
No known pytest, Ruff, or MyPy failures. Latest full suite: 289 passed in 72.30s; Ruff clean; MyPy clean for 59 source files. Live Ollama diagram, narration-script, and report generation remain NOT RUN under ENV-002. P5.5 ranking metrics use a 30-query internal SciFact split; P4.5 live revision-quality measurement remains unrun. Poppler and Node are absent; PDF visual review used PDFium and the PDF-skill marker ran in the available V8 runtime.

## Gotchas learned
- GNU Make is absent; invoke locked `uv` commands directly.
- Hugging Face downloads need `truststore` before Transformers on this host; keep TLS verification enabled. Symlinks are unavailable, so the cache uses copies.
- Recreate the ignored reranker checkpoint/export with `python -m ara.dl.train` and `python -m ara.dl.export`.
- Re-download the ignored Piper model with `python -m ara.generative.tts --download-voice`; reproduce controlled audio with `python scripts/tts_synthesis_smoke.py`.
- `build_narration_script` needs local Ollama; `synthesize_narration` needs the `tts` extra and voice files but no network access. `build_report()` needs locked Markdown-it/ReportLab/svglib dependencies and validates citations before writing.
