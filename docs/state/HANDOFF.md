# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: Phase 6 / P6.2 — narration script and local TTS synthesis | Status: next

Last completed task: P6.1 diagram generator source committed as `e6f798d`; state commit is pending.

## Do next (exact)
1. Check whether Piper, Kokoro, Coqui, `espeak`, or other local TTS engines and weights are already available; inspect current Python dependency and model-cache constraints.
2. Choose a reproducible offline TTS adapter or deterministic not-ready behavior, log the choice, and implement a 1–2 minute narration script builder plus audio synthesis with explicit missing-model/runtime errors.
3. Add tests for script length/content, successful synthesis through an injected engine, missing weights/runtime behavior, and output writing; run the full suite, Ruff, MyPy, and `git diff --check`, then update and commit state.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are under ignored `.tools/`. Use `UV_PROJECT_ENVIRONMENT=.tools/dl-venv`, `UV_SYSTEM_CERTS=true`, and `UV_CACHE_DIR=.tools/uv-cache`; locked environment has PyTorch `2.14.1+cpu`, Transformers `4.57.6`, Matplotlib 3.11.2, pytest 8.4.2, Ruff 0.17.2, and MyPy 1.20.2. CPU-only, 18 logical processors, 15.52 GiB RAM; exact display adapter/VRAM unknown. Pinned reranker/dense weights are cached under ignored `models/huggingface/`; trained checkpoint and export bundle are ignored under `models/`. GNU Make and Ollama are unavailable; no services are running. Graphviz `dot`, Mermaid CLI `mmdc`, Node, and npm are absent; diagram rendering currently uses the standard-library SVG fallback.

## WIP / uncommitted
P6.1 implementation files: `src/ara/generative/__init__.py`, `src/ara/generative/diagrams.py`, and `tests/test_diagrams.py` are committed as `e6f798d`. P6.1 state docs are updated and pending the state commit. No other code WIP is known.

## Known failing tests / issues
No known pytest/Ruff/MyPy failures. Latest full suite: 266 passed in 35.52s; Ruff clean; MyPy clean for 56 source files. P6.1 live Ollama generation and a real Graphviz binary were NOT RUN. The P5.5 evaluation covers a 30-query internal SciFact split, not the official test set; live Ollama reports and real P4.5 model-quality measurement remain unavailable under ENV-002.

## Gotchas learned
- Set `$env:UV_SYSTEM_CERTS='true'` and `$env:UV_CACHE_DIR='.tools/uv-cache'` before uv commands in this environment.
- GNU Make is absent; invoke the matching uv commands directly.
- Import `truststore` and call `truststore.inject_into_ssl()` before Transformers on this host; TLS verification remains enabled. Hugging Face cache uses copies because symlinks are unavailable.
- Recreate the ignored reranker checkpoint with `python -m ara.dl.train`, then recreate the exported scorer with `python -m ara.dl.export`.
- Researcher reranking is controlled by `ARA_DL_USE_SCORER` and defaults off; it requires a connected `dl-model` MCP server and exported bundle.
- `generate_diagram` validates only the documented Mermaid subset; unsupported source receives a bounded syntax retry. This host renders through the built-in SVG path.
