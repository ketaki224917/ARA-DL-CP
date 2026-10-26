# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current task: P7.5 — verify short-report TTS fallback in full live bundle | Status: ready for rerun
Environment task: ENV-006 — old OneDrive checkout at C: remains blocked by inherited deny-child-delete ACL; D: project/runtime are canonical and usable

Last committed task: `4117b3e [P7.5] Fall back for short narration scripts`.

## Do next (exact)
1. Commit the tested TTS fallback and state updates; verify `git diff --check` first.
2. Rerun the RRF report topic with `D:\msys64\usr\bin\make.exe "TOPIC=Explain reciprocal rank fusion and compare it with score-based fusion." run` from `D:\DL CP`, setting D: uv/cache/Python paths, `UV_SYSTEM_CERTS=true`, `ARA_LLM_REQUEST_TIMEOUT_SECONDS=300`, and `OLLAMA_MODELS=D:\Ollama\user-data\models`.
3. Inspect trace and `outputs/<run_id>/`; verify all citations, the recovered report, structural diagram, narration WAV, and MD/HTML/PDF before resolving RUN-001.

## Environment state
Windows 11, PowerShell, Python 3.12.15, uv 0.13.4, CPU-only, 18 logical processors, 15.52 GiB RAM. Canonical checkout: `D:\DL CP`; committed HEAD `16d8a11`. GNU Make 4.4.1/MSYS2: `D:\msys64`. uv executable/cache/managed Python: `D:\DL CP\.tools\uv`, `.tools\uv-cache`, `.tools\uv-python`; `.venv` is on D:. Ollama 0.40.11: `D:\Ollama\app`; models/user data: `D:\Ollama\user-data`; server at `localhost:11434`. Models available: `qwen2.5:1.5b`, `embeddinggemma:latest`.

## WIP / uncommitted
None. The citation-grounded TTS fallback is committed; focused TTS tests: 13 passed; full suite: 307 passed in 29.00s; Ruff passes; MyPy reports no issues in 55 source files.

## Known failing tests / issues
Latest live run `6f77b0bac8064a98a4e26ec746075863`: research finished with five local chunks; critic found one unsupported claim; recovery removed it, retained four cited claims, and the critic re-reviewed them with zero unsupported. Qwen Mermaid failed three attempts; structural SVG fallback rendered. TTS returned only 90 words on all four attempts, and the command stopped before report assembly. The TTS fallback is unit-tested but not yet live-verified. The four-way RAG evaluation remains NOT RUN; only four first-rank DL test failures exist, fewer than the required 20-case review. ENV-006 remains open due the C: OneDrive inherited deny-child-delete ACL; no permissions changed.

## Gotchas learned
- This PowerShell did not inherit the new D: PATH; invoke `D:\msys64\usr\bin\make.exe` and add `D:\DL CP\.tools\uv` explicitly. Set uv cache/Python paths to D:.
- For tests set `TEMP`/`TMP=D:\DL CP\.tools\pytest-tmp`; sandbox access to the D: uv lock may need approved escalation.
- Keep TLS verification enabled and `UV_SYSTEM_CERTS=true` for uv/web calls.
- `make setup` removes QA-only `pypdfium2`; use a separate QA environment for PDF rendering.
- `.tools/p7_5_clone/` is historical P7.4 and lacks ignored model/voice assets; use a fresh clone only after D: is stable.
