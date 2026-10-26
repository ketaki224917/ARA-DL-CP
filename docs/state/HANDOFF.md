# HANDOFF (overwritten after every task)

Updated: 2026-10-26  | Session #: 1
Current phase/task: Phase 5 / P5.8 — write the custom reranker model card | Status: P5.7 source committed; state update ready to commit

Last completed task commits: P5.7 source `ba8a332`; P5.6 source `23a58b3`; P5.5 source `482adf4`, state `dfa6b34`.

## Do next (exact)
1. Read ADR-031–036, `outputs/dl_training_metrics.json`, `outputs/dl_evaluation_metrics.json`, `outputs/dl_error_analysis.json`, and `data/dl_data/SOURCES.md`.
2. Create `docs/model_card.md` covering model/revision, intended use, dataset sources/licenses and document-disjoint splits, training procedure, held-out metrics/baselines, all four observed ranking failures, P5.7 integration demo, and limitations (small internal test split, unjudged negatives, CPU-only, no credibility labels).
3. Verify every reported number against the committed JSON artifacts and `docs/state/PROGRESS.md`; run the full DL-extra suite, Ruff, MyPy, and `git diff --check`, then commit the model card and state updates separately.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are under ignored `.tools/`. Use `UV_PROJECT_ENVIRONMENT=.tools/dl-venv`, `UV_SYSTEM_CERTS=true`, and `UV_CACHE_DIR=.tools/uv-cache`; the locked environment has PyTorch `2.14.1+cpu`, Transformers `4.57.6`, Matplotlib `3.11.2`, pytest 8.4.2, Ruff 0.17.2, and MyPy 1.20.2. CPU-only, 18 logical processors, 15.52 GiB RAM; exact display adapter/VRAM unknown. Pinned cross-encoder/dense weights are cached under ignored `models/huggingface/`. Trained checkpoint is at ignored `models/checkpoints/reranker.pt`; exported 90,891,152-byte bundle is at ignored `models/exported/reranker.pt`. Dense test embedding cache is ignored at `data/indexes/dl_eval_test_embeddings.pt`. GNU Make and Ollama are unavailable; no services are running.

## WIP / uncommitted
P5.7 researcher/config/tests/demo and `outputs/dl_researcher_ab.{json,md}` are committed as `ba8a332`; P5.7 state files are ready for the required follow-up commit. Source A/B used the actual local checkpoint through the MCP SDK on one controlled two-passage fixture. Generated model artifacts are ignored.

## Known failing tests / issues
No known pytest/Ruff/MyPy failures. Full suite: 255 passed in 35.68s; Ruff clean; MyPy clean for 54 source files. The P5.7 A/B is one synthetic fixture and is not a statistical quality evaluation. P5.5 metrics cover only a 30-query internal SciFact split, not the official test set. Live Ollama reports and real P4.5 model-quality measurement remain unavailable under ENV-002.

## Gotchas learned
- Use `$env:UV_SYSTEM_CERTS='true'` and `$env:UV_CACHE_DIR='.tools/uv-cache'` before uv commands in this environment.
- GNU Make is absent; invoke the matching uv commands directly.
- Import `truststore` and call `truststore.inject_into_ssl()` before Transformers on this host; certificate validation stays enabled. Hugging Face cache uses copies because symlinks are unavailable.
- Run `python -m ara.dl.train` then `python -m ara.dl.export` to recreate the ignored local inference bundle; the server returns typed `not_ready` when it is absent.
- Researcher reranking is controlled by `ARA_DL_USE_SCORER` and defaults off; enable only when the caller connects `dl-model` and the exported bundle exists. Scoring is called through MCP and consumes the research tool-call budget.
- The checked-in internal SciFact split has 30 test queries and is not the official SciFact test set.
