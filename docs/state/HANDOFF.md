# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: Phase 6 / P6.1 — diagram generation, rendering, and validation | Status: next

Last completed task commits: P5.8 model card `c55b028`; P5.7 source/demo `ba8a332`; P5.6 source `23a58b3`; P5.5 code/artifacts `482adf4`.

## Do next (exact)
1. Inspect `src/ara/generative/`, `pyproject.toml`, `config.yaml`, and the report schema for existing diagram hooks and renderer dependencies.
2. Check whether Mermaid CLI or Graphviz is installed; choose a reproducible local renderer, log a decision if a nontrivial dependency/API choice is needed, and implement diagram generation with syntax validation and bounded retry.
3. Add focused tests for valid output, invalid syntax/retry, unavailable renderer, and report embedding; run the full suite, Ruff, MyPy, and `git diff --check`, then update and commit state.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are under ignored `.tools/`. Use `UV_PROJECT_ENVIRONMENT=.tools/dl-venv`, `UV_SYSTEM_CERTS=true`, and `UV_CACHE_DIR=.tools/uv-cache`; locked environment has PyTorch `2.14.1+cpu`, Transformers `4.57.6`, Matplotlib 3.11.2, pytest 8.4.2, Ruff 0.17.2, and MyPy 1.20.2. CPU-only, 18 logical processors, 15.52 GiB RAM; exact display adapter/VRAM unknown. Pinned reranker/dense weights are cached under ignored `models/huggingface/`; trained checkpoint and export bundle are ignored under `models/`. GNU Make and Ollama are unavailable; no services are running.

## WIP / uncommitted
P5.8 model card is committed as `c55b028`. State updates for P5.8 are pending commit. No code WIP is known.

## Known failing tests / issues
No known pytest/Ruff/MyPy failures. Latest full suite: 255 passed in 30.74s; Ruff clean; MyPy clean for 54 source files. The P5.5 evaluation covers a 30-query internal SciFact split, not the official test set. Live Ollama reports and real P4.5 model-quality measurement remain unavailable under ENV-002.

## Gotchas learned
- Set `$env:UV_SYSTEM_CERTS='true'` and `$env:UV_CACHE_DIR='.tools/uv-cache'` before uv commands in this environment.
- GNU Make is absent; invoke the matching uv commands directly.
- Import `truststore` and call `truststore.inject_into_ssl()` before Transformers on this host; TLS verification remains enabled. Hugging Face cache uses copies because symlinks are unavailable.
- Recreate the ignored reranker checkpoint with `python -m ara.dl.train`, then recreate the exported scorer with `python -m ara.dl.export`.
- Researcher reranking is controlled by `ARA_DL_USE_SCORER` and defaults off; it requires a connected `dl-model` MCP server and exported bundle.
