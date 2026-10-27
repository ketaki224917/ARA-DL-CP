# HANDOFF (overwritten after every task)

Updated: 2026-10-27 | Session #: 1
Current phase/task: P7.7 - final clean-clone acceptance rerun | Status: in progress
Last committed task: 18f0a4f [P7.7] Recover research from web provider failures
Environment task: ENV-006 - the original C: OneDrive checkout remains blocked by an inherited deny-child-delete ACL; D: is the canonical project and runtime.

## Do next (exact)
1. Create a new clean clone at `D:\DL CP\.tools\p7_7_final_retry` from commit `18f0a4f`; keep `.tools\p7_7_final` as the failed-run record.
2. In the new clone, configure the D: uv/Make/Ollama paths and TTS voice, then run `make setup`, `make ingest`, and `make TOPIC="Explain reciprocal rank fusion and compare it with score-based fusion." run`.
3. Validate the report citations and MD/HTML/PDF/SVG/WAV artifacts, inspect PDF/audio metadata, resolve CLONE-002 if successful, and update the final acceptance audit.

## Environment state
Windows 11 build 26200, PowerShell, Python 3.12.15. Host: HP Laptop 14-gr1xxx, Intel Core Ultra 5 125H, 14 cores/18 logical, 15.52 GiB RAM, integrated Intel Arc (WMI reports about 2 GiB adapter memory), PyTorch 2.14.1+cpu without CUDA. Canonical checkout, uv, managed Python, GNU Make/MSYS2, Ollama, and model store are on D:. Ollama 0.40.11 has `qwen2.5:1.5b` and `embeddinggemma`; local TTS voice is `D:\DL CP\models\tts\en_US-sam-medium.onnx`. Last verification: `make test` 315 passed; `make lint` clean; MyPy clean in 56 files.

## WIP / uncommitted
Only this handoff refresh is pending commit.

## Known failing tests / issues
No known failing tests. CLONE-002 remains open until the fresh-clone report rerun passes. The free web-search provider returned intermittent 403/429/202 responses on the prior clone; ADR-063 adds one bounded local-RAG fallback. ENV-006 remains open because the old C: duplicate cannot be removed through its inherited deny-delete ACL; permissions have not been changed. P5.5 reports genuine evaluation results: the fine-tuned model beats RRF and generic reranking, while random-negative control is slightly higher on MRR/nDCG.

## Gotchas learned
- Before using uv: `UV_CACHE_DIR=D:\DL CP\.tools\uv-cache`, `UV_PYTHON_INSTALL_DIR=D:\DL CP\.tools\uv-python`, `UV_SYSTEM_CERTS=true`.
- Put `D:\DL CP\.tools\uv`, `D:\msys64\usr\bin`, and `D:\Ollama\app` on PATH; set `OLLAMA_MODELS=D:\Ollama\user-data\models` and `ARA_LLM_REQUEST_TIMEOUT_SECONDS=300`.
- Set `ARA_TTS_VOICE_MODEL_PATH=D:\DL CP\models\tts\en_US-sam-medium.onnx`; set `TEMP` and `TMP` to `D:\DL CP\.tools\pytest-tmp` for tests.
- `ara eval` evaluates the custom DL model; `ara rag-eval` evaluates the four retrieval systems. `make setup` installs the locked project environment; it does not install the optional PDF QA tools in `.tools\reports-venv`.
