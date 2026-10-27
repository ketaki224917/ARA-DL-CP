# HANDOFF (overwritten after every task)

Updated: 2026-10-27 | Session #: 1
Current phase/task: P7.7 - final acceptance regression and audit | Status: in progress
Environment task: ENV-006 - the old C: OneDrive checkout remains blocked by an inherited deny-child-delete ACL; D: is the canonical checkout/runtime.

Last committed task: 4caf82e [P0.6] Record the complete hardware inventory.

## Do next (exact)
1. Create a clean clone at D:\DL CP\.tools\p7_7_final from the current commit.
2. In that clone, run make setup, make ingest, and make run TOPIC="Explain reciprocal rank fusion and compare it with score-based fusion." with the D: Ollama service and local voice model configured.
3. Validate the generated citations, MD/HTML/PDF/SVG/WAV files, run the final acceptance checklist and repository checks, and record any remaining blocker honestly.

## Environment state
Windows 11 Home Single Language build 26200, PowerShell, Python 3.12.15. CPU: Intel Core Ultra 5 125H, 14 cores/18 logical processors; RAM: 15.52 GiB. Integrated Intel Arc graphics reports 2 GiB adapter memory through WMI; PyTorch 2.14.1+cpu has no CUDA devices. Canonical checkout, uv, Python, GNU Make, Ollama, and models are on D:. Ollama 0.40.11 serves qwen2.5:1.5b and embeddinggemma. P1.10 RAG comparison, P4.5 live three-topic critic experiment, and P5.5 208-query reranker evaluation are complete. Last full suite: 311 passed; Ruff and MyPy clean.

## WIP / uncommitted
Only this handoff refresh is pending commit.

## Known failing tests / issues
No known failing tests. P4.5 recorded unsupported counts 1->0, 0->0, 0->0. P5.5 has 20 genuine fine-tuned first-rank failures; the random-negative control slightly exceeds the fine-tuned model on MRR/nDCG. ENV-006 remains open: Windows denies deleting the old C: OneDrive copy through an inherited deny-child-delete ACL; no permissions have been changed.

## Gotchas learned
- Set TEMP and TMP to D:\DL CP\.tools\pytest-tmp for tests.
- Set UV_SYSTEM_CERTS=true and keep TLS verification enabled.
- ara eval is for custom-DL evaluation; ara rag-eval runs the four-system RAG comparison.
- Set OLLAMA_MODELS=D:\Ollama\user-data\models before local inference.
- Keep PDF visual QA dependencies in .tools\reports-venv; make setup removes them from the project environment.