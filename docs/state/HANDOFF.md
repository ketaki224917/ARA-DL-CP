# HANDOFF (overwritten after every task)

Updated: 2026-10-25  | Session #: 1
Current phase/task: Phase 5 / P5.6 — load trained scorer in the DL MCP server | Status: P5.5 code/artifacts committed; state update ready to commit

Last completed task commit: `482adf4` — [P5.5] Evaluate reranker on held-out evidence.

## Do next (exact)
1. Inspect `src/ara/mcp_servers/dl_model_server.py`, locate its tests with `rg -n "DLModelService|score_chunks" tests`, and read the vector-store/RAG interfaces that can resolve chunk IDs to text.
2. Implement configurable checkpoint loading and bounded `score_chunks(query, chunk_ids)` inference through the MCP service; retain a typed `not_ready` result when the checkpoint or requested chunks are unavailable.
3. Add deterministic tests with an injected scorer and chunk lookup, then run the full DL-extra pytest suite, Ruff, MyPy, and `git diff --check`.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are under ignored `.tools/`. Use `UV_PROJECT_ENVIRONMENT=.tools/dl-venv`, `UV_SYSTEM_CERTS=true`, and `UV_CACHE_DIR=.tools/uv-cache`; the locked environment has PyTorch `2.14.1+cpu`, Transformers `4.57.6`, Matplotlib `3.11.2`, pytest 8.4.2, Ruff 0.17.2, and MyPy 1.20.2. CPU-only, 18 logical processors, 15.52 GiB RAM; exact display adapter/VRAM unknown. The pinned cross-encoder and dense encoder are cached under ignored `models/huggingface/`. Trained checkpoints are local and ignored at `models/checkpoints/reranker.pt` and `reranker_random_negatives.pt`; regenerate with `python -m ara.dl.train` and the evaluator's default ablation. The P5.5 document embedding cache is at ignored `data/indexes/dl_eval_test_embeddings.pt`. GNU Make and Ollama are unavailable; no services are running.

## WIP / uncommitted
P5.5 source, tests, and evaluation artifacts are committed as `482adf4`; this state update is ready for the required follow-up state commit. Local checkpoints and embedding cache are ignored. The previous task was P5.4 (`0e89284`).

## Known failing tests / issues
No known pytest/Ruff/MyPy failures. Full suite: 246 passed in 69.43s; Ruff clean; MyPy clean for 52 source files. P5.5 evaluated only the 30-query internal SciFact test partition, not the official test set. Candidate recall@20 was 1.0; the fine-tuned model tied RRF recall@10 and slightly improved MRR/nDCG. Four queries had a fine-tuned first-rank error, and all four are reviewed; 20 failures were not present to analyze. Live Ollama reports and real P4.5 model-quality measurement remain unavailable under ENV-002.

## Gotchas learned
- Use `$env:UV_SYSTEM_CERTS='true'` and `$env:UV_CACHE_DIR='.tools/uv-cache'` before uv commands in this environment.
- GNU Make is absent; invoke the matching uv commands directly.
- Import `truststore` and call `truststore.inject_into_ssl()` before Transformers on this host; certificate verification remains enabled. Hugging Face cache uses copies because symlinks are unavailable.
- `python -m ara.dl.evaluate` trains and compares the random-negative control by default; `--no-random-negative-ablation` skips its training.
- The evaluator uses support and contradict evidence as relevant labels and never passes test examples to training or checkpoint selection.
- The DL MCP service remains a typed P2.4 stub returning `not_ready`; P5.6 must add model loading without downloading at import time.
- The checked-in internal SciFact split has 30 test queries and 5,183 corpus documents split without document overlap; do not describe it as the official SciFact test set.
