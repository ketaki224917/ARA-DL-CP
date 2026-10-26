# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: P1.10 — run four-way retrieval evaluation | Status: in progress
Environment task: ENV-006 — duplicate C: OneDrive checkout retirement remains blocked by inherited deny-child-delete ACL; D: project/runtime are canonical.

Last committed task: `60efa17 [P7.5] Pass clean-clone report regression`.

## Do next (exact)
1. Inspect `src/ara/rag/eval.py`, the concrete retriever/index APIs, and `src/ara/dl/evaluate.py`; implement a resumable 52-query runner for dense, BM25, hybrid RRF, and hybrid+rerank without disturbing DL `ara eval`.
2. Add focused tests for checkpoint/resume and metric semantics; expose a RAG evaluation command/Make target and save query-level predictions plus aggregate JSON/Markdown.
3. Run all 52 queries on the 21-document/33-chunk sample corpus with recorded model/version/candidate depth, then update `docs/evaluation.md`, TODO, PROGRESS, and this handoff with measured results.

## Environment state
Windows 11, PowerShell, Python 3.12.15 CPU-only (18 logical processors, 15.52 GiB RAM). Canonical checkout `D:\DL CP`; uv 0.13.4 at `D:\DL CP\.tools\uv\uv.exe`, cache `.tools\uv-cache`, managed Python `.tools\uv-python`; GNU Make 4.4.1 at `D:\msys64\usr\bin\make.exe`. Ollama 0.40.11 is running at localhost:11434 with `qwen2.5:1.5b` and `embeddinggemma`. Main checkout tests last passed 308; Ruff and MyPy passed. Fresh clone `.tools\p7_5_clean` passed setup/ingest/full report run at `0dfd734`; its bundle was citation-checked and the PDF/audio verified.

## WIP / uncommitted
None.

## Known failing tests / issues
No known failing tests. P1.10 four-system retrieval metrics are not yet run. P4.5 has a scripted three-topic demonstration but still needs a live-model effect over three topics. P5.5 has a 30-query held-out SciFact evaluation, but only four first-rank failures were available, fewer than the required 20-case review. ENV-006 remains open because Windows denies deleting the old C: OneDrive copy through an inherited deny-child-delete ACL; no permissions have been changed.

## Gotchas learned
- Set `TEMP` and `TMP` to `D:\DL CP\.tools\pytest-tmp` for tests.
- Set `UV_SYSTEM_CERTS=true`; keep TLS verification enabled.
- `ara eval` delegates to the custom DL evaluation. Add a separate RAG command or target so the existing behavior stays intact.
- Set `OLLAMA_MODELS=D:\Ollama\user-data\models` before running local inference.
- Keep PDF visual QA dependencies in `.tools\reports-venv`; `make setup` removes them from the project environment.
