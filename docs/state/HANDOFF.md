# HANDOFF (overwritten after every task)

Updated: 2026-10-25 | Session #: 1
Current phase/task: Phase 5 / P5.3 - CPU-feasible reranker model and dataset/dataloader | Status: ready to begin; P5.2 SciFact subset is committed

Last completed task commit: `d5db624` - [P5.2] Add SciFact subset with document-level splits.

## Do next (exact)
1. Inspect `pyproject.toml`, `uv.lock`, and the CPU hardware notes; choose a small CPU PyTorch/Transformers stack and record model/runtime decisions before adding dependencies.
2. Build a typed pair dataset/dataloader that reads the committed train/validation/test SciFact files plus P5.1 pairs without mixing source-document splits; implement a small pretrained cross-encoder with a relevance head and an optional separately supervised credibility head.
3. Add deterministic CPU tests with tiny fixtures and a short training/inference smoke run; verify checkpoint/config handling and rerun pytest, Ruff, mypy, and `git diff --check`.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are installed under ignored `.tools/`; `.venv` and `uv.lock` are present. The dev environment includes pytest 8.4.2, Ruff 0.17.2, mypy 1.20.2, MCP SDK 2.3.0, and ChromaDB 1.5.9. Set `UV_SYSTEM_CERTS=true` for PyPI TLS and `UV_CACHE_DIR=.tools/uv-cache` to avoid the default AppData cache lock error. Public PyPI access works; the user confirmed there is no trusted internal mirror. GNU Make and Ollama are unavailable. Hardware probing found 18 logical processors and 15.52 GiB RAM, but no supported CUDA/MPS adapter; exact display hardware/VRAM is unknown. No models are pulled and no services are running.

## WIP / uncommitted
P5.2 code/data/test is committed as d5db624; P5.2 state updates are included in this handoff commit. P5.1 code/data/test is committed as fa6ba18 with state follow-up dca1157. No source or dataset files are currently uncommitted.

## Known failing tests / issues
No known pytest/Ruff/mypy failures: `.tools/uv/uv.exe run --locked --no-sync pytest` -> 233 passed; Ruff is clean; mypy reports no issues in 46 source files. The P4.5 three-topic reduction is a scripted controlled demonstration only; live-model quality measurement is NOT RUN because Ollama/model weights are unavailable (ENV-002). P5.1 generated and committed 32 extractive/BM25 offline pairs; local-LLM generation and dense mining are NOT RUN. P5.2 generated and committed the checksum-verified SciFact subset (200 claims, 5,183 documents) with document-disjoint internal splits. Planner/researcher/orchestrator/writer/critic/revision-loop tests use mocked LLM behavior; the committed end-to-end sample uses an actual MCP stdio subprocess with synthetic evidence. No live model generation, indexed-corpus search, or external web query has been run. All three ARA MCP servers were started and queried through stdio subprocesses. Claude Desktop itself was not launched, and the DDGS live search request was not smoke-tested. The four retrieval comparisons and live Ollama/Chroma CLI run remain unavailable because Ollama and model weights are absent. Exact GPU/VRAM remains unknown.

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
