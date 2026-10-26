# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: Phase 7 / P7.1 - CLI and Makefile polish | Status: complete

Last source commit: `6b89e02 [P7.1] Polish CLI and Makefile targets`; P7.1 state commit is pending.

## Do next (exact)
1. Review the README and the measured retrieval, DL training/evaluation, revision-loop, MCP, and report artifacts before writing claims or tables.
2. Complete README architecture (Mermaid), usage from setup through report output, real results tables, limitations, and troubleshooting; keep metrics tied to the recorded artifacts.
3. Check links/commands and run the full suite, Ruff, MyPy, and `git diff --check`; update state and commit P7.2.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are under ignored `.tools/`. Use `$env:UV_SYSTEM_CERTS='true'`, `$env:UV_CACHE_DIR='.tools/uv-cache'`, `$env:UV_PROJECT_ENVIRONMENT='.tools/reports-venv'`, and `.tools/uv/uv.exe`. The locked report environment has `dev`, `dl`, and `tts` extras: CPU PyTorch `2.14.1+cpu`, Transformers 4.57.6, Matplotlib 3.11.2, Piper 1.8.0, ReportLab 5.1.0, svglib 2.3.2, and Markdown-it 4.2.0. `pypdfium2 5.14.0` is an ignored QA-only install; Poppler, Node, GNU Make, and Ollama are unavailable. CPU-only, 18 logical processors, 15.52 GiB RAM; exact display adapter/VRAM unknown. Pinned Piper voice and reranker model weights are present under ignored `models/`; configured Ollama chat and embedding models are not pulled. No services are running.

## WIP / uncommitted
P7.1 source is committed as `6b89e02`; its state files are updated and pending the state commit. No source WIP remains. The ignored cited report demo is under `outputs/generated/p6_3_demo/`.

## Known failing tests / issues
No known pytest, Ruff, or MyPy failures. Latest full suite: 293 passed in 62.27s; Ruff clean; MyPy clean for 59 source files. GNU Make is unavailable, so Make targets are not executable on this host. Live Ollama diagram, narration-script, and full topic-run commands remain NOT RUN under ENV-002. P5.5 ranking metrics use a 30-query internal SciFact split; P4.5 live revision-quality measurement remains unrun.

## Gotchas learned
- GNU Make is absent; use `.tools/uv/uv.exe` direct commands from README on this host. Set the workspace-local uv cache and system certificates first.
- Hugging Face downloads need `truststore` before Transformers; keep TLS verification enabled. Symlinks are unavailable, so cache uses copies.
- Recreate the ignored reranker checkpoint/export with `python -m ara.dl.train` and `python -m ara.dl.export`.
- Re-download the ignored Piper model with `python -m ara.generative.tts --download-voice`; reproduce controlled audio with `python scripts/tts_synthesis_smoke.py`.
- Full `ara run` needs Ollama, an indexed corpus or working web search, and the pinned Piper voice; `--until research` skips report generation. `ara eval` needs the SciFact split and cached base weights.
