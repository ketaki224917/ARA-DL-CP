# HANDOFF (overwritten after every task)

Updated: 2026-10-24 | Session #: 1
Current phase/task: Phase 4 / P4.4 - revision loop and stopping logic | Status: ready; P4.3 is committed and all local checks pass

Last completed task commit: `a5b081e` - [P4.3] Add structured evidence critic.

## Do next (exact)
1. Inspect `AgentState.increment_revision`, `Writer.write`, `Critic.review`, and their current prompt/state contracts.
2. Add a capped writer/critic loop (default cap from `run_metadata.max_revisions`) that feeds prior critiques to the writer and stops on clean review, abstention, or the revision cap.
3. Record per-iteration reviewed/unsupported/gap/contradiction counts and stopping reason; add deterministic tests for convergence, no-op, errors, and cap behavior; run pytest, Ruff, and mypy, then continue to P4.5.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are installed under ignored `.tools/`; `.venv` and `uv.lock` are present. The dev environment includes pytest 8.4.2, Ruff 0.17.2, mypy 1.20.2, MCP SDK 2.3.0, and ChromaDB 1.5.9. Set `UV_SYSTEM_CERTS=true` for PyPI TLS and `UV_CACHE_DIR=.tools/uv-cache` to avoid the default AppData cache lock error. Public PyPI access works; the user confirmed there is no trusted internal mirror. GNU Make and Ollama are unavailable. Hardware probing found 18 logical processors and 15.52 GiB RAM, but no supported CUDA/MPS adapter; exact display hardware/VRAM is unknown. No models are pulled and no services are running.

## WIP / uncommitted
P4.3 critic implementation is committed as `a5b081e`; P4.2 implementation/state commits are `a127221` and `fe1bf8c`; P4.1 implementation/state commits are `03a58eb` and `c539fa7`. P3.6 code/state commits are `8f13e3b` and `d6b6f25`; P3.5 code/state commits are `edffedc` and `51f3808`; P3.4 code/state commits are `8be34d9` and `3f614b2`; P3.3 code/state commits are `447ed8c` and `6a51fb4`; P3.2 code/state commits are `3997ed9` and `23b664e`; P3.1 code/state commits are `f16cf94` and `8960921`. P2.6 code/state commits are `855317b` and `4fff6ce`; P2.5 code/state commits are `5622d2a` and `6bcbad3`; P2.4 code/state commits are `c822b17` and `5567002`; P2.3 code/state commits are `f260566` and `73ed8d9`. Earlier work includes P0.1 and P0.5-P0.7 through `e705513`, `0e97fd5`, `411fa3f`, and `b2db93c`; P1.1 `50af3fc`; P1.3 `54f0772`; P1.11 `cdcba25` with state follow-up `17b1052`; P2.1 `0bdbaf1` with state follow-up `9bd2e28`; and P2.2 `4526588` with handoff follow-up `a22878b`.

## Known failing tests / issues
No known pytest/Ruff/mypy failures: `.tools/uv/uv.exe run --locked --no-sync pytest` -> 209 passed; Ruff is clean; mypy reports no issues in 42 source files. Planner/researcher/orchestrator/writer/critic tests use mocked LLM behavior; the committed end-to-end sample uses an actual MCP stdio subprocess with synthetic evidence. No live model generation, indexed-corpus search, or external web query has been run. All three ARA MCP servers were started and queried through stdio subprocesses. Claude Desktop itself was not launched, and the DDGS live search request was not smoke-tested. The four retrieval comparisons and live Ollama/Chroma CLI run remain unavailable because Ollama and model weights are absent. Exact GPU/VRAM remains unknown.

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
