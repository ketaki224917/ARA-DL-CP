# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: Phase 7 / P7.3 - architecture and design decision documentation | Status: complete

Last source commit: `8182727 [P7.3] Document architecture and design tradeoffs`; P7.3 state commit is pending.

## Do next (exact)
1. Inspect `data/sample_corpus/03_hybrid_retrieval.md`, `11_chunk_citation_metadata.md`, and `19_untrusted_retrieved_text.md`; compute real chunk IDs using the production chunker and pick three evidence-grounded report topics.
2. Add a reproducible `scripts/generate_example_reports.py` and three complete bundles under `outputs/examples/`, with validated citations, SVG diagrams, and local narration assets.
3. Run the generator and deterministic citation/PDF checks, validate all three bundles, run full tests/Ruff/MyPy/diff checks, update state, and commit P7.4.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are under ignored `.tools/`. Use `$env:UV_SYSTEM_CERTS='true'`, `$env:UV_CACHE_DIR='.tools/uv-cache'`, `$env:UV_PROJECT_ENVIRONMENT='.tools/reports-venv'`, and `.tools/uv/uv.exe`. The locked report environment has `dev`, `dl`, and `tts` extras: CPU PyTorch `2.14.1+cpu`, Transformers 4.57.6, Matplotlib 3.11.2, Piper 1.8.0, ReportLab 5.1.0, svglib 2.3.2, and Markdown-it 4.2.0. `pypdfium2 5.14.0` is an ignored QA-only install; Poppler, Node, GNU Make, and Ollama are unavailable. CPU-only, 18 logical processors, 15.52 GiB RAM; exact display adapter/VRAM unknown. Pinned Piper voice and reranker model weights are present under ignored `models/`; configured Ollama chat and embedding models are not pulled. No services are running.

## WIP / uncommitted
P7.3 source is committed as `8182727`; its state files are updated and pending the state commit. No source WIP remains. The ignored P6.3 demo bundle is under `outputs/generated/p6_3_demo/`.

## Known failing tests / issues
No known pytest, Ruff, or MyPy failures. Latest full suite: 293 passed in 37.84s; Ruff clean; MyPy clean for 59 source files. GNU Make and Ollama are unavailable. The four-way 52-question RAG metric comparison and live topic runs remain NOT RUN under ENV-002. DL metrics cover 30 queries from an internal SciFact split and are descriptive. Claude Desktop UI was not launched.

## Gotchas learned
- GNU Make is absent; use `.tools/uv/uv.exe` direct commands from README. Set the workspace-local uv cache and system certificates first.
- The configured `embeddinggemma` model page requires Ollama 0.11.10 or newer.
- Hugging Face downloads need `truststore` before Transformers; keep TLS verification enabled. Symlinks are unavailable, so the cache uses copies.
- Recreate the ignored reranker checkpoint/export with `python -m ara.dl.train` and `python -m ara.dl.export`.
- Re-download the ignored Piper model with `python -m ara.generative.tts --download-voice`; reproduce controlled audio with `python scripts/tts_synthesis_smoke.py`.
- `build_report()` validates citation IDs against the supplied evidence mapping, but the sample-report generator must also derive IDs from actual source files so the references remain reproducible.
