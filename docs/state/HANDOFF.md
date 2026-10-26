# HANDOFF (overwritten after every task)

Updated: 2026-10-26 | Session #: 1
Current phase/task: P7.5 — fresh-clone full regression | Status: in progress
Environment task: ENV-006 — duplicate C: OneDrive checkout retirement remains blocked by inherited deny-child-delete ACL; D: project/runtime are canonical.

Last committed task: `98e4785 [P7.5] Keep tall figure heading with diagram`.

## Do next (exact)
1. Create a new clean clone: `git clone --no-local "D:\DL CP" "D:\DL CP\.tools\p7_5_clean"`.
2. In that clone, run `make setup` and `make ingest` with D: uv/cache/Python, `UV_SYSTEM_CERTS=true`, `OLLAMA_MODELS=D:\Ollama\user-data\models`, and `ARA_TTS_VOICE_MODEL_PATH=D:\DL CP\models\tts\en_US-sam-medium.onnx`.
3. Run `make "TOPIC=Explain reciprocal rank fusion and compare it with score-based fusion." run`; inspect outputs/citations and resolve CLONE-001 if the complete MD/HTML/PDF/SVG/WAV bundle passes.

## Environment state
Windows 11, PowerShell, Python 3.12.15 CPU-only (18 logical processors, 15.52 GiB RAM). Canonical checkout `D:\DL CP`; uv 0.13.4 at `D:\DL CP\.tools\uv\uv.exe`, cache `.tools\uv-cache`, managed Python `.tools\uv-python`; GNU Make 4.4.1 at `D:\msys64\usr\bin\make.exe`. Ollama 0.40.11 is running on localhost:11434 with `qwen2.5:1.5b` and `embeddinggemma`; Piper voice assets are at `D:\DL CP\models\tts\en_US-sam-medium.onnx` and its `.onnx.json`. The main checkout last passed 308 pytest tests, Ruff, and MyPy. Main-checkout run `cb9bbc9da4d9495eb76f87fe1543d78c` has a complete cited report bundle in `outputs/`; its 73.28-second narration and three-page PDF were checked.

## WIP / uncommitted
Only this handoff refresh is pending commit. No code or report artifacts are uncommitted.

## Known failing tests / issues
No known failing tests. P7.5 fresh-clone run remains unverified (CLONE-001). Four-way RAG evaluation (P1.10), three-topic live revision effect (P4.5), and the 20-case DL error analysis (P5.5) remain incomplete; do not report them as passed. ENV-006 remains open because the old C: OneDrive copy has an inherited deny-child-delete ACL; no permissions have been changed.

## Gotchas learned
- Set `TEMP` and `TMP` to `D:\DL CP\.tools\pytest-tmp` for tests.
- Use `UV_SYSTEM_CERTS=true`; keep TLS verification enabled.
- The D: voice/model assets are ignored and absent from a fresh Git clone, so point the clone's TTS configuration at the existing voice file.
- Keep PDF visual QA dependencies in `.tools\reports-venv`; `make setup` removes them from the project environment.
