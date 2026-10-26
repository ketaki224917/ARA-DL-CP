# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current task: P7.5 — verify live writer with JSON Schema punctuation pattern | Status: in progress; prior writer caps failed
Environment task: ENV-006 — old OneDrive checkout at C: remains blocked by inherited deny-child-delete ACL; D: project/runtime are canonical and usable

Last task commit: `7005b5a [P7.5] Require sentence punctuation in writer schema`.

## Do next (exact)
1. From `D:\DL CP`, run `D:\msys64\usr\bin\make.exe "TOPIC=Explain reciprocal rank fusion and compare it with score-based fusion." run`, with D: uv/cache/Python, `UV_SYSTEM_CERTS=true`, `ARA_LLM_REQUEST_TIMEOUT_SECONDS=300`, and the D: Ollama model store.
2. Inspect its trace and `outputs/<run_id>/`; verify every citation ID, validate the report, and open/inspect Markdown, HTML, PDF, diagram/SVG, and narration/WAV. If the model still fails, keep validation fail-closed and make a bounded fix based on the trace.
3. Complete the four-system RAG comparison on the checked-in 52 questions using `src/ara/rag/eval.py` metrics; record corpus/index/model metadata. Then extend the reranker error review to 20 genuine cases if the held-out data supports it.

## Environment state
Windows 11, PowerShell, Python 3.12.15, uv 0.13.4, CPU-only, 18 logical processors, 15.52 GiB RAM. Canonical checkout: `D:\DL CP`; current HEAD `7005b5a`. GNU Make 4.4.1/MSYS2: `D:\msys64`. uv executable/cache/managed Python: `D:\DL CP\.tools\uv`, `.tools\uv-cache`, `.tools\uv-python`; `.venv` is on D:. Ollama 0.40.11: `D:\Ollama\app`; models/user data: `D:\Ollama\user-data`; server at `localhost:11434`. Available models: `qwen2.5:1.5b`, `embeddinggemma:latest`. User PATH, Ollama/uv variables, and shortcuts point to D:. Former runtime C: paths are compatibility junctions to D:.

## WIP / uncommitted
None. The writer's 80-character/10-word cap and JSON Schema terminal-punctuation pattern are committed. Latest failed traces: `ba7f2991d03d4a20aa2d4bd74062d81d` (384 tokens); `7949dbe60cba4ecd8a4d0dd7afa6be78` (640); `e51717ee0a864ef695045fac2151705b` (768/120-char).

## Known failing tests / issues
`make test` → 303 passed in 23.59s; `make lint` → all checks passed; `mypy src/ara` → no issues in 55 source files. No failing tests. RUN-001 remains open: the current punctuation-pattern writer has not been run live; previous attempts emitted no report bundle. Four-way RAG evaluation remains NOT RUN. Current SciFact evaluation has four first-rank failures, short of the 20-case review. ENV-006: old C: OneDrive project folder remains due inherited `Everyone` deny-child-delete; no ACL changes made.

## Gotchas learned
- This PowerShell did not inherit the new D: PATH; invoke `D:\msys64\usr\bin\make.exe` and add `D:\DL CP\.tools\uv` explicitly. Set uv cache/Python paths to D:.
- For tests, set `TEMP`/`TMP=D:\DL CP\.tools\pytest-tmp`; cache writes from ordinary sandbox calls may require approved escalation.
- Keep TLS verification enabled and `UV_SYSTEM_CERTS=true` for uv/web calls.
- `make setup` removes QA-only `pypdfium2`; use a separate QA environment for PDF rendering.
- `.tools/p7_5_clone/` is historical P7.4 and lacks ignored model/voice assets; use a fresh clone only after D: is stable.
