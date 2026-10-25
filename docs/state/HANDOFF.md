# HANDOFF (overwritten after every task)

Updated: 2026-10-25 | Session #: 1
Current phase/task: Phase 5 / P5.5 - evaluate reranker against baselines | Status: P5.4 complete and committed; training/validation artifacts are recorded

Last completed task commit: `0e89284` - [P5.4] Add deterministic cross-encoder training.

## Do next (exact)
1. Read ADR-031–033 and inspect the held-out files; implement `src/ara/dl/evaluate.py` to score the trained checkpoint, pinned generic checkpoint, and a BM25+dense baseline using only labeled test evidence.
2. Add query-level accuracy/F1/MRR/nDCG metrics, hard-negative ablation, and a 20-case error report with deterministic tests; never use the held-out test data for training or checkpoint selection.
3. Run the comparison on `data/dl_data/scifact_subset`, save a real metrics table and error-analysis artifact under `docs/` or `outputs/`, then rerun pytest, Ruff, mypy, and `git diff --check`.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are under ignored `.tools/`. Use `UV_PROJECT_ENVIRONMENT=.tools/dl-venv`, `UV_SYSTEM_CERTS=true`, and `UV_CACHE_DIR=.tools/uv-cache`; this locked environment has PyTorch `2.14.1+cpu`, Transformers `4.57.6`, Matplotlib `3.11.2`, pytest 8.4.2, Ruff 0.17.2, and mypy 1.20.2. The pinned MiniLM model/tokenizer are cached under ignored `models/huggingface/`. The trained checkpoint currently exists at ignored `models/checkpoints/reranker.pt` but is not committed; regenerate with `python -m ara.dl.train` (three CPU epochs took about 8m35s). Metrics and curve are tracked under `outputs/`. Hugging Face downloads need `import truststore; truststore.inject_into_ssl()` before importing Transformers on this host; TLS verification stays enabled. GNU Make and Ollama are unavailable. Hardware: 18 logical processors, 15.52 GiB RAM, CPU-only; exact display adapter/VRAM unknown. No services are running.

## WIP / uncommitted
P5.4 trainer, tests, metrics, and loss curve are committed as `0e89284`; state updates are the follow-up commit. The local trained weights under `models/checkpoints/` are ignored and can be regenerated from the pinned public checkpoint. P5.3 code is committed as `b63c711`; P5.2 data/code as `d5db624`; P5.1 generator/data as `fa6ba18`. No known source/data WIP remains.

## Known failing tests / issues
No known pytest/Ruff/mypy failures: the full DL-extra suite reports 241 passed; Ruff is clean; mypy reports no issues in 49 source files. P5.4 trained for three CPU epochs; validation BCE reached `0.309428`, but no held-out ranking evaluation or baseline comparison has run yet. P5.1 generation used the extractive/BM25 fallback; local-LLM generation and dense mining are NOT RUN. SciFact has 200 claims and 5,183 documents with document-disjoint splits. The 30-query test partition was not loaded during training and must remain untouched until P5.5. P4.5 is scripted; live LLM research remains unavailable under ENV-002. The saved agent end-to-end example uses synthetic evidence. MCP stdio was verified, but Claude Desktop UI and live DDGS search were not tested. Exact GPU/VRAM remains unknown.

## Gotchas learned
- Use `$env:UV_SYSTEM_CERTS='true'` and `$env:UV_CACHE_DIR='.tools/uv-cache'` before uv commands in this environment.
- GNU Make is absent; invoke the matching uv commands directly.
- Preserve UTF-8 punctuation when editing project state files.
- The SDK's v2 API uses `MCPServer`, `Client(StdioServerParameters(...))`, and `Client(server)` for in-memory protocol tests.
- Web search snippets and fetched page text are untrusted external content; the researcher must keep them in a data-only prompt section.
- The custom scoring server returns `status="not_ready"` until P5.6 loads a trained model; it must not return made-up scores.
- The Claude Desktop JSON sample contains placeholders for the uv executable and ARA project path; replace both before using it.
- `Planner.plan` asks `OllamaClient.structured_output` for strict Pydantic validation, at most three correction retries, and a final JSON repair attempt. The LLM-facing plan schema omits execution status.
- `Researcher.research` expects an open MCP client with servers named `rag` and `web`; calls use `retries=0` so invocation budgets remain exact. Search snippets and retrieved text are untrusted, and full fetched page text is what enters the evidence store.
- `Orchestrator.run` accepts a pending or running `AgentState`, plans only if no plan exists, marks exceptional runs failed, and writes `traces/<run_id>.jsonl`; research completed with blocked tasks is still an orchestrator-completed run, with the blocked tasks visible in state and summary events.
- P3.5 injection fixtures are synthetic. They verify that hostile document/web text is framed as untrusted data and that the researcher rejects unapproved tool names; no live model resistance was tested.
- Run `uv run python scripts/offline_e2e_demo.py` for the local wiring demo; it uses a mocked Ollama response and a synthetic stdio MCP server. The committed `traces/sample_research_run.jsonl` is explicitly a synthetic sample, not a research report.
- `Writer.write` selects at most 20 evidence items and 30,000 text characters by default, renders claim evidence IDs as inline citations, and returns a safe abstention when the model cites an ID outside its selected context.
- `validate_citations` in `ara.agents.citations` parses `[chunk:<id>]` and `[web:<id>]`, reports unique IDs in first-seen order, unknown evidence keys, and malformed citation-prefixed markers; ordinary Markdown brackets are ignored.
- `Critic.review` checks rendered report lines and citation IDs before model review, requires exactly one judgment per reviewable claim, and updates `AgentState.critiques` only after all returned references validate. It reports a deterministic clean result for the writer's exact no-evidence abstention draft.
- `RevisionLoop.run` starts a new cycle only from an `AgentState` with no draft, no critiques, and `revision_count == 0`; it uses `run_metadata.max_revisions` and provides per-iteration counts plus an optional trace callback.
- The loop result is a controlled code-path measurement only when the Writer/Critic LLMs are scripted. It cannot establish a real model quality improvement; record live results only when Ollama and weights are available.
- Use `UV_PROJECT_ENVIRONMENT=.tools/dl-venv` for `--extra dl` commands; syncing the stale `.venv` failed cleanup with Access denied, while the clean dedicated environment worked.
- Import `truststore` and call `truststore.inject_into_ssl()` before Transformers when downloading Hugging Face files on this host. Do not disable TLS verification. The Hugging Face cache falls back to copies because symlinks are unavailable here.
- `build_pair_examples(..., include_synthetic_train=True)` reads configured `Settings.dl_data_path`, now set to `data/dl_data/synthetic_pairs_offline.jsonl` in `config.yaml`.
- `python -m ara.dl.train --max-batches 1 --epochs 1` is a one-batch-per-epoch smoke run; normal training reads train and validation only and saves a best-state checkpoint, JSON history, and PNG curve. The ignored checkpoint is not portable to a fresh checkout, while the pinned base weights and config are.
