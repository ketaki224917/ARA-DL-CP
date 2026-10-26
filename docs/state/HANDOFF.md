# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current task: P7.5 — CPU writer latency optimization complete | Status: verified by software checks; live RUN-001 rerun next
Environment task: ENV-006 — old OneDrive checkout at C: remains blocked by inherited deny-child-delete ACL; D: project/runtime are canonical and usable

Last task commit: `0386bf5 [P7.5] Bound CPU writer context and output`.

## Do next (exact)
1. In PowerShell, set `PATH` to begin with `D:\DL CP\.tools\uv;D:\msys64\usr\bin`, set `UV_CACHE_DIR=D:\DL CP\.tools\uv-cache`, `UV_PYTHON_INSTALL_DIR=D:\DL CP\.tools\uv-python`, `ARA_LLM_REQUEST_TIMEOUT_SECONDS=300`, and `TEMP`/`TMP=D:\DL CP\.tools\pytest-tmp`; run `D:\msys64\usr\bin\make.exe "TOPIC=Explain reciprocal rank fusion and compare it with score-based fusion." run`.
2. Inspect the new `traces/<run_id>.jsonl` and `outputs/<run_id>/`; verify a non-abstained report, citations resolve to stored evidence, and MD/HTML/PDF, diagram, and WAV artifacts all exist and open.
3. Record the live result in `docs/state/PROGRESS.md` and update RUN-001/P7.5 in `docs/state/BLOCKERS.md` and `docs/state/TODO.md`; if it fails, capture the trace/error and continue with the next bounded fix.

## Environment state
Windows 11, PowerShell, Python 3.12.15, uv 0.13.4, CPU-only, 18 logical processors, 15.52 GiB RAM. Canonical checkout: `D:\DL CP`; current HEAD `0386bf5`. GNU Make 4.4.1/MSYS2: `D:\msys64`. uv executable/cache/managed Python: `D:\DL CP\.tools\uv`, `.tools\uv-cache`, `.tools\uv-python`; standard `.venv` is rebuilt on D:. Ollama 0.40.11: `D:\Ollama\app`; models/user data: `D:\Ollama\user-data`; server at `localhost:11434`. Available models: `qwen2.5:1.5b`, `embeddinggemma:latest`. User PATH and Ollama/uv variables and shortcuts point to D:. C: compatibility junctions for former runtime paths resolve to D:.

## WIP / uncommitted
None. Writer optimization and state record are committed. No services besides the existing Ollama server need to be started manually; the CLI spawns MCP servers.

## Known failing tests / issues
`make test` → 302 passed in 25.49s; `make lint` → all checks passed; `mypy src/ara` → no issues in 55 source files. No known failing tests. RUN-001 remains open: prior live run gathered six local chunks but timed out in the writer after 300 seconds, so no complete report bundle has been verified. Four-way RAG evaluation remains NOT RUN; the reranker error analysis still has four cases rather than the target 20. ENV-006: old source folder remains in OneDrive C: because the inherited `Everyone` deny-child-delete ACE prevents traversal/deletion; no ACL changes were made.

## Gotchas learned
- This already-open PowerShell process did not inherit the new D: PATH; invoke `D:\msys64\usr\bin\make.exe` and put `D:\DL CP\.tools\uv` on PATH explicitly.
- In the restricted tool shell, uv/MyPy cache writes under D: were denied unless commands used approved escalation. For pytest, set `TEMP` and `TMP` to `D:\DL CP\.tools\pytest-tmp`; `-p no:cacheprovider` avoids the inaccessible pytest cache when running without escalation.
- Keep TLS verification enabled and use `UV_SYSTEM_CERTS=true` for uv/web calls.
- `make setup` removes QA-only `pypdfium2`; use a separate QA environment for PDF rendering.
- A historical `.tools/p7_5_clone/` is at P7.4 and lacks ignored model/voice assets; only use a fresh clone after the D: state is stable.
