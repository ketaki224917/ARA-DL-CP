# HANDOFF (overwritten after every task)

Updated: 2026-10-23 | Session #: 1  
Current phase/task: Phase 2 / P2.5 - MCP client wrapper | Status: ready; P2.3 web search and P2.4 typed DL model servers are committed and pass the full suite

Last completed task commit: `c822b17` - [P2.4] Add typed DL model MCP stub.

## Do next (exact)
1. Implement `src/ara/mcp_client/client.py` to spawn stdio MCP servers, list tools, call tools, and handle bounded timeouts/retries.
2. Add client tests with local MCP servers, including process cleanup, tool listing/calls, timeout, and retry/error behavior; run the full checks.
3. Implement P2.6 with a Claude Desktop sample config and a manual stdio verification note, then continue to Phase 3 / P3.1.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are installed under ignored `.tools/`; `.venv` and `uv.lock` are present. The lock resolves 156 packages, including DDGS 9.16.0; the dev environment includes pytest 8.4.2, Ruff 0.17.2, mypy 1.20.2, MCP SDK 2.3.0, and ChromaDB 1.5.9. Set `UV_SYSTEM_CERTS=true` for PyPI TLS and `UV_CACHE_DIR=.tools/uv-cache` to avoid the default AppData cache lock error. Public PyPI access works; the user confirmed there is no trusted internal mirror. GNU Make and Ollama are unavailable. Hardware probing found 18 logical processors and 15.52 GiB RAM, but no supported CUDA/MPS adapter; exact display hardware/VRAM is unknown. No models are pulled and no services are running.

## WIP / uncommitted
The P2.4 code commit is `c822b17`; the state-file follow-up commit is pending. P2.3 code/state commits are `f260566` and `73ed8d9`. Earlier work includes P0.1 and P0.5-P0.7 through `e705513`, `0e97fd5`, `411fa3f`, and `b2db93c`; P1.1 `50af3fc`; P1.3 `54f0772`; P1.11 `cdcba25` with state follow-up `17b1052`; P2.1 `0bdbaf1` with state follow-up `9bd2e28`; and P2.2 `4526588` with handoff follow-up `a22878b`.

## Known failing tests / issues
No known pytest/Ruff/mypy failures: `.tools/uv/uv.exe run --locked --no-sync pytest` -> 118 passed; Ruff is clean; mypy reports no issues in 24 source files. A live DDGS search request and the real stdio/Claude Desktop check were not run. The four retrieval comparisons and live Ollama/Chroma CLI run remain unavailable because Ollama and model weights are absent. Exact GPU/VRAM remains unknown.

## Gotchas learned
- Use `$env:UV_SYSTEM_CERTS='true'` and `$env:UV_CACHE_DIR='.tools/uv-cache'` before uv commands in this environment.
- GNU Make is absent; invoke the matching uv commands directly.
- Preserve UTF-8 punctuation when editing project state files.
- The SDK's v2 API uses `MCPServer` and supports `Client(server)` for in-memory protocol tests.
- Web search snippets and fetched page text are untrusted external content; the researcher must keep them in a data-only prompt section.
- The custom scoring server returns `status="not_ready"` until P5.6 loads a trained model; it must not return made-up scores.
