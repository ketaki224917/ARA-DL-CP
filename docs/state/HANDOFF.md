# HANDOFF (overwritten after every task)

Updated: 2026-10-29 | Session #: 1
Current phase/task: ENV-007 - D:-only runtime storage | Status: complete; latest uploaded-document run failed in critic
Last committed task: 9398348 [STATE] Refresh final acceptance and browser environment (P7.8: 914a0e3)
Canonical project/runtime: `D:\DL CP`; the old C: OneDrive duplicate remains blocked by its inherited deny-child-delete ACL (ENV-006).

## Do next (exact)
1. Inspect failed run `73efd09ccb424d5db6af94fbae0f14bf` for topic `risk aware abstention` at `http://127.0.0.1:8765/`; five user PDFs are stored under D:\DL CP\data\web_sessions\73efd09ccb424d5db6af94fbae0f14bf.
2. Fix critic structured-output handling: local Qwen returned malformed JSON and used citation chunk IDs instead of the supplied claim-NNN IDs; then retry the run with those stored PDFs.
3. Confirm the retried run completes and all artifacts remain under D:\DL CP\outputs and D:\DL CP\data\web_sessions.

## Environment state
Windows 11 build 26200, PowerShell, Python 3.12.15. HP Laptop 14-gr1xxx; Intel Core Ultra 5 125H, 14 cores/18 logical, 15.52 GiB RAM, integrated Intel Arc (WMI reports about 2 GiB adapter memory), PyTorch 2.14.1+cpu without CUDA. Canonical checkout, uv, managed Python, GNU Make/MSYS2, Ollama, model store, uv cache, and temporary directory are on D:. Ollama 0.40.11 serves `qwen2.5:1.5b` and `embeddinggemma`; Piper voice is `D:\DL CP\models\tts\en_US-sam-medium.onnx`. ARA Research Studio currently listens on `127.0.0.1:8765`; latest run failed in critic after indexing and researching five PDFs, with logs and session indexes under D:. The MyPy cache created on C: during the previous check was removed; subsequent MyPy cache is `D:\DL CP\.tools\mypy-webapp-cache`. Root Ruff passes via `make lint`; web-module MyPy passed before this task. The previous full suite was 315 passed before P7.8.

## WIP / uncommitted
ENV-007 storage-path changes and state records are uncommitted. The failed run has five uploaded PDFs in the ignored D:-relative session directory; no user documents were added to tracked files.

## Known failing tests / issues
No known failing tests. Tests were not rerun after P7.8. The browser app and `/api/status` returned HTTP 200; latest `risk aware abstention` run failed after indexing five user PDFs. Critic output had invalid JSON and chunk IDs where claim-NNN identifiers were required. All project caches, temp files, indexes, traces, uploads, and report outputs are configured to D:. CLONE-002 is resolved by the clean-clone run and artifact audit. ENV-006 remains open because the old C: duplicate is blocked by its inherited deny-child-delete ACL; no permissions were changed. The web app binds only to loopback and may send topic-derived queries to the configured public search provider. Each uploaded-document run re-indexes the sample corpus and retains the user files and its own index locally.

## Gotchas learned
- The ARA project is report-oriented; the browser page is the interface for starting an ARA run, which produces a cited report bundle.
- `make web` creates D:-local `.tools/tmp`, exports the D: uv cache/Python paths, and starts the interface. Direct `python -m ara.web_app` also sets runtime cache/temp paths under the checkout.
- Ollama and TTS are already configured on D:. `UV_SYSTEM_CERTS=true`, `OLLAMA_MODELS=D:\Ollama\user-data\models`, and `ARA_TTS_VOICE_MODEL_PATH=D:\DL CP\models\tts\en_US-sam-medium.onnx` are in the current runtime environment.
- `ara eval` is the custom-DL evaluation command; `ara rag-eval` compares the four retrieval systems.
