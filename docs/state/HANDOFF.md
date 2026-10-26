# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current task: P7.5 — verify bounded researcher fallback in full report run | Status: ready for rerun
Environment task: ENV-006 — old OneDrive checkout at C: remains blocked by inherited deny-child-delete ACL; D: project/runtime are canonical and usable

Last committed task: `1e9956f [STATE] Refresh handoff for report rerun`; researcher fallback and ADR-057/state updates are pending commit.

## Do next (exact)
1. Commit the researcher fallback after checking the diff; tests/Ruff/MyPy currently pass.
2. Rerun `D:\msys64\usr\bin\make.exe "TOPIC=Explain reciprocal rank fusion and compare it with score-based fusion." run` from `D:\DL CP`, with D: uv/cache/Python paths, `UV_SYSTEM_CERTS=true`, `ARA_LLM_REQUEST_TIMEOUT_SECONDS=300`, and `OLLAMA_MODELS=D:\Ollama\user-data\models`.
3. Inspect the new trace and output directory; verify revision recovery, citations, MD/HTML/PDF, SVG diagram, and WAV. RUN-001 remains open until a substantive complete bundle passes.

## Environment state
Windows 11, PowerShell, Python 3.12.15, uv 0.13.4, CPU-only, 18 logical processors, 15.52 GiB RAM. Canonical checkout: `D:\DL CP`; committed HEAD `1e9956f`. GNU Make 4.4.1/MSYS2: `D:\msys64`. uv executable/cache/managed Python: `D:\DL CP\.tools\uv`, `.tools\uv-cache`, `.tools\uv-python`; `.venv` is on D:. Ollama 0.40.11: `D:\Ollama\app`; models/user data: `D:\Ollama\user-data`; server at `localhost:11434`. Available models: `qwen2.5:1.5b`, `embeddinggemma:latest`; the chat model unloaded after the latest failed run.

## WIP / uncommitted
`src/ara/agents/researcher.py` and `tests/test_researcher.py` avoid another model-selection request when a web search adds no evidence and earlier tasks already collected evidence. The fallback is traced, uses the RAG MCP server, and completes the task. Full suite: 306 passed in 21.07s; Ruff passes; MyPy has no issues in 55 source files. ADR-057 and state updates are pending commit.

## Known failing tests / issues
Latest full live run `084e0be2b2a049e1998725436a71eaa7`: five local chunks were retrieved, then the task-3 tool-selection request timed out before drafting. Ollama was at 100% CPU; `load_settings()` confirmed the configured 300-second timeout, though the process elapsed much longer before the HTTP timeout surfaced. Prior run `ffb3c61542014d55814699761c1abda8` had four of five claims supported but the revision writer abstained. Critic-filter recovery and Mermaid fallback are implemented and unit-tested, not yet live-verified. Four-way RAG evaluation remains NOT RUN; the DL test split has four first-rank errors, fewer than the 20-case review requirement. ENV-006 remains open due the inherited C: OneDrive deny-child-delete ACL; no permissions changed.

## Gotchas learned
- This PowerShell did not inherit the new D: PATH; invoke `D:\msys64\usr\bin\make.exe` and add `D:\DL CP\.tools\uv` explicitly. Set uv cache/Python paths to D:.
- For tests set `TEMP`/`TMP=D:\DL CP\.tools\pytest-tmp`; sandbox access to the D: uv lock may need approved escalation.
- Keep TLS verification enabled and `UV_SYSTEM_CERTS=true` for uv/web calls.
- `make setup` removes QA-only `pypdfium2`; use a separate QA environment for PDF rendering.
- `.tools/p7_5_clone/` is historical P7.4 and lacks ignored model/voice assets; use a fresh clone only after D: is stable.
