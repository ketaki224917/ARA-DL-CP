# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current task: P7.5 — live report with shortened claims and 768-token writer cap | Status: in progress, next action is live rerun
Environment task: ENV-006 — old OneDrive checkout at C: remains blocked by inherited deny-child-delete ACL; D: project/runtime are canonical and usable

Last task commit: `fe93ea3 [P7.5] Shorten report claims for local writer`.

## Do next (exact)
1. Run `D:\msys64\usr\bin\make.exe "TOPIC=Explain reciprocal rank fusion and compare it with score-based fusion." run` from `D:\DL CP` with `D:\DL CP\.tools\uv` on PATH, D: uv cache/Python variables, `UV_SYSTEM_CERTS=true`, and `ARA_LLM_REQUEST_TIMEOUT_SECONDS=300`.
2. Inspect the new trace and `outputs/<run_id>/`; check all citations against evidence and validate Markdown, HTML, PDF, diagram, and WAV artifacts; if generation fails, capture the stage/error and continue with a bounded fix.
3. Run `ara eval --help`, then perform the documented 52-query dense/BM25/hybrid/hybrid+rerank evaluation and expand the held-out ranking failure review to 20 cases if its inputs permit it.

## Environment state
Windows 11, PowerShell, Python 3.12.15, uv 0.13.4, CPU-only, 18 logical processors, 15.52 GiB RAM. Canonical checkout: `D:\DL CP`; current HEAD `fe93ea3`. GNU Make 4.4.1/MSYS2: `D:\msys64`. uv executable/cache/managed Python: `D:\DL CP\.tools\uv`, `.tools\uv-cache`, `.tools\uv-python`; standard `.venv` is on D:. Ollama 0.40.11: `D:\Ollama\app`; models/user data: `D:\Ollama\user-data`; server at `localhost:11434`. Available models: `qwen2.5:1.5b`, `embeddinggemma:latest`. User PATH, Ollama/uv variables, and shortcuts point to D:. C: compatibility junctions for former runtime paths resolve to D:.

## WIP / uncommitted
None. Writer change and state are committed. The latest traces `ba7f2991d03d4a20aa2d4bd74062d81d` (384 tokens, JSON truncation) and `7949dbe60cba4ecd8a4d0dd7afa6be78` (640 tokens, incomplete sentences) are committed as evidence in state.

## Known failing tests / issues
Latest complete checks after writer limit changes: `make test` → 303 passed in 25.30s; `make lint` → all checks passed; `mypy src/ara` → no issues in 55 source files. No known failing tests. RUN-001 remains open: writer 768-token cap with 120-character/14-word claims is not yet live-tested; previous two cap attempts emitted no report artifacts. Four-way RAG evaluation remains NOT RUN; 20-case reranker error analysis remains short of target (four cases in the current 30-query split). ENV-006: old source folder remains in OneDrive C: because inherited `Everyone` deny-child-delete ACE prevents traversal/deletion; no ACL changes were made.

## Gotchas learned
- The existing PowerShell process did not inherit the new D: PATH; invoke `D:\msys64\usr\bin\make.exe` and add `D:\DL CP\.tools\uv` explicitly.
- Restricted shell cache writes under D: sometimes require approved escalation. For pytest, set `TEMP`/`TMP` to `D:\DL CP\.tools\pytest-tmp`; `-p no:cacheprovider` avoids the inaccessible pytest cache without escalation.
- Keep TLS verification enabled and `UV_SYSTEM_CERTS=true` for uv/web calls.
- `make setup` removes QA-only `pypdfium2`; use a separate QA environment for PDF rendering.
- `.tools/p7_5_clone/` is historical P7.4 and lacks ignored model/voice assets; use a fresh clone only after D: is stable.
