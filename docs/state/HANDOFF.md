# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current task: user-requested relocation of ARA, Ollama, model data, and project tools to D: | Status: in progress
Project task: Phase 7 / P7.5 - live full-report regression | Status: in progress under RUN-001

Last task commit: `2098962 [P7.5] Bound CPU writer output and citations`.

## Do next (exact)
1. Inspect destination and reparse-point layout before copying: verify `D:\DL CP` does not already contain user files, check `D:` free space, and inventory `C:\msys64`, the Ollama install/data folders, and any project junctions.
2. Copy the entire checkout, including `.git`, `.tools`, ignored model weights, and outputs, to `D:\DL CP`; verify the destination file count/size and Git state before retiring the C: copy. Move/install Ollama binaries to `D:\Ollama`, move models and Ollama user data there, and relocate GNU Make if its D: copy passes `make --version`.
3. Set user `OLLAMA_MODELS` and PATH to D:, restart Ollama, verify `ollama list`, `/api/version`, `make test`, and `make ingest` from `D:\DL CP`, then update `ENVIRONMENT.md`/HANDOFF and resume P7.5 with an RRF topic aligned to the corpus.

## Environment state
Windows 11, PowerShell, Python 3.12.15, uv 0.13.4, CPU-only, 18 logical processors, 15.52 GiB RAM. Current checkout is `C:\Users\ketaki more\OneDrive\Documents\DL CP` (~6.57 GiB); D: is fixed and has ~147.9 GiB free. Ollama model data at `C:\Users\ketaki more\.ollama\models` is ~1.50 GiB. Ollama 0.40.11 is serving `http://localhost:11434` with `qwen2.5:1.5b` and `embeddinggemma`. GNU Make 4.4.1 is at `C:\msys64\usr\bin\make.exe`. The checkout contains uv, Python, virtual environments, caches, project weights, and Piper voice files under ignored `.tools/` and `models/` paths.

Use `UV_SYSTEM_CERTS=true`, `UV_CACHE_DIR=.tools/uv-cache`, and `UV_PROJECT_ENVIRONMENT=.tools/reports-venv` for project commands. Set `ARA_LLM_REQUEST_TIMEOUT_SECONDS=300` for live model calls. Ollama and web search need a process that can read the Windows certificate store; keep TLS verification enabled.

## WIP / uncommitted
No uncommitted source changes after `2098962`. The D: relocation has not started. P7.5 remains open; do not call the live report gate complete based on the isolated writer probe.

## Known failing tests / issues
`make test UV=.tools/uv/uv.exe` passed 298 tests in 28.77s; `make lint UV=.tools/uv/uv.exe` passed; MyPy reported no issues in 55 source files. The direct writer probe over five MCP-topic chunks returned a valid abstention, not a full report. RUN-001 remains open. The four-way RAG evaluation is NOT RUN, and the required 20-case reranker error analysis remains short of its target.

## Gotchas learned
- Reopen terminals after changing PATH.
- `make setup` removes QA-only packages such as `pypdfium2`; use a separate QA environment for PDF rendering.
- The current default shell cannot read the Ollama install folder or Windows native certificate store; use the approved process context for the move and verified-TLS web calls.
- The writer's structured schema constrains citations to supplied chunk IDs, one per claim, and permits a safe abstention. A complete live report bundle still needs verification.
- A historical shared clone `.tools/p7_5_clone/` is at P7.4 and lacks ignored model/voice assets; create a fresh clone only after the current commit and D: migration are stable.
