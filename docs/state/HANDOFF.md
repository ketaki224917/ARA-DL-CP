# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current task: P7.5 — full live MCP report with split summary schema | Status: ready for rerun
Environment task: ENV-006 — old OneDrive checkout at C: remains blocked by inherited deny-child-delete ACL; D: project/runtime are canonical and usable

Last task commit: `584185d [P7.5] Split summary and section claim bounds`.

## Do next (exact)
1. From `D:\DL CP`, run `D:\msys64\usr\bin\make.exe "TOPIC=Explain reciprocal rank fusion and compare it with score-based fusion." run`, with D: uv/cache/Python paths, `UV_SYSTEM_CERTS=true`, `ARA_LLM_REQUEST_TIMEOUT_SECONDS=300`, and `OLLAMA_MODELS=D:\Ollama\user-data\models`.
2. Inspect `traces/<run_id>.jsonl` and `outputs/<run_id>/`; validate all claim citations against available chunks and inspect Markdown, HTML, PDF, SVG diagram, and WAV narration. Record whether the live bundle passes RUN-001.
3. Implement/run the 52-question dense/BM25/hybrid/RRF+reranker comparison through `src/ara/rag/eval.py`, then pursue the 20-case held-out reranker error review using genuine failures.

## Environment state
Windows 11, PowerShell, Python 3.12.15, uv 0.13.4, CPU-only, 18 logical processors, 15.52 GiB RAM. Canonical checkout: `D:\DL CP`; current HEAD `584185d`. GNU Make 4.4.1/MSYS2: `D:\msys64`. uv executable/cache/managed Python: `D:\DL CP\.tools\uv`, `.tools\uv-cache`, `.tools\uv-python`; `.venv` is on D:. Ollama 0.40.11: `D:\Ollama\app`; models/user data: `D:\Ollama\user-data`; server at `localhost:11434`. Available models: `qwen2.5:1.5b`, `embeddinggemma:latest`. User PATH and Ollama/uv variables and shortcuts point to D:. Former C: runtime paths are compatibility junctions to D:.

## WIP / uncommitted
None. Current writer uses 768 output tokens; four evidence chunks/3,600 characters; section claims max 256 characters/30 words; executive summary max 512 characters/50 words; both schemas require terminal punctuation and evidence IDs from the supplied chunks. A direct Qwen call returned a valid cited five-section report.

## Known failing tests / issues
`make test` → 303 passed in 20.42s; `make lint` → all checks passed; `mypy src/ara` → no issues in 55 source files. No failing tests. RUN-001 remains open: full run `3c2fb03854514cc6bff9ef540a20663e` retrieved five chunks but its summary exceeded the earlier shared claim cap; full pipeline hasn't been rerun with separate summary schema. Four-way RAG evaluation remains NOT RUN. Current SciFact reranker evaluation has four first-rank failures, short of the 20-case review. ENV-006: old C: OneDrive project folder remains due inherited `Everyone` deny-child-delete; no ACL changes made.

## Gotchas learned
- This PowerShell did not inherit the new D: PATH; invoke `D:\msys64\usr\bin\make.exe` and add `D:\DL CP\.tools\uv` explicitly. Set uv cache/Python paths to D:.
- For tests set `TEMP`/`TMP=D:\DL CP\.tools\pytest-tmp`; ordinary sandbox cache writes may need approved escalation.
- Keep TLS verification enabled and `UV_SYSTEM_CERTS=true` for uv/web calls.
- `make setup` removes QA-only `pypdfium2`; use a separate QA environment for PDF rendering.
- `.tools/p7_5_clone/` is historical P7.4 and lacks ignored model/voice assets; use a fresh clone only after D: is stable.
