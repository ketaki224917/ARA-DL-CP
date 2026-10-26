# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current task: ENV-006 — retire the duplicate OneDrive checkout | Status: blocked by inherited deny-child-delete ACL; canonical D: copy is ready
Project task: Phase 7 / P7.5 — live full-report regression | Status: in progress under RUN-001

Last task commit: `a9acee5 [ENV-005] Relocate ARA and add local RAG fallback`.

## Do next (exact)
1. Remove `C:\Users\ketaki more\OneDrive\Documents\DL CP` from OneDrive or resolve its inherited `Everyone` deny-child-delete ACL; the D: copy is clean at `a9acee5`. Confirm the C: path is absent before marking ENV-006 resolved. No ACL changes were made by this session.
2. Continue RUN-001 by reducing writer prompt/output work in `src/ara/agents/writer.py` or config, add a focused test, then run `make test`, `make lint`, and `uv run --locked mypy src/ara`.
3. Rerun the RRF topic with `ARA_LLM_REQUEST_TIMEOUT_SECONDS=300`; inspect every generated MD/HTML/PDF/diagram/audio file and deterministic citation result before changing RUN-001.

## Environment state
Windows 11, PowerShell, Python 3.12.15, uv 0.13.4, CPU-only, 18 logical processors, 15.52 GiB RAM. Canonical checkout: `D:\DL CP`; Git HEAD is `a9acee5`. GNU Make 4.4.1 and MSYS2 are at `D:\msys64`. The uv executable/cache/Python are at `D:\DL CP\.tools\uv`, `.tools\uv-cache`, and `.tools\uv-python`; the standard `.venv` was rebuilt on D:. Ollama 0.40.11 is at `D:\Ollama\app`; models and user data are at `D:\Ollama\user-data`, and the D: server is running at `localhost:11434`. `qwen2.5:1.5b` and `embeddinggemma:latest` are available. User PATH, Ollama/uv variables, and Ollama/MSYS2 shortcuts point to D:. Six C: runtime compatibility junctions resolve to D:. The old project folder itself remains under OneDrive C: due ENV-006.

## WIP / uncommitted
Only the latest state correction for ENV-006 is uncommitted. The D: code and researcher fallback are committed. Runtime migration backup directories on C: are removed; the old OneDrive project folder remains intact because Windows denied access to `.pytest_cache`.

## Known failing tests / issues
`make test` → 299 passed in 30.46s; Ruff passed; MyPy found no issues in 55 source files. `make ingest` loaded 21 sources/documents and 33 chunks, then skipped as current. D: Ollama chat and embedding worked (768 dimensions). The RRF live run added six local chunks, but the writer request timed out after 300 seconds; no complete report bundle was produced. RUN-001 remains open. The four-way RAG evaluation is NOT RUN; the 20-case reranker error analysis remains short of its target.

## Gotchas learned
- Reopen terminals after changing PATH; quote `D:\DL CP` because it contains a space.
- The old OneDrive project has an inherited `Everyone` deny-child-delete ACL; `Get-Acl` on `.pytest_cache` is denied. Do not change permissions without an explicit safe path forward.
- In this sandbox, pytest's default C: temp directory is inaccessible; set the current process `TEMP` and `TMP` to `D:\DL CP\.tools\pytest-tmp` when running tests. The user's general Windows temp variables were not changed.
- `make setup` removes QA-only packages such as `pypdfium2`; use a separate QA environment for PDF rendering.
- Keep TLS verification enabled and use `UV_SYSTEM_CERTS=true` for uv/web calls.
- A historical shared clone `.tools/p7_5_clone/` is at P7.4 and lacks ignored model/voice assets; use a fresh clone only after the D: state is stable.
