# HANDOFF (overwritten after every task)

Updated: 2026-10-29 | Session #: 1
Current phase/task: P7.8 - localhost browser interface with topic and document upload | Status: complete; user-submitted run active
Last committed task: 914a0e3 [P7.8] Add local browser interface with document uploads
Canonical project/runtime: `D:\DL CP`; the old C: OneDrive duplicate remains blocked by its inherited deny-child-delete ACL (ENV-006).

## Do next (exact)
1. Follow run `f4fe60f79d2b4a9abf6321efb5c63ed4` for topic `risk aware abstention` at `http://127.0.0.1:8765/`; it is currently researching with no uploaded files.
2. When this run completes, use its report-artifact links in the page.
3. For a document run, start another topic and select multiple files or choose a folder (PDF, DOCX, Markdown, TXT, or HTML; 20 files, 20 MB/file, 50 MB total).

## Environment state
Windows 11 build 26200, PowerShell, Python 3.12.15. HP Laptop 14-gr1xxx; Intel Core Ultra 5 125H, 14 cores/18 logical, 15.52 GiB RAM, integrated Intel Arc (WMI reports about 2 GiB adapter memory), PyTorch 2.14.1+cpu without CUDA. Canonical checkout, uv, managed Python, GNU Make/MSYS2, Ollama, and models are on D:. Ollama 0.40.11 serves `qwen2.5:1.5b` and `embeddinggemma`; Piper voice is `D:\DL CP\models\tts\en_US-sam-medium.onnx`. ARA Research Studio currently listens on `127.0.0.1:8765` from the canonical checkout. Root-wide Ruff check passes; MyPy reports no issues in `src/ara/web_app.py`. The previous full test suite was 315 passed before P7.8.

## WIP / uncommitted
Only this handoff refresh is pending commit. The active run has no uploaded documents; no user files have been copied into the repository.

## Known failing tests / issues
No known failing tests. Tests were not rerun after P7.8. The browser app and `/api/status` returned HTTP 200; the user-submitted `risk aware abstention` run is still active, with no documents attached. CLONE-002 is resolved by the clean-clone run and artifact audit. ENV-006 remains open because the old C: duplicate is blocked by its inherited deny-delete ACL; no permissions were changed. The web app binds only to loopback and may send topic-derived queries to the configured public search provider. Each uploaded-document run re-indexes the sample corpus and retains the user files and its own index locally.

## Gotchas learned
- The ARA project is report-oriented; the browser page is the interface for starting an ARA run, which produces a cited report bundle.
- `make web` starts the interface; direct equivalent: `uv run --locked python -m ara.web_app`.
- Set `UV_CACHE_DIR=D:\DL CP\.tools\uv-cache`, `UV_PYTHON_INSTALL_DIR=D:\DL CP\.tools\uv-python`, `UV_SYSTEM_CERTS=true`, `OLLAMA_MODELS=D:\Ollama\user-data\models`, and `ARA_TTS_VOICE_MODEL_PATH=D:\DL CP\models\tts\en_US-sam-medium.onnx` before starting from a new shell.
- `ara eval` is the custom-DL evaluation command; `ara rag-eval` compares the four retrieval systems.
