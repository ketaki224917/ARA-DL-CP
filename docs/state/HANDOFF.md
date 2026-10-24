# HANDOFF (overwritten after every task)

Updated: 2026-10-24 | Session #: 1
Current phase/task: Phase 3 / P3.5 - prompt-injection test fixtures | Status: ready; P3.4 orchestration and trace code is committed and all local checks pass

Last completed task commit: `8be34d9` - [P3.4] Add orchestration and JSONL traces.

## Do next (exact)
1. Inspect the planner/researcher prompts and trace plumbing in `src/ara/agents/prompts/`, `researcher.py`, and `trace.py`; review existing MCP fixtures and the prompt-injection requirement in `AGENTS.md`.
2. Add malicious local-document, web-snippet, and fetched-page fixtures under `tests/fixtures/prompt_injection/`, keeping examples short and clearly synthetic.
3. Add tests proving injected text stays data-only in researcher observations and cannot request a disallowed tool or bypass evidence/budget validation; run pytest, Ruff, and mypy, then continue to P3.6.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are installed under ignored `.tools/`; `.venv` and `uv.lock` are present. The dev environment includes pytest 8.4.2, Ruff 0.17.2, mypy 1.20.2, MCP SDK 2.3.0, and ChromaDB 1.5.9. Set `UV_SYSTEM_CERTS=true` for PyPI TLS and `UV_CACHE_DIR=.tools/uv-cache` to avoid the default AppData cache lock error. Public PyPI access works; the user confirmed there is no trusted internal mirror. GNU Make and Ollama are unavailable. Hardware probing found 18 logical processors and 15.52 GiB RAM, but no supported CUDA/MPS adapter; exact display hardware/VRAM is unknown. No models are pulled and no services are running.

## WIP / uncommitted
P3.4 implementation is committed as `8be34d9`; state-file follow-up is pending. P3.3 code/state commits are `447ed8c` and `6a51fb4`; P3.2 code/state commits are `3997ed9` and `23b664e`; P3.1 code/state commits are `f16cf94` and `8960921`. P2.6 code/state commits are `855317b` and `4fff6ce`; P2.5 code/state commits are `5622d2a` and `6bcbad3`; P2.4 code/state commits are `c822b17` and `5567002`; P2.3 code/state commits are `f260566` and `73ed8d9`. Earlier work includes P0.1 and P0.5-P0.7 through `e705513`, `0e97fd5`, `411fa3f`, and `b2db93c`; P1.1 `50af3fc`; P1.3 `54f0772`; P1.11 `cdcba25` with state follow-up `17b1052`; P2.1 `0bdbaf1` with state follow-up `9bd2e28`; and P2.2 `4526588` with handoff follow-up `a22878b`.

## Known failing tests / issues
No known pytest/Ruff/mypy failures: `.tools/uv/uv.exe run --locked --no-sync pytest` -> 173 passed; Ruff is clean; mypy reports no issues in 35 source files. Planner/researcher/orchestrator tests use mocked LLM and MCP behavior; no live model generation, indexed-corpus search, or external web query has been run. All three ARA MCP servers were started and queried through stdio subprocesses. Claude Desktop itself was not launched, and the DDGS live search request was not smoke-tested. The four retrieval comparisons and live Ollama/Chroma CLI run remain unavailable because Ollama and model weights are absent. Exact GPU/VRAM remains unknown.

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
