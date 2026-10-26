# Environment

Updated: 2026-10-26 (session 1)

- OS/shell: Windows 11; PowerShell.
- CPU: Intel64 Family 6 Model 170 Stepping 4, GenuineIntel; 18 logical processors.
- RAM: 16,660,357,120 bytes (15.52 GiB), detected through `psutil.virtual_memory()`.
- GPU/VRAM: No supported CUDA/MPS adapter detected; CPU PyTorch reports `torch.cuda.is_available() == False`. `nvidia-smi` is unavailable, so exact display adapter/VRAM details remain unknown.
- Python: 3.12.15 managed by uv at `.tools/python/cpython-3.12.15-windows-x86_64-none`; no PATH or registry change.
- uv: 0.13.4 at `.tools/uv/uv.exe`.
- Project environments: `.venv` is the original dev environment. A clean `.tools/dl-venv` was synced with `uv sync --locked --extra dev --extra dl` after stale `.venv` metadata caused an access-denied cleanup error. The DL environment has Python 3.12.15, PyTorch `2.14.1+cpu`, Transformers `4.57.6`, Matplotlib `3.11.2`, pytest 8.4.2, Ruff 0.17.2, and mypy 1.20.2. `uv.lock` pins the full dependency graph.
- TTS environment: `.tools/tts-venv` was synced with `uv sync --locked --extra dev --extra dl --extra tts`; it includes Piper `1.8.0`, ONNX Runtime `1.31.0`, Hugging Face Hub `0.36.2`, and truststore `0.10.5`. Piper is an optional `tts` extra and is GPL-3.0-or-later. The selected `en_US-sam-medium` voice files are cached at ignored `models/tts/` from pinned `rhasspy/piper-voices` revision `b145f2ac26522d6a2ccde0164b7b0e48b1e3199c`; the voice model card points to an Apache-2.0 training dataset. Re-download with `python -m ara.generative.tts --download-voice` or `make tts-model` after installing the TTS extra.
- Package index: PyPI resolution/download works when `UV_SYSTEM_CERTS=true`. Default uv cache lock access was denied outside the workspace; set `UV_CACHE_DIR=.tools/uv-cache` for commands.
- Git: 2.55.0 available. GNU `make`: NOT FOUND.
- Ollama/model weights: Ollama NOT FOUND; chat and embedding models are not pulled. The `cross-encoder/ms-marco-MiniLM-L6-v2` checkpoint and tokenizer are cached under ignored `models/huggingface/` at revision `df500e56a59fc34f37322735a40eff666200312e`; CPU inference returned one finite relevance logit. The 90,870,598-byte weights file and tokenizer cache are not committed.
- Training artifacts: three CPU epochs completed with best validation BCE `0.309428`; metrics and loss curve are tracked at `outputs/dl_training_metrics.json` and `outputs/dl_training_loss.png`. The fine-tuned 90,891,664-byte checkpoint currently exists at ignored `models/checkpoints/reranker.pt` but is not committed and must be recreated by training in a fresh checkout.
- Export/inference: `python -m ara.dl.export` writes the validated 90,891,152-byte bundle to ignored `models/exported/reranker.pt`. `ara-dl-model-mcp` loads the bundle and tokenizer lazily on its first valid scoring call; a real MCP client scored two in-memory chunks on CPU with `dl_batch_size=1`. Recreate the source checkpoint by training, then run the export command. Neither trained checkpoint nor exported bundle is committed.
- Researcher reranking: optional and disabled by default (`dl.use_scorer: false`, `ARA_DL_USE_SCORER=false`). Enable it only when the caller connects the named `dl-model` MCP server and the exported bundle exists; unavailable scores preserve the original retrieval order.
- Evaluation artifacts: the pinned `sentence-transformers/all-MiniLM-L6-v2` encoder is cached under ignored `models/huggingface/` at revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; its document embedding cache is ignored at `data/indexes/dl_eval_test_embeddings.pt`. P5.5 compared 30 internal held-out SciFact queries. The random-negative control checkpoint is also ignored at `models/checkpoints/reranker_random_negatives.pt`; both learned checkpoints can be regenerated with `python -m ara.dl.train` and the evaluator's default ablation.
- Diagram tools: `dot`, Mermaid CLI (`mmdc`), Node, and npm were not found on PATH. ARA renders the constrained Mermaid subset with its standard-library SVG fallback; the optional Graphviz subprocess path is covered by a mocked test but has not been run against an installed Graphviz binary.
- Audio smoke: `python scripts/tts_synthesis_smoke.py` synthesized a controlled 185-word narration to ignored `outputs/generated/p6_2_voice_smoke.wav`; the last run was 68.79 seconds, 22,050 Hz, mono, 3,033,644 bytes. This verifies local Piper synthesis, not live LLM script generation. Ollama is unavailable under ENV-002.
- Services/ports: none started or checked.

- Report generation: `.tools/reports-venv` synced with locked `dev`, `dl`, and `tts` extras; Markdown-it `4.2.0`, ReportLab `5.1.0`, and svglib `2.3.2` are core locked dependencies. Poppler is NOT FOUND. `pypdfium2 5.14.0` is installed only in the ignored report QA environment for PDF-to-PNG visual inspection and is not a project dependency. Demo report bundle and rendered page are ignored under `outputs/generated/p6_3_demo/`.

## Model choice

Hardware probing found a CPU-only runtime with 18 logical processors and 15.52 GiB RAM. The supported GPU probe found no CUDA/MPS accelerator; the machine's display hardware and VRAM remain unknown. The default chat model remains `qwen2.5:1.5b` to keep the prescribed CPU laptop demo small. The embedding model remains `embeddinggemma`. Neither has been downloaded or run; see ADR-015. For the custom DL component, ADR-032 records the pinned MiniLM cross-encoder and CPU PyTorch choice.

## Commands

```powershell
$env:UV_SYSTEM_CERTS = 'true'
$env:UV_CACHE_DIR = '.tools/uv-cache'
$env:UV_PROJECT_ENVIRONMENT = '.tools/dl-venv'
.tools/uv/uv.exe sync --locked --extra dev --extra dl
.tools/uv/uv.exe run --locked --extra dev --extra dl pytest
.tools/uv/uv.exe run --locked --extra dev --extra dl ruff check .
.tools/uv/uv.exe run --locked --extra dev --extra dl mypy src scripts
```

On this Windows host, Hugging Face HTTPS needed `truststore.inject_into_ssl()` before importing Transformers because `requests`' bundled CA store did not trust the available system chain. Keep certificate validation enabled. Hugging Face warns that symlinks are unavailable under the current permissions; its cache falls back to copies and remains usable.

With Ollama installed and the configured models pulled, use `uv run ara ingest`, `uv run ara ask "<question>"`, and `uv run ara-rag-mcp`. GNU Make is unavailable; invoke the corresponding uv commands directly.
