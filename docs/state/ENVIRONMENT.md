# Environment

Updated: 2026-10-29 (session 1; localhost browser interface with local document uploads)

- OS/shell: Microsoft Windows 11 Home Single Language, build 26200 (64-bit); PowerShell.
- System/CPU: HP Laptop 14-gr1xxx; Intel Core Ultra 5 125H, 14 cores and 18 logical processors.
- RAM: 16,660,357,120 bytes (15.52 GiB), detected through psutil.virtual_memory().
- GPU/VRAM: Win32_VideoController reports integrated Intel Arc Graphics with AdapterRAM 2,147,479,552 bytes (about 2 GiB; adapter/shared-memory report, not a dedicated-VRAM measurement) and Meta Virtual Monitor with no memory value. Installed PyTorch is 2.14.1+cpu; torch.cuda.is_available() is false and device_count() is 0.
- Python: 3.12.15 managed by uv at `D:\DL CP\.tools\uv-python\cpython-3.12.15-windows-x86_64-none`.
- uv: 0.13.4 at `D:\DL CP\.tools\uv\uv.exe`; package cache at `D:\DL CP\.tools\uv-cache`.
- Project environments: `.venv` was rebuilt on D: with `uv sync --locked --extra dev --extra dl --extra tts`; it has the complete 137-package locked environment. `.tools/dl-venv`, `.tools/tts-venv`, and `.tools/reports-venv` were copied with the checkout. The D: uv Python runtime also keeps the old C: interpreter path working through a compatibility junction. `uv.lock` pins the full dependency graph.
- TTS environment: `.tools/tts-venv` was synced with `uv sync --locked --extra dev --extra dl --extra tts`; it includes Piper `1.8.0`, ONNX Runtime `1.31.0`, Hugging Face Hub `0.36.2`, and truststore `0.10.5`. Piper is an optional `tts` extra and is GPL-3.0-or-later. The selected `en_US-sam-medium` voice files are cached at ignored `models/tts/` from pinned `rhasspy/piper-voices` revision `b145f2ac26522d6a2ccde0164b7b0e48b1e3199c`; the voice model card points to an Apache-2.0 training dataset. Re-download with `python -m ara.generative.tts --download-voice` or `make tts-model` after installing the TTS extra.
- Package index: PyPI resolution/download works when `UV_SYSTEM_CERTS=true`; uv uses the D: cache and managed Python paths configured in the current user's environment.
- Git: 2.55.0 available. GNU Make 4.4.1 is at `D:\msys64\usr\bin\make.exe`; `D:\msys64\usr\bin`, `D:\Ollama\app`, and `D:\DL CP\.tools\uv` are in the user's PATH. Existing terminals need to be restarted to pick up the new entries.
- Ollama/model weights: Ollama 0.40.11 is installed at `D:\Ollama\app`; its model/config data is at `D:\Ollama\user-data` and `OLLAMA_MODELS` points to `D:\Ollama\user-data\models`. Its API responds at `http://localhost:11434`. `qwen2.5:1.5b` (986,061,892 bytes, Q4_K_M) and `embeddinggemma:latest` (621,875,917 bytes, BF16) are available. The `cross-encoder/ms-marco-MiniLM-L6-v2` checkpoint and tokenizer are cached under ignored `models/huggingface/` at revision `df500e56a59fc34f37322735a40eff666200312e`; CPU inference returned one finite relevance logit. The 90,870,598-byte weights file and tokenizer cache are not committed.
- Training artifacts: the expanded 415/70-query train/validation split trained on CPU for three epochs and selected epoch 1 by validation BCE `0.407094` (early stopping after epoch 3). Metrics and loss curve are tracked at `outputs/dl_training_metrics.json` and `outputs/dl_training_loss.png`. The fine-tuned 90,891,664-byte checkpoint exists at ignored `models/checkpoints/reranker.pt` but is not committed and must be recreated by training in a fresh checkout.
- Export/inference: `python -m ara.dl.export` writes the validated 90,891,152-byte bundle to ignored `models/exported/reranker.pt`. `ara-dl-model-mcp` loads the bundle and tokenizer lazily on its first valid scoring call; a real MCP client scored two in-memory chunks on CPU with `dl_batch_size=1`. Recreate the source checkpoint by training, then run the export command. Neither trained checkpoint nor exported bundle is committed.
- Researcher reranking: optional and disabled by default (`dl.use_scorer: false`, `ARA_DL_USE_SCORER=false`). Enable it only when the caller connects the named `dl-model` MCP server and the exported bundle exists; unavailable scores preserve the original retrieval order.
- Evaluation artifacts: the pinned `sentence-transformers/all-MiniLM-L6-v2` encoder is cached under ignored `models/huggingface/` at revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; its 1,592-document test embedding cache is ignored at `data/indexes/dl_eval_test_embeddings.pt`. P5.5 compared all 208 internal held-out SciFact queries and wrote 20 observed first-rank failures. The random-negative control checkpoint is also ignored at `models/checkpoints/reranker_random_negatives.pt`; recreate it by running `python -m ara.dl.evaluate` with the configured default ablation.
- Diagram tools: `dot`, Mermaid CLI (`mmdc`), Node, and npm were not found on PATH. ARA renders the constrained Mermaid subset with its standard-library SVG fallback; the optional Graphviz subprocess path is covered by a mocked test but has not been run against an installed Graphviz binary.
- Audio smoke: `python scripts/tts_synthesis_smoke.py` synthesized a controlled 185-word narration to ignored `outputs/generated/p6_2_voice_smoke.wav`; the last run was 68.79 seconds, 22,050 Hz, mono, 3,033,644 bytes. The pinned voice is present under `models/tts/`. In live run `cb9bbc9da4d9495eb76f87fe1543d78c`, the short model script was replaced with citation-grounded report text and Piper produced a 73.28-second WAV.
- Services/ports: D: Ollama serves `localhost:11434` (version `0.40.11`). ARA Research Studio is running from the canonical checkout at `http://127.0.0.1:8765/`; it binds loopback only and currently returns HTTP 200 for `/` and `/api/status`.

