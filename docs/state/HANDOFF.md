# HANDOFF (overwritten after every task)

Updated: 2026-10-26  | Session #: 1
Current phase/task: Phase 5 / P5.7 — integrate scoring in the researcher | Status: P5.6 source committed; state update ready to commit

Last completed task commits: P5.6 source `23a58b3`; P5.5 implementation `482adf4`; P5.5 state `dfa6b34`. P5.6 state update is ready to commit.

## Do next (exact)
1. Read `src/ara/agents/researcher.py`, `src/ara/mcp_client/client.py`, and the orchestrator wiring; identify how the researcher receives named MCP clients and evidence candidate IDs.
2. Add an opt-in P5.7 path that calls `dl-model.score_chunks` only through the MCP client, validates returned IDs/status, and reorders matching local evidence without dropping provenance; retain current behavior when scoring is disabled or unavailable.
3. Add deterministic A/B tests for scorer-enabled and scorer-disabled research, run the full DL-extra pytest suite, Ruff, MyPy, and `git diff --check`, then record measured results and update this handoff.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are under ignored `.tools/`. Use `UV_PROJECT_ENVIRONMENT=.tools/dl-venv`, `UV_SYSTEM_CERTS=true`, and `UV_CACHE_DIR=.tools/uv-cache`; the locked environment has PyTorch `2.14.1+cpu`, Transformers `4.57.6`, Matplotlib `3.11.2`, pytest 8.4.2, Ruff 0.17.2, and MyPy 1.20.2. CPU-only, 18 logical processors, 15.52 GiB RAM; exact display adapter/VRAM unknown. Pinned cross-encoder/dense weights are cached under ignored `models/huggingface/`. The trained checkpoint is at ignored `models/checkpoints/reranker.pt`; its exported 90,891,152-byte bundle is at ignored `models/exported/reranker.pt`. The test-embedding cache is ignored at `data/indexes/dl_eval_test_embeddings.pt`. GNU Make and Ollama are unavailable; no services are running.

## WIP / uncommitted
P5.6 exporter, MCP service, config, tests, and `.gitignore` are committed as `23a58b3`; P5.6 state files are ready for the required follow-up state commit. Generated model artifacts are ignored. Previous tasks: P5.5 code `482adf4`, state `dfa6b34`.

## Known failing tests / issues
No known pytest/Ruff/MyPy failures. Full suite: 251 passed in 29.76s; Ruff clean; MyPy clean for 53 source files. The real MCP smoke used in-memory chunks and a locally cached checkpoint; it does not yet demonstrate researcher integration or a report-level A/B effect. P5.5 metrics cover only a 30-query internal SciFact split. Live Ollama reports and real P4.5 model-quality measurement remain unavailable under ENV-002.

## Gotchas learned
- Use `$env:UV_SYSTEM_CERTS='true'` and `$env:UV_CACHE_DIR='.tools/uv-cache'` before uv commands in this environment.
- GNU Make is absent; invoke the matching uv commands directly.
- Import `truststore` and call `truststore.inject_into_ssl()` before Transformers on this host; certificate validation stays enabled. Hugging Face cache uses copies because symlinks are unavailable.
- Run `python -m ara.dl.train` then `python -m ara.dl.export` to recreate the ignored local inference bundle; the server returns typed `not_ready` when it is absent.
- The DL MCP tool accepts up to 50 unique chunk IDs, uses configured mini-batches, returns sigmoid probabilities, and returns typed `not_found` for unknown IDs.
- Researcher tools must be called through the named MCP client; P5.7 must not import or invoke the DL service directly.
- The checked-in internal SciFact split has 30 test queries and is not the official SciFact test set.
