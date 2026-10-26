# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: Phase 6 / P6.3 — Markdown/HTML/PDF report builder with figures, references, and audio | Status: next

Last completed task: P6.2 narration/TTS source committed as `6b318bd`; state commit is pending.

## Do next (exact)
1. Inspect `ReportDraft`/citation rendering, the diagram and TTS artifact APIs, installed HTML/PDF libraries, and existing output conventions.
2. Choose a CPU-local PDF path, log any nontrivial choice, then implement report assembly for Markdown, HTML, PDF, figures, references, and a narrated-audio link.
3. Add focused tests for citation/reference preservation, SVG/image embedding, audio links, renderer failures, and output paths; run the full suite, Ruff, MyPy, and `git diff --check`, then update and commit state.

## Environment state
Windows 11; PowerShell; Git 2.55.0. Python 3.12.15 and uv 0.13.4 are under ignored `.tools/`. Use `UV_PROJECT_ENVIRONMENT=.tools/tts-venv`, `UV_SYSTEM_CERTS=true`, and `UV_CACHE_DIR=.tools/uv-cache`; this environment was synced with locked `dev`, `dl`, and `tts` extras. It includes PyTorch `2.14.1+cpu`, Transformers 4.57.6, Matplotlib 3.11.2, Piper 1.8.0, ONNX Runtime 1.31.0, Hugging Face Hub 0.36.2, and truststore 0.10.5. CPU-only, 18 logical processors, 15.52 GiB RAM; exact display adapter/VRAM unknown. Trained reranker files and voice assets are ignored under `models/`. The `en_US-sam-medium` voice is downloaded at pinned revision `b145f2ac26522d6a2ccde0164b7b0e48b1e3199c`. GNU Make and Ollama are unavailable; Graphviz/mermaid-cli are absent; no services are running.

## WIP / uncommitted
P6.2 files: `src/ara/generative/tts.py`, `scripts/tts_synthesis_smoke.py`, `tests/test_tts.py`, configuration, lockfile, Makefile, and `.env.example` are committed as `6b318bd`. State docs for P6.2 are updated and pending the state commit. The smoke WAV at `outputs/generated/p6_2_voice_smoke.wav` is ignored.

## Known failing tests / issues
No known pytest/Ruff/MyPy failures. Latest full suite: 279 passed in 38.82s; Ruff clean; MyPy clean for 58 source files. P6.2 local audio synthesis ran successfully; live LLM narration-script generation remains NOT RUN because Ollama is unavailable under ENV-002. P5.5 retrieval metrics cover a 30-query internal SciFact split, not the official test set; P4.5 live revision-quality measurement also remains unavailable.

## Gotchas learned
- Set `$env:UV_SYSTEM_CERTS='true'` and `$env:UV_CACHE_DIR='.tools/uv-cache'` before uv commands in this environment.
- GNU Make is absent; invoke the matching uv commands directly.
- Import `truststore` before Hugging Face downloads on this host; TLS verification remains enabled. Hugging Face cache uses copies because symlinks are unavailable.
- Recreate the ignored reranker checkpoint with `python -m ara.dl.train`, then recreate its export with `python -m ara.dl.export`.
- Re-download the ignored Piper model with `python -m ara.generative.tts --download-voice`; reproduce local synthesis with `python scripts/tts_synthesis_smoke.py`.
- `build_narration_script` needs the configured local Ollama model; `synthesize_narration` needs the TTS extra and voice files but performs no network access.
