# Environment

Updated: 2026-10-23 (session 1)

- OS/shell: Windows 11; PowerShell.
- CPU: Intel64 Family 6 Model 170 Stepping 4, GenuineIntel; 18 logical processors.
- RAM: 16,660,357,120 bytes (15.52 GiB), detected through `psutil.virtual_memory()`.
- GPU/VRAM: No supported CUDA/MPS adapter detected. `nvidia-smi` is unavailable and PyTorch is not installed, so GPU/VRAM details remain unknown.
- Python: 3.12.15 managed by uv at `.tools/python/cpython-3.12.15-windows-x86_64-none`; no PATH or registry change.
- uv: 0.13.4 at `.tools/uv/uv.exe`.
- Project environment: `.venv` created with `uv sync --extra dev`; `uv.lock` locks 154 resolved packages. Installed notable versions: pytest 8.4.2, Ruff 0.17.2, mypy 1.20.2, MCP SDK 2.3.0, ChromaDB 1.5.9.
- Package index: PyPI resolution/download works when `UV_SYSTEM_CERTS=true`. Default uv cache lock access was denied outside the workspace; set `UV_CACHE_DIR=.tools/uv-cache` for commands.
- Git: 2.55.0 available. GNU `make`: NOT FOUND.
- Ollama/model weights: Ollama NOT FOUND; no chat, embedding, or reranker model pulled.
- Services/ports: none started or checked.

## Model choice

Hardware probing found a CPU-only runtime with 18 logical processors and 15.52 GiB RAM. The supported GPU probe found no CUDA/MPS accelerator; the machine's display hardware and VRAM are not known because neither `nvidia-smi` nor PyTorch is available. The default chat model remains `qwen2.5:1.5b` to keep the prescribed CPU laptop demo small. The embedding model remains `embeddinggemma`. Neither has been downloaded or run; see ADR-015.

## Commands

```powershell
$env:UV_SYSTEM_CERTS = 'true'
$env:UV_CACHE_DIR = '.tools/uv-cache'
.tools/uv/uv.exe sync --extra dev
.tools/uv/uv.exe run pytest
.tools/uv/uv.exe run ruff check .
.tools/uv/uv.exe run mypy src
```

With Ollama installed and the configured models pulled, use `uv run ara ingest`, `uv run ara ask "<question>"`, and `uv run ara-rag-mcp`. GNU Make is unavailable; invoke the corresponding uv commands directly.
