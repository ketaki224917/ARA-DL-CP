# HANDOFF (overwritten after every task)

Updated: 2026-10-27 | Session #: 1
Current phase/task: P5.5 - expand held-out reranker error analysis to 20 cases | Status: in progress
Environment task: ENV-006 — duplicate C: OneDrive checkout retirement remains blocked by inherited deny-child-delete ACL; D: project/runtime are canonical.

Last committed task: cad5582 [STATE] Resume live critic experiment.

$11. Inspect src/ara/dl/public_data.py, src/ara/dl/evaluate.py, split manifests, and current P5.5 metrics/error output to identify legal held-out queries.
2. Choose a deterministic expansion of the document-disjoint test split, retrain using only its train/validation documents, and rerun make eval with the expanded test set.
3. Review and document 20 actual held-out ranking failure cases, update P5.5 progress/TODO and model card, then run project regression checks.## Environment state
Windows 11, PowerShell, Python 3.12.15 CPU-only (18 logical processors, 15.52 GiB RAM). Canonical checkout `D:\DL CP`; uv 0.13.4/cache/Python under `D:\DL CP\.tools`; GNU Make 4.4.1 at `D:\msys64\usr\bin\make.exe`. Ollama 0.40.11 runs at localhost:11434 with `qwen2.5:1.5b` and `embeddinggemma`; Piper voice assets are on D:. Last full test suite: 311 passed; Ruff and MyPy clean. P7.5 fresh-clone report path and P1.10 52-query retrieval evaluation are complete. The measured RAG table and per-query rankings are committed in `outputs/rag_retrieval_evaluation/`.

## WIP / uncommitted
P4.5 live results and state updates are pending their task commit.

## Known failing tests / issues
No known failing tests. P4.5 has three live runs: one reduced unsupported claims from one to zero, and two stopped clean at zero; this is a small demonstration. P5.5 current 30-query SciFact test split yielded only four first-rank failures, so the requested 20-case error analysis needs a larger deterministic held-out test set with document-level isolation. ENV-006 remains open because Windows denies deleting the old C: OneDrive copy through an inherited deny-child-delete ACL; no permissions have been changed.

## Gotchas learned
- Set `TEMP`/`TMP` to `D:\DL CP\.tools\pytest-tmp` for tests.
- Set `UV_SYSTEM_CERTS=true`; keep TLS verification enabled.
- `ara eval` is for custom-DL evaluation; `ara rag-eval` runs the four-system RAG comparison.
- Set `OLLAMA_MODELS=D:\Ollama\user-data\models` before local inference.
- Keep PDF visual QA dependencies in `.tools\reports-venv`; `make setup` removes them from the project environment.
