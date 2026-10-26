# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: Phase 7 / P7.5 - live full-report regression | Status: in progress; RUN-001 is open

Last committed audit: `e5b871c [P7.7] Audit final acceptance checklist`. This checkpoint has source and state changes pending commit.

## Do next (exact)
1. Inspect the writer's prompt and structured-output payload: `rg -n "class ReportDraft|def structured_output|writer_messages" src/ara/agents/writer.py src/ara/agents/prompts/writer.py src/ara/llm/client.py`; reduce CPU generation cost or add a bounded output setting, with tests.
2. Re-run the live report after that change: set `ARA_LLM_REQUEST_TIMEOUT_SECONDS=300`, then run `make run TOPIC="MCP host client server responsibilities" ARGS="--max-revisions 0" UV=.tools/uv/uv.exe`; verify citations, Markdown/HTML/PDF, diagram, and WAV.
3. Create a clean clone at the updated commit and repeat the literal gate: `git clone --shared --local . .tools/p7_5_current_clone`; from the clone run `make setup UV=../uv/uv.exe`, `make ingest UV=../uv/uv.exe`, `make tts-model UV=../uv/uv.exe`, and `make run TOPIC="MCP host client server responsibilities" UV=../uv/uv.exe`.

## Environment state
Windows 11, PowerShell, Python 3.12.15, uv 0.13.4, CPU-only, 18 logical processors, 15.52 GiB RAM. GNU Make 4.4.1 is installed at `C:\msys64\usr\bin\make.exe`; that folder and `%LOCALAPPDATA%\Programs\Ollama` are in the user PATH (restart existing terminals). Ollama 0.40.11 is running at `http://localhost:11434`; `qwen2.5:1.5b` and `embeddinggemma` are pulled. The root checkout uses `.tools/reports-venv`, `.tools/uv-cache`, and the managed `.tools/uv/uv.exe`. `make setup` and `make ingest` passed; ingestion indexed 21 documents into 33 chunks. The pinned Piper voice already exists in the root `models/tts/`. Last disk check showed about 1.8 GB free.

## WIP / uncommitted
Researcher tool-call history fix and regression assertions, README corrections, and updated ADR/progress/environment/handoff/blocker/TODO/session state files are pending commit. The incomplete abstention-only probe created before the tool-history fix has been removed; its trace remains as an ignored diagnostic artifact.

## Known failing tests / issues
No known failing automated tests. `make test UV=.tools/uv/uv.exe` passed 295 tests in 60.71s; `make lint UV=.tools/uv/uv.exe` passed. The full live run completed research with six evidence chunks, but the writer returned an invalid structured draft and its retry exceeded a 300-second request timeout. P7.5 has not produced a complete live bundle or been verified in a clean clone. The 52-question four-way RAG evaluation remains NOT RUN. P5.5 has only four observed held-out ranking failures, short of the required 20. Live P4.5 and P5.1 measurements remain unrun. Web search from the restricted managed process could not access the Windows native certificate store; verified TLS search succeeded in the approved process context.

## Gotchas learned
- Pass `UV=.tools/uv/uv.exe` to Make because uv is workspace-local; set `UV_SYSTEM_CERTS=true`, `UV_CACHE_DIR=.tools/uv-cache`, and `UV_PROJECT_ENVIRONMENT=.tools/reports-venv`.
- Reopen the IDE terminal to load the updated user PATH for `make` and `ollama`.
- `make setup` removes QA-only packages not declared in `pyproject.toml`; it removed `pypdfium2`, so use a separate QA environment for PDF rendering.
- ADR-045 records that every Ollama tool turn must retain its assistant `tool_calls` message and the matching `role=tool` result, with retrieved content kept explicitly untrusted.
- A live `ara run` with `--max-revisions 0` still needs planning, researcher tool selection, structured writer output, critique, and report rendering; the local CPU model can exceed 300 seconds on the writer retry.
- The fresh clone `.tools/p7_5_clone/` is historical at P7.4 and lacks ignored model/voice assets. Use a new clone only after committing current changes.
