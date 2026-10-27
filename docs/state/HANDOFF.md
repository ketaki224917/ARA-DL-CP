# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: P4.5 — measure live Writer/Critic quality on three topics | Status: in progress
Environment task: ENV-006 — duplicate C: OneDrive checkout retirement remains blocked by inherited deny-child-delete ACL; D: project/runtime are canonical.

Last committed task: `8a02797 [P1.10] Measure four-way RAG retrieval`.

## Do next (exact)
1. Inspect `data/sample_corpus/` and existing live traces; select three distinct topics that have relevant local evidence.
2. Run `make "TOPIC=<topic>" run` for each topic sequentially with D: Ollama/uv paths and a 300-second local LLM request timeout. Preserve each trace/run ID.
3. Compare first and final critic unsupported-claim counts from each revision-loop trace; update the P4.5 results table, progress/TODO, and handoff.

## Environment state
Windows 11, PowerShell, Python 3.12.15 CPU-only (18 logical processors, 15.52 GiB RAM). Canonical checkout `D:\DL CP`; uv 0.13.4/cache/Python under `D:\DL CP\.tools`; GNU Make 4.4.1 at `D:\msys64\usr\bin\make.exe`. Ollama 0.40.11 runs at localhost:11434 with `qwen2.5:1.5b` and `embeddinggemma`; Piper voice assets are on D:. Last full test suite: 311 passed; Ruff and MyPy clean. P7.5 fresh-clone report path and P1.10 52-query retrieval evaluation are complete. The measured RAG table and per-query rankings are committed in `outputs/rag_retrieval_evaluation/`.

## WIP / uncommitted
Only this handoff refresh is pending commit.

## Known failing tests / issues
No known failing tests. P4.5's scripted three-topic demo passes, but its live-model three-topic quality effect remains unmeasured; one live topic reduced unsupported claims from one to zero. P5.5's 30-query SciFact test split yielded only four first-rank failures, short of the requested 20-case review. ENV-006 remains open because Windows denies deleting the old C: OneDrive copy through an inherited deny-child-delete ACL; no permissions have been changed.

## Gotchas learned
- Set `TEMP`/`TMP` to `D:\DL CP\.tools\pytest-tmp` for tests.
- Set `UV_SYSTEM_CERTS=true`; keep TLS verification enabled.
- `ara eval` is for custom-DL evaluation; `ara rag-eval` runs the four-system RAG comparison.
- Set `OLLAMA_MODELS=D:\Ollama\user-data\models` before local inference.
- Keep PDF visual QA dependencies in `.tools\reports-venv`; `make setup` removes them from the project environment.
