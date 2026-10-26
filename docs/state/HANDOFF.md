# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current task: P7.5 — live verification of critic-filter recovery | Status: ready for rerun
Environment task: ENV-006 — old OneDrive checkout at C: remains blocked by inherited deny-child-delete ACL; D: project/runtime are canonical and usable

Last committed task: `55d7904 [P7.5] Fall back to report-structure diagrams`.

## Do next (exact)
1. Run the RRF report topic with `D:\msys64\usr\bin\make.exe "TOPIC=Explain reciprocal rank fusion and compare it with score-based fusion." run`, setting D: uv/cache/Python paths, `UV_SYSTEM_CERTS=true`, `ARA_LLM_REQUEST_TIMEOUT_SECONDS=300`, `OLLAMA_MODELS=D:\Ollama\user-data\models`, and pytest `TEMP`/`TMP` to `D:\DL CP\.tools\pytest-tmp`.
2. Inspect the new JSONL trace and `outputs/<run_id>/`; confirm the critic-filter recovery removed the one flagged claim, re-review reaches zero unsupported claims, and full MD/HTML/PDF, diagram, WAV, and citations are valid.
3. After P7.5, implement a resumable runner for the real 52-question dense/BM25/hybrid/RRF+reranker comparison and expand the held-out DL error review to the required 20 cases if data supports it.

## Environment state
Windows 11, PowerShell, Python 3.12.15, uv 0.13.4, CPU-only, 18 logical processors, 15.52 GiB RAM. Canonical checkout: `D:\DL CP`; committed HEAD `55d7904`. GNU Make 4.4.1/MSYS2: `D:\msys64`. uv executable/cache/managed Python: `D:\DL CP\.tools\uv`, `.tools\uv-cache`, `.tools\uv-python`; `.venv` is on D:. Ollama 0.40.11: `D:\Ollama\app`; models/user data: `D:\Ollama\user-data`; server at `localhost:11434`. Available models: `qwen2.5:1.5b`, `embeddinggemma:latest`.

## WIP / uncommitted
`src/ara/agents/revision.py` and `tests/test_revision.py` add exact critic-filter recovery when a revision writer abstains. Focused revision tests: 11 passed. Full suite: 305 passed in 22.11s; Ruff passes after import sorting; MyPy has no issues in 55 source files. ADR-056 and state updates are uncommitted.

## Known failing tests / issues
Latest full live run `ffb3c61542014d55814699761c1abda8`: research stored five chunks; critic marked four of five initial claims supported, but revision writer abstained. It emitted an abstention MD/HTML/PDF only; no diagram/audio, so RUN-001 remains open. The diagram fallback and critic-filter recovery are unit-tested; neither has been exercised together in a complete live run. Four-way RAG evaluation is NOT RUN. The held-out SciFact split has only four first-rank failures, fewer than the required 20-case error review. ENV-006 remains open because Windows denies deleting the C: OneDrive copy through inherited `Everyone` deny-child-delete; no ACL changes made.

## Gotchas learned
- This PowerShell did not inherit the new D: PATH; invoke `D:\msys64\usr\bin\make.exe` and add `D:\DL CP\.tools\uv` explicitly. Set uv cache/Python paths to D:.
- For tests set `TEMP`/`TMP=D:\DL CP\.tools\pytest-tmp`; sandbox access to the D: uv lock may need approved escalation.
- Keep TLS verification enabled and `UV_SYSTEM_CERTS=true` for uv/web calls.
- `make setup` removes QA-only `pypdfium2`; use a separate QA environment for PDF rendering.
- `.tools/p7_5_clone/` is historical P7.4 and lacks ignored model/voice assets; use a fresh clone only after D: is stable.
