# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: Phase 7 / P7.2 - README architecture, usage, and measured results | Status: complete

Last source commit: `f9c6a29 [P7.2] Document architecture and measured results`; P7.2 state commit is pending.

## Do next (exact)
1. Review module interfaces and ADRs 013-042 to ground the architecture and trade-off documentation in implemented decisions.
2. Create `docs/architecture.md` and `docs/design_decisions.md` with component/data flow, design rationale, limitations, measured outcomes, and next steps.
3. Cross-check links and all claims against code/state/outputs, run documentation checks plus full suite/Ruff/MyPy, update state, and commit P7.3.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are under ignored `.tools/`. Use `$env:UV_SYSTEM_CERTS='true'`, `$env:UV_CACHE_DIR='.tools/uv-cache'`, `$env:UV_PROJECT_ENVIRONMENT='.tools/reports-venv'`, and `.tools/uv/uv.exe`. The locked report environment has `dev`, `dl`, and `tts` extras: CPU PyTorch `2.14.1+cpu`, Transformers 4.57.6, Matplotlib 3.11.2, Piper 1.8.0, ReportLab 5.1.0, svglib 2.3.2, and Markdown-it 4.2.0. `pypdfium2 5.14.0` is an ignored QA-only install; Poppler, Node, GNU Make, and Ollama are unavailable. CPU-only, 18 logical processors, 15.52 GiB RAM; exact display adapter/VRAM unknown. Pinned Piper voice and reranker model weights are present under ignored `models/`; configured Ollama chat and embedding models are not pulled. No services are running.

## WIP / uncommitted
P7.2 README is committed as `f9c6a29`; state files are updated and pending the state commit. No source WIP remains. The ignored cited report demo is under `outputs/generated/p6_3_demo/`.

## Known failing tests / issues
No known pytest, Ruff, or MyPy failures. Latest full suite: 293 passed in 62.27s; Ruff clean; MyPy clean for 59 source files. GNU Make is unavailable. The four-way 52-question RAG metric comparison and live Ollama report runs remain NOT RUN under ENV-002. DL metrics cover 30 queries from an internal SciFact split and are descriptive. Claude Desktop UI was not launched.

## Gotchas learned
- GNU Make is absent; use `.tools/uv/uv.exe` direct commands from README on this host. Set the workspace-local uv cache and system certificates first.
- The configured `embeddinggemma` model page requires Ollama 0.11.10 or newer.
- Hugging Face downloads need `truststore` before Transformers; keep TLS verification enabled. Symlinks are unavailable, so the cache uses copies.
- Recreate the ignored reranker checkpoint/export with `python -m ara.dl.train` and `python -m ara.dl.export`.
- Re-download the ignored Piper model with `python -m ara.generative.tts --download-voice`; reproduce controlled audio with `python scripts/tts_synthesis_smoke.py`.
- Full `ara run` needs Ollama, an indexed corpus or working web search, and the pinned Piper voice; `--until research` skips report generation. `ara eval` needs the SciFact split and cached base weights.
