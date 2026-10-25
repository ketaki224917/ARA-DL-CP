# Environment

Updated: 2026-10-25 (session 1)

- OS/shell: Windows 11; PowerShell.
- CPU: Intel64 Family 6 Model 170 Stepping 4, GenuineIntel; 18 logical processors.
- RAM: 16,660,357,120 bytes (15.52 GiB), detected through `psutil.virtual_memory()`.
- GPU/VRAM: No supported CUDA/MPS adapter detected; CPU PyTorch reports `torch.cuda.is_available() == False`. `nvidia-smi` is unavailable, so exact display adapter/VRAM details remain unknown.
- Python: 3.12.15 managed by uv at `.tools/python/cpython-3.12.15-windows-x86_64-none`; no PATH or registry change.
- uv: 0.13.4 at `.tools/uv/uv.exe`.
- Project environments: `.venv` is the original dev environment. A clean `.tools/dl-venv` was synced with `uv sync --locked --extra dev --extra dl` after stale `.venv` metadata caused an access-denied cleanup error. The DL environment has Python 3.12.15, PyTorch `2.14.1+cpu`, Transformers `4.57.6`, Matplotlib `3.11.2`, pytest 8.4.2, Ruff 0.17.2, and mypy 1.20.2. `uv.lock` pins the full dependency graph.
- Package index: PyPI resolution/download works when `UV_SYSTEM_CERTS=true`. Default uv cache lock access was denied outside the workspace; set `UV_CACHE_DIR=.tools/uv-cache` for commands.
- Git: 2.55.0 available. GNU `make`: NOT FOUND.
- Ollama/model weights: Ollama NOT FOUND; chat and embedding models are not pulled. The `cross-encoder/ms-marco-MiniLM-L6-v2` checkpoint and tokenizer are cached under ignored `models/huggingface/` at revision `df500e56a59fc34f37322735a40eff666200312e`; CPU inference returned one finite relevance logit. The 90,870,598-byte weights file and tokenizer cache are not committed.
- Training artifacts: three CPU epochs completed with best validation BCE `0.309428`; metrics and loss curve are tracked at `outputs/dl_training_metrics.json` and `outputs/dl_training_loss.png`. The fine-tuned 90,891,664-byte checkpoint currently exists at ignored `models/checkpoints/reranker.pt` but is not committed and must be recreated by training in a fresh checkout.
- Services/ports: none started or checked.

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
