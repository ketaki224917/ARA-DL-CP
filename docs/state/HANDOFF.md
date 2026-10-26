# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current task: P7.5 — full live MCP report after direct Qwen writer passed | Status: in progress
Environment task: ENV-006 — old OneDrive checkout at C: remains blocked by inherited deny-child-delete ACL; D: project/runtime are canonical and usable

Last task commit: `a6d6ed0 [P7.5] Keep complete local writer sentences`.

## Do next (exact)
1. Run `D:\msys64\usr\bin\make.exe "TOPIC=Explain reciprocal rank fusion and compare it with score-based fusion." run` from `D:\DL CP` with D: uv/cache/Python variables, `UV_SYSTEM_CERTS=true`, `ARA_LLM_REQUEST_TIMEOUT_SECONDS=300`, and the Ollama model store on D:.
2. Inspect the run trace and `outputs/<run_id>/`; validate every citation and inspect the Markdown, HTML, PDF, SVG diagram, and WAV narration. Record the live result and update RUN-001/P7.5.
3. Build/run the 52-question dense/BM25/hybrid/RRF+reranker comparison using the existing `ara.rag.eval` harness, then work toward 20 genuine held-out reranker errors without substituting synthetic cases.

## Environment state
Windows 11, PowerShell, Python 3.12.15, uv 0.13.4, CPU-only, 18 logical processors, 15.52 GiB RAM. Canonical checkout: `D:\DL CP`; current HEAD `a6d6ed0`. GNU Make 4.4.1/MSYS2: `D:\msys64`. uv executable/cache/managed Python: `D:\DL CP\.tools\uv`, `.tools\uv-cache`, `.tools\uv-python`; `.venv` is on D:. Ollama 0.40.11: `D:\Ollama\app`; models/user data: `D:\Ollama\user-data`; server at `localhost:11434`. Available models: `qwen2.5:1.5b`, `embeddinggemma:latest`. User PATH, Ollama/uv variables, and shortcuts point to D:. Former runtime C: paths are compatibility junctions to D:.

## WIP / uncommitted
None. Latest writer config is 768 output tokens, four evidence items/3,600 characters, 256-character/30-word claims, and a JSON Schema terminal-punctuation pattern. A direct Qwen call on two real corpus chunks returned a valid five-section report with citations in about 20 seconds.

## Known failing tests / issues
`make test` → 303 passed in 27.30s; `make lint` → all checks passed; `mypy src/ara` → no issues in 55 source files. No failing tests. RUN-001 remains open: direct writer validation passed, but the full MCP/critic/diagram/TTS/report CLI run is still needed. Four-way RAG evaluation remains NOT RUN. Current SciFact reranker evaluation has four first-rank failures, short of the 20-case review. ENV-006: old C: OneDrive project folder remains due inherited `Everyone` deny-child-delete; no ACL changes made.

## Gotchas learned
- This PowerShell did not inherit the D: PATH; invoke `D:\msys64\usr\bin\make.exe` and add `D:\DL CP\.tools\uv` explicitly. Set uv cache/Python paths to D:.
- For tests, set `TEMP`/`TMP=D:\DL CP\.tools\pytest-tmp`; ordinary sandbox cache writes may need approved escalation.
- Keep TLS verification enabled and `UV_SYSTEM_CERTS=true` for uv/web calls.
- `make setup` removes QA-only `pypdfium2`; use a separate QA environment for PDF rendering.
- `.tools/p7_5_clone/` is historical P7.4 and lacks ignored model/voice assets; use a fresh clone only after D: is stable.
