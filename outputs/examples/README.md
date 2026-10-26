# Example report bundles

These three examples exercise ARA's Markdown, HTML, PDF, figure, reference, and narration
pipeline using curated summaries of original sample corpus notes. They are reproducible software
demos, not reports produced by a live Planner/Researcher/Writer run; no Ollama request, web search,
retrieval benchmark, or retrieval-quality claim is included.

Each report has inline citations to chunk IDs computed by ARA's production loader and chunker.
The bundle includes `evidence.json` with the exact passage and chunk settings, a constrained Mermaid
source plus rendered SVG, a Piper narration WAV, and the Markdown, HTML, and PDF outputs. The diagram
structure is supplied by a deterministic local stub through the production validation and SVG
renderer so it can be rebuilt without Ollama. Audio is synthesized locally with the configured
Piper voice.

## Rebuild and validate

From the repository root, install the `dev`, `dl`, and `tts` extras, download the configured voice,
then generate and validate the reports:

```powershell
uv run --locked --extra dev --extra dl --extra tts python -m ara.generative.tts --download-voice
uv run --locked --extra dev --extra dl --extra tts python scripts/generate_example_reports.py
uv run --locked --extra dev --extra dl --extra tts python scripts/generate_example_reports.py --validate-only
```

The generation command writes three subdirectories here. Citation validation resolves the
generated IDs against fresh chunks from `data/sample_corpus/`; PDF files are opened with pypdf and
the referenced SVG and WAV assets are checked for presence. Voice setup is documented in
`docs/state/ENVIRONMENT.md` and `Makefile`.

## Attribution

The source notes are original ARA explanatory text licensed under CC BY 4.0. Their references and
license details are in [`data/sample_corpus/SOURCES.md`](../../data/sample_corpus/SOURCES.md).
Retain attribution to this repository and its CC BY 4.0 notice when adapting the notes or excerpts.
