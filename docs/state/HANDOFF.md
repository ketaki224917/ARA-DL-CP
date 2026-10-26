# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current task: ENV-005 — finish retiring verified C: copies after the D: state commit | Status: D: project/runtime verified; compatibility junctions are active
Project task: Phase 7 / P7.5 — live full-report regression | Status: in progress under RUN-001

Last task commit: `f7db79a [STATE] Record D drive relocation next steps`.

## Do next (exact)
1. Commit the verified D: researcher fix and state updates: `git status --short`, then commit the intended files from `D:\DL CP`.
2. After the commit, remove only the old `C:\Users\ketaki more\OneDrive\Documents\DL CP` checkout and the exact `.d-move-backup` runtime folders; verify each target path before recursive removal and confirm the C: junctions still point to D:.
3. Resume RUN-001 by reducing writer prompt/output work in `src/ara/agents/writer.py` or config, add a focused test, run `make test`, `make lint`, MyPy, then rerun the RRF report and inspect every output/citation.

## Environment state
Windows 11, PowerShell, Python 3.12.15, uv 0.13.4, CPU-only, 18 logical processors, 15.52 GiB RAM. Canonical checkout: `D:\DL CP`; D: was fixed with about 147.9 GiB free. The uv executable/cache/Python are at `D:\DL CP\.tools\uv`, `.tools\uv-cache`, and `.tools\uv-python`; the rebuilt standard `.venv` is on D:. GNU Make 4.4.1 and MSYS2 are at `D:\msys64`. Ollama 0.40.11 is at `D:\Ollama\app`; models and user data are under `D:\Ollama\user-data`; `OLLAMA_MODELS` is set to its `models` directory. `qwen2.5:1.5b` and `embeddinggemma:latest` are available. User PATH, uv variables, and Ollama/MSYS2 shortcuts point to D:. C: compatibility junctions route old Ollama, MSYS2, and uv paths to D:.

## WIP / uncommitted
The researcher fallback and its regression test, plus ENV-005/P7.5 state updates, are modified in the D: Git working tree. C: migration backups and the former OneDrive checkout are still present pending the state commit. The abstention-only first-run output was removed; traces remain.

## Known failing tests / issues
`make test` → 299 passed in 30.46s; Ruff passed; MyPy found no issues in 55 source files. `make ingest` loaded 21 sources/documents and 33 chunks, then skipped as current. D: Ollama chat and embedding both worked (768 dimensions). The RRF live run added six local chunks, but the writer request timed out after 300 seconds; no complete report bundle was produced. RUN-001 remains open. The four-way RAG evaluation is NOT RUN; the 20-case reranker error analysis remains short of its target.

## Gotchas learned
- Reopen terminals after changing PATH; quote `D:\DL CP` because it contains a space.
- In this sandbox, pytest's default C: temp directory is inaccessible; set the current process `TEMP` and `TMP` to `D:\DL CP\.tools\pytest-tmp` when running tests. The user's general Windows temp variables were not changed.
- `make setup` removes QA-only packages such as `pypdfium2`; use a separate QA environment for PDF rendering.
- Keep TLS verification enabled and use `UV_SYSTEM_CERTS=true` for uv/web calls.
- A historical shared clone `.tools/p7_5_clone/` is at P7.4 and lacks ignored model/voice assets; use a fresh clone only after the current D: commit is stable.
