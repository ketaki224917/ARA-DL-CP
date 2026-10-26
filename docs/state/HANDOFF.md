# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current task: P7.5 — live writer with 80-character claim schema and 768-token cap | Status: in progress, prior caps failed validation
Environment task: ENV-006 — old OneDrive checkout at C: remains blocked by inherited deny-child-delete ACL; D: project/runtime are canonical and usable

Last task commit: `5b529bc [P7.5] Constrain writer claims for small model`.

## Do next (exact)
1. Run `D:\msys64\usr\bin\make.exe "TOPIC=Explain reciprocal rank fusion and compare it with score-based fusion." run` from `D:\DL CP` with D: uv paths/cache, `UV_SYSTEM_CERTS=true`, and `ARA_LLM_REQUEST_TIMEOUT_SECONDS=300`.
2. Inspect the resulting trace and `outputs/<run_id>/`; verify non-abstained cited Markdown/HTML/PDF, SVG/diagram, WAV, and deterministic citation validation. Capture any validation error and continue with a bounded fix if needed.
3. Inspect `src/ara/rag/eval.py` and `docs/evaluation.md`; run the four systems over all 52 fixed questions with real ranked IDs, document corpus/index/model settings, and record the metrics. Then extend the reranker error analysis to 20 genuine failures if the available held-out split supports it.

## Environment state
Windows 11, PowerShell, Python 3.12.15, uv 0.13.4, CPU-only, 18 logical processors, 15.52 GiB RAM. Canonical checkout: `D:\DL CP`; current HEAD `5b529bc`. GNU Make 4.4.1/MSYS2: `D:\msys64`. uv executable/cache/managed Python: `D:\DL CP\.tools\uv`, `.tools\uv-cache`, `.tools\uv-python`; standard `.venv` is on D:. Ollama 0.40.11: `D:\Ollama\app`; models/user data: `D:\Ollama\user-data`; server at `localhost:11434`. Available models: `qwen2.5:1.5b`, `embeddinggemma:latest`. User PATH and Ollama/uv variables and shortcuts point to D:. C: runtime compatibility junctions resolve to D:.

## WIP / uncommitted
None. Writer limit and all state changes are committed. Latest traces: `ba7f2991d03d4a20aa2d4bd74062d81d` (384, truncation), `7949dbe60cba4ecd8a4d0dd7afa6be78` (640, incomplete), `e51717ee0a864ef695045fac2151705b` (768/120-char, incomplete).

## Known failing tests / issues
`make test` → 303 passed in 24.18s; `make lint` → all checks passed; `mypy src/ara` → no issues in 55 source files. No failing tests. RUN-001 remains open: writer cap 768 with current 80-character/10-word claims not yet live-tested; prior attempts emitted no report artifacts. Four-way RAG evaluation remains NOT RUN. Current SciFact reranker evaluation has only four first-rank failures; required 20-case error analysis is still open. ENV-006: old checkout remains on C: OneDrive due inherited `Everyone` deny-child-delete; no ACL changes made.

## Gotchas learned
- This shell did not inherit the new D: PATH. Invoke `D:\msys64\usr\bin\make.exe`, add `D:\DL CP\.tools\uv`, and set `UV_CACHE_DIR=D:\DL CP\.tools\uv-cache` and `UV_PYTHON_INSTALL_DIR=D:\DL CP\.tools\uv-python`.
- For tests set `TEMP`/`TMP` to `D:\DL CP\.tools\pytest-tmp`; ordinary sandbox calls may not write uv/MyPy caches without approved escalation.
- Keep TLS verification enabled and `UV_SYSTEM_CERTS=true` for uv/web calls.
- `make setup` removes QA-only `pypdfium2`; use a separate QA environment for PDF rendering.
- `.tools/p7_5_clone/` is historical P7.4 and lacks ignored model/voice assets; use a fresh clone only after D: is stable.
