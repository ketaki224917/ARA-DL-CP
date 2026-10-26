# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: Phase 6 / P6.3 - cited Markdown/HTML/PDF report builder | Status: complete

Last source commit: `4079d02 [P6.3] Build cited report bundles`; P6.3 state commit is pending.

## Do next (exact)
1. Resolve the optional P6.4 Stable Diffusion stretch task: record a reasoned drop in TODO/DECISIONS/PROGRESS if it is not pursued, then commit that task's state.
2. Inspect the existing CLI, Makefile, and README against P7.1; write down the concrete gaps before editing.
3. Implement and test P7.1 CLI/Makefile polish, update the state files, and commit the task.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are under ignored `.tools/`. Use `$env:UV_SYSTEM_CERTS='true'`, `$env:UV_CACHE_DIR='.tools/uv-cache'`, `$env:UV_PROJECT_ENVIRONMENT='.tools/reports-venv'`, and `.tools/uv/uv.exe`. The report environment has locked `dev`, `dl`, and `tts` extras: PyTorch `2.14.1+cpu`, Transformers 4.57.6, Matplotlib 3.11.2, Piper 1.8.0, ReportLab 5.1.0, svglib 2.3.2, and Markdown-it 4.2.0. `pypdfium2 5.14.0` is an untracked QA-only install in this environment; Poppler, Node, GNU Make, and Ollama are unavailable. CPU-only, 18 logical processors, 15.52 GiB RAM; exact display adapter/VRAM unknown. The pinned Piper voice and reranker model weights are present under ignored `models/`; configured Ollama chat and embedding models are not pulled. No services are running.

## WIP / uncommitted
P6.3 source/test changes are committed as `4079d02`. P6.3 state files are updated but pending their state commit. The ignored demo bundle is under `outputs/generated/p6_3_demo/`; the PDF is one page and has a rendered QA image at `rendered/page-1.png`. No source WIP remains.

## Known failing tests / issues
No known pytest, Ruff, or MyPy failures. Latest full suite: 289 passed in 72.30s; Ruff clean; MyPy clean for 59 source files. Live Ollama report/narration/diagram generation remains NOT RUN under ENV-002. The P5.5 ranking evaluation uses a 30-query internal SciFact split, not the official test partition; P4.5 live revision-quality measurement remains unrun. The project PDF skill's marker script was executed in the available V8 runtime because the host has no `node` executable; PDF visual inspection used PDFium because Poppler is absent.

## Gotchas learned
- GNU Make is absent; invoke locked `uv` commands directly.
- Hugging Face downloads need `truststore` before Transformers on this host; keep TLS verification enabled. Symlinks are unavailable, so the cache uses copies.
- Recreate the ignored reranker checkpoint/export with `python -m ara.dl.train` and `python -m ara.dl.export`.
- Re-download the ignored Piper model with `python -m ara.generative.tts --download-voice`; reproduce controlled audio with `python scripts/tts_synthesis_smoke.py`.
- `build_narration_script` needs local Ollama; `synthesize_narration` needs the `tts` extra and voice files but no network access. `build_report()` needs its locked Markdown-it/ReportLab/svglib dependencies and validates citation IDs before writing.
