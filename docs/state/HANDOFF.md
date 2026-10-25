# HANDOFF (overwritten after every task)

Updated: 2026-10-25 | Session #: 1
Current phase/task: Phase 5 / P5.4 - deterministic cross-encoder training | Status: P5.3 complete and committed; training has not started

Last completed task commit: `b63c711` - [P5.3] Add CPU cross-encoder dataset and model.

## Do next (exact)
1. Implement `src/ara/dl/train.py` to seed Python/Torch, load split-specific `PairExample` sets and the pinned tokenizer/model, and train relevance with the existing `CrossEncoderScorer.compute_loss`.
2. Add validated training settings for epochs, learning rate, early-stopping patience, output checkpoint, and curve paths; write tests for deterministic CPU training, validation-based best-checkpoint selection, and loss-curve output.
3. Run a short CPU fit using `data/dl_data/scifact_subset`, then rerun `.tools/uv/uv.exe run --locked --extra dev --extra dl pytest`, Ruff, mypy, and `git diff --check`; record training/validation metrics without claiming a baseline win.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are under ignored `.tools/`. Use `UV_PROJECT_ENVIRONMENT=.tools/dl-venv`, `UV_SYSTEM_CERTS=true`, and `UV_CACHE_DIR=.tools/uv-cache`; this locked environment has PyTorch `2.14.1+cpu`, Transformers `4.57.6`, pytest 8.4.2, Ruff 0.17.2, and mypy 1.20.2. The pinned MiniLM model and tokenizer are cached under ignored `models/huggingface/`; no fine-tuned checkpoint exists yet. Hugging Face download on this host needs `import truststore; truststore.inject_into_ssl()` before importing Transformers, with TLS verification enabled. GNU Make and Ollama are unavailable. Hardware: 18 logical processors, 15.52 GiB RAM, CPU-only inference; exact display adapter/VRAM unknown. No services are running.

## WIP / uncommitted
P5.3 model, pair dataset, config, lock, and tests are committed as `b63c711`; state updates are the follow-up commit. P5.2 code/data is committed as `d5db624`; P5.1 code/data is committed as `fa6ba18`. No known source/data WIP remains.

## Known failing tests / issues
No known pytest/Ruff/mypy failures: the full DL-extra suite reports 240 passed; Ruff is clean; mypy reports no issues in 48 source files. The pinned pretrained checkpoint loaded and CPU inference passed. P5.4 training and P5.5 baseline evaluation have not run yet. P4.5 is a scripted controlled demonstration only; live LLM work remains unavailable under ENV-002. P5.1 data uses the extractive/BM25 fallback; local-LLM generation and dense mining are NOT RUN. SciFact has 200 claims and 5,183 documents with document-disjoint internal splits. Planner/researcher/writer/critic/revision-loop tests use mocked LLM behavior; the saved end-to-end sample uses synthetic evidence. The three MCP servers were verified through stdio, but Claude Desktop UI and live DDGS search were not tested. Retrieval comparisons and local Ollama/Chroma runs remain unavailable. Exact GPU/VRAM remains unknown. The default `dl_data_path` is the configured generation output; pass `data/dl_data/synthetic_pairs_offline.jsonl` explicitly when using the committed offline pair artifact.

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
- `build_pair_examples(..., include_synthetic_train=True)` defaults to configured `Settings.dl_data_path`; the checked-in fallback is `data/dl_data/synthetic_pairs_offline.jsonl`, so pass that path explicitly unless the generator has created the configured output file.