- Report generation: `.tools/reports-venv` has the locked `dev`, `dl`, and `tts` extras; Markdown-it `4.2.0`, ReportLab `5.1.0`, and svglib `2.3.2` are core locked dependencies. Poppler is not installed. `pypdfium2 5.14.0` is now installed only in `.tools/reports-venv` for visual QA; it is not a project dependency. The demo bundle remains ignored under `outputs/generated/p6_3_demo/`.
- Fresh-clone regression: `.tools/p7_7_final_retry/` at commit `a70d09f` passed `make setup`, `make ingest`, and `make TOPIC="Explain reciprocal rank fusion and compare it with score-based fusion." run`; it generated MD/HTML/PDF/SVG/WAV with valid citations and completed all three research tasks. `make test` passed 315 tests there. P7.8 adds the browser interface after that clone; the current canonical source passes Ruff and single-module MyPy checks.

## Model choice

WMI reports an HP Laptop 14-gr1xxx with an Intel Core Ultra 5 125H (14 cores, 18 logical processors), 15.52 GiB RAM, and integrated Intel Arc Graphics with about 2 GiB adapter memory. The installed PyTorch wheel is CPU-only and reports no CUDA devices; no supported accelerator runtime is available to this project. The default chat model remains qwen2.5:1.5b to fit the CPU-first laptop policy, and embeddinggemma remains the configurable embedding model. Both are installed and live report runs succeeded. ADR-015 records the original model choice; ADR-062 records this hardware inventory.

## Commands

```powershell
$env:UV_SYSTEM_CERTS = 'true'
$env:UV_CACHE_DIR = 'D:\DL CP\.tools\uv-cache'
$env:UV_PYTHON_INSTALL_DIR = 'D:\DL CP\.tools\uv-python'
make setup
make test
make lint
uv run --locked mypy src/ara
make ingest
make web
```

On this Windows host, Hugging Face HTTPS needed `truststore.inject_into_ssl()` before importing Transformers because `requests`' bundled CA store did not trust the available system chain. Keep certificate validation enabled. Hugging Face warns that symlinks are unavailable under the current permissions; its cache falls back to copies and remains usable.

GNU Make and Ollama are installed on this host. In a new PowerShell session, run `make setup`, `make ingest`, and `make run TOPIC="..."`. The user's PATH and `UV_CACHE_DIR`, `UV_PYTHON_INSTALL_DIR`, `UV_SYSTEM_CERTS`, and `OLLAMA_MODELS` variables now point to D:. No project-wide `UV_PROJECT_ENVIRONMENT` override is set; uv uses the rebuilt `.venv` at the D: checkout by default.

## D: relocation

- Working tree and Git history: `D:\DL CP` (canonical checkout; P7.8 browser interface committed as `914a0e3`). The original `C:\Users\ketaki more\OneDrive\Documents\DL CP` copy remains because Windows denies access to its `.pytest_cache`; `icacls` shows an inherited `Everyone` deny for deleting children on the OneDrive folder, and `Get-Acl` cannot read the cache. No ACL changes were made. The D: checkout has no junction back into OneDrive; source retirement is tracked as ENV-006.
- Ollama install: `D:\Ollama\app`; models, keys, and user data: `D:\Ollama\user-data`; app data: `D:\Ollama\appdata`.
- GNU Make/MSYS2: `D:\msys64`; uv cache: `D:\DL CP\.tools\uv-cache`; uv Python: `D:\DL CP\.tools\uv-python`.
- Compatibility junctions at the former C: Ollama, MSYS2, uv-cache, and uv-Python paths point to their D: locations. The user Ollama and MSYS2 shortcuts were changed to D: targets.
- Verification: full `pytest` → 308 passed; Ruff → all checks passed; MyPy → no issues in 55 source files. `make ingest` → 21 sources and 33 chunks, skipped as current. Ollama 0.40.11 found both models, generated chat responses, and returned 768-dimensional embeddings from the D: model store.
- Earlier live runs exposed writer, critique/revision, Mermaid, and narration failure modes; the D: report run `cb9bbc9da4d9495eb76f87fe1543d78c` completed the full bundle after adding bounded fallbacks. RUN-001 is resolved; CLONE-001 is still open.
