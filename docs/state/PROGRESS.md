# Progress Log

### 2026-10-22 — SESSION-1 — Bootstrap inspection
Done: Confirmed the workspace was empty and had no `.git`, project files, or state directory. Checked the required tools and hardware access.
Evidence: `git status --short --branch` and `git log --oneline -20` → both report “not a git repository”; `make test` → failed because `make` is not installed; `py --version` → no installed Python; `uv --version` and `ollama --version` → commands unavailable; `Get-CimInstance` CPU/RAM/GPU queries → WMI access denied; CPU identifier and 18 logical processors were readable.
Files: none at this inspection point.
Notes: Python/uv are needed before locking dependencies or running tests. RAM and GPU state remain unknown.

### 2026-10-22 — P0.2 — Bootstrap repository instructions and state
Done: Copied the supplied UTF-8 ARA specification to `AGENTS.md`; created all required state files, the initial full TODO, and the project directory layout. Added `CONVENTIONS.md` and initialized the workspace Git repository.
Evidence: `Get-ChildItem -Force` initially showed an empty workspace; created `docs/state/{HANDOFF,TODO,PROGRESS,DECISIONS,BLOCKERS,SESSIONS,ENVIRONMENT,CONVENTIONS}.md`, then confirmed Git recognizes the initialized `master` branch with `git -c safe.directory=... status --short --branch`. Commit NOT RUN: sandbox blocks writes to `.git` and requires approved escalation.
Files: `AGENTS.md`, `docs/state/*`, `.git/`.
Notes: `[P0.2]` and `[P0.3]` are complete. P0.1 packaging/lock generation remains in progress because Python and `uv` are absent.

### 2026-10-22 — P0.3 — Document coding conventions
Done: Added conventions for code style, modularity, logging, configuration, lazy model/network setup, test naming, determinism, and task commit messages.
Evidence: `Get-Content docs/state/CONVENTIONS.md` → convention file created and reviewed. Automated style checks NOT RUN because PyPI timed out before dev dependencies could be installed.
Files: `docs/state/CONVENTIONS.md`.
Notes: The conventions follow the user-supplied project requirements; the checks will run once dependencies resolve.

### 2026-10-22 — SESSION-1 — Toolchain setup and foundation implementation
Done: Installed uv 0.13.4 and managed CPython 3.12.15 in ignored `.tools/`; added packaging/config files, settings loading, logging setup, hardware probing, Ollama chat/stream/tool-call/structured-output client, and unit tests. Copied `AGENTS.md` matches the user attachment by SHA-256.
Evidence: Official uv installer completed; `.tools/uv/uv.exe python list --only-installed` → managed CPython 3.12.15 found; `.tools/python/.../python.exe -m compileall -q src tests` → passed; `uv lock` → NOT RUN TO COMPLETION because `https://pypi.org/simple/` timed out (PowerShell HEAD probe timed out after 15 seconds). pytest/ruff/mypy → NOT RUN because dependencies could not be resolved/installed.
Files: `pyproject.toml`, `.python-version`, `config.yaml`, `.env.example`, `Makefile`, `src/ara/config.py`, `src/ara/logging_setup.py`, `src/ara/hardware.py`, `src/ara/llm/client.py`, and tests.
Notes: P0.1 remains blocked on package-index access. P0.4-P0.7 code exists but remains in progress until dependency-backed tests pass. `.git` cannot be written from the current sandbox; no task commits exist yet.

### 2026-10-22 — SESSION-1 — Commit bootstrap tasks
Done: Committed P0.2 and P0.3 separately after approved Git escalation. Commit identity was passed for those commands only; global Git settings were not changed.
Evidence: `git log --oneline -3` → `f178f8c [P0.3] Document project conventions`; `21354d1 [P0.2] Bootstrap persistent instructions and state`.
Files: `AGENTS.md`, `docs/state/*`.
Notes: The preceding entry recorded the state before these commits. ENV-003 is resolved; later code tasks still need their own commits.

### 2026-10-22 — P0.8 — Build the open-licensed sample corpus
Done: Added 19 original explanatory Markdown notes on local retrieval and evidence grounding, with a CC BY 4.0 notice and a source/license manifest covering the upstream references. Logged ADR-003 for the corpus approach.
Evidence: PowerShell corpus check → 19 numbered notes, 0 missing reference lines, `LICENSE.md` and `SOURCES.md` present; Python `compileall -q src tests` → passed. Upstream claims and license metadata were checked against official documentation/repository pages; no upstream text was reproduced verbatim.
Files: `data/sample_corpus/*.md`, `docs/state/DECISIONS.md`, `docs/state/TODO.md`.
Notes: These are original concise summaries, not bundled copies of the complete source pages. The task is ready to commit; dependency-backed tests remain blocked on PyPI connectivity.

### 2026-10-22 — P0.8 — Commit the sample corpus
Done: Committed the 19-note CC BY 4.0 sample corpus, its sources/license manifest, ADR-003, and task state.
Evidence: `git log --oneline -3` → `521114b [P0.8] Add licensed retrieval sample corpus`.
Files: `data/sample_corpus/*`, `docs/state/DECISIONS.md`, `docs/state/TODO.md`, `docs/state/PROGRESS.md`, `docs/state/HANDOFF.md`.
Notes: The handoff now points to this task commit; P0.4-P0.7 are still awaiting dependency-backed test results.

### 2026-10-22 — P1.1/P1.2 — Implement source loaders and chunking
Done: Implemented loaders for PDF, DOCX, Markdown, text, and HTML, plus configurable overlap-aware chunking with stable IDs and source/page/character metadata. Added unit tests for formats, ordering, filtering, boundaries, offsets, and invalid settings.
Evidence: `.tools/python/.../python.exe -m compileall -q src tests` → passed; `tomllib.load` parsed `pyproject.toml`; pytest → NOT RUN because declared dependencies are not installed and PyPI timed out.
Files: `src/ara/rag/ingest.py`, `src/ara/rag/chunking.py`, `tests/test_ingest.py`, `tests/test_chunking.py`, `pyproject.toml`.
Notes: P1.1/P1.2 remain blocked until their test suites can run. HTML parsing removes script/style/template elements; chunk offsets remain tied to extracted page text.

### 2026-10-22 — P1.3 — Implement cached batched embeddings
Done: Added an Ollama `/api/embed` client, bounded batching, duplicate input handling, persistent SQLite vector cache keyed by model and text hash, and validation for malformed/non-finite/inconsistent vectors. Added mocked HTTP and cache tests; documented ADR-004.
Evidence: Python `compileall -q src tests` and `tomllib.load(pyproject.toml)` → passed before the final test additions; pytest → NOT RUN because PyPI timed out and dependencies are unavailable.
Files: `src/ara/rag/embeddings.py`, `src/ara/config.py`, `config.yaml`, `.env.example`, `tests/test_embeddings.py`, `tests/test_config.py`, `docs/state/DECISIONS.md`.
Notes: Ollama's official `/api/embed` documentation accepts one text or an array of texts; the selected model remains configurable and has not been pulled or run.

### 2026-10-22 — P1.4 — Implement vector-store adapters
Done: Added a shared vector-store protocol, a deterministic in-memory cosine store, a persistent Chroma adapter configured for cosine distance, and a Qdrant placeholder. Chroma accepts injected collections for isolated tests and preserves chunk provenance on upsert/search/get. Added adapter tests and ADR-005.
Evidence: `.tools/python/cpython-3.12.15-windows-x86_64-none/python.exe -m compileall -q src tests` → passed; `tomllib` parsed `pyproject.toml`; dependency-free smoke check exercised chunk offsets, in-memory cosine ranking, and ID lookup → passed. pytest/ruff/mypy → NOT RUN because PyPI timed out and dependencies are unavailable.
Files: `src/ara/rag/vectorstore.py`, `src/ara/rag/types.py`, `src/ara/rag/ingest.py`, `src/ara/rag/chunking.py`, `tests/test_vectorstore.py`, `tests/test_chunking.py`, `docs/state/DECISIONS.md`, `docs/state/TODO.md`.
Notes: P1.4 remains blocked until its tests run successfully. `LoadedDocument` was moved to a dependency-free shared type module so chunking and the in-memory store can be smoke-checked without parser packages.

### 2026-10-22 — P1.5 — Implement persisted BM25 retrieval
Done: Added deterministic Unicode word tokenization, BM25 ranking with provenance filters, stable tie ordering, versioned JSON persistence, atomic file replacement, index validation, and round-trip tests. Logged ADR-006.
Evidence: `compileall -q src tests` → passed; `tomllib` parsed `pyproject.toml`; dependency-free smoke check covered ranking, filtering, and persistence round-trip → passed. pytest/ruff/mypy → NOT RUN because PyPI timed out and dependencies remain unavailable.
Files: `src/ara/rag/bm25.py`, `tests/test_bm25.py`, `docs/state/DECISIONS.md`, `docs/state/TODO.md`.
Notes: P1.5 remains blocked until its test suite runs successfully. Persisted JSON stores the chunks and BM25 parameters, then reconstructs postings on load.

### 2026-10-22 — P1.6 — Implement hybrid RRF retrieval
Done: Added a hybrid retriever that embeds the query once, requests bounded candidate lists from dense and BM25 indexes, applies weighted reciprocal-rank fusion, and returns source ranks/scores with stable chunk IDs. Added protocol-backed unit tests and ADR-007.
Evidence: `compileall -q src tests` → passed; dependency-free smoke check confirmed a chunk ranked by both sources receives the fused lead and retains dense/BM25 ranks. pytest/ruff/mypy → NOT RUN because dependency resolution remains blocked. Escalated `uv lock` with Windows system certificates downloaded the managed interpreter but stalled before package resolution and was interrupted; `uv.lock` remains unavailable.
Files: `src/ara/rag/retriever.py`, `tests/test_retriever.py`, `docs/state/DECISIONS.md`, `docs/state/BLOCKERS.md`, `docs/state/TODO.md`.
Notes: P1.6 remains blocked until its tests run successfully. RRF uses one-based ranks and equal default weights; actual effectiveness still requires evaluation.

### 2026-10-22 — P1.7 — Add optional CrossEncoder reranker
Done: Added a lazy Sentence Transformers CrossEncoder adapter that reranks hybrid candidates, validates one finite score per candidate, and preserves retrieval score/ranks. Added optional dependency metadata, configurable model name, and injected-model tests. Logged ADR-008.
Evidence: `compileall -q src tests` → passed; `tomllib` parsed `pyproject.toml`; dependency-free reranker smoke check confirmed score ordering and retrieval provenance. pytest/ruff/mypy → NOT RUN because PyPI resolution remains blocked.
Files: `src/ara/rag/reranker.py`, `src/ara/config.py`, `config.yaml`, `.env.example`, `pyproject.toml`, `tests/test_reranker.py`, `tests/test_config.py`, `docs/state/DECISIONS.md`, `docs/state/TODO.md`.
Notes: P1.7 remains blocked until its tests run successfully. Sentence Transformers and model weights are not installed; module import and empty candidate calls do not load either.

### 2026-10-22 — P1.8 — Add cited answers and abstention
Done: Added structured atomic claim generation, code-rendered chunk citations, validation that cited IDs are in the retrieved evidence, prompt-injection framing for evidence text, deterministic empty/low-score abstention, and configurable evidence floor/context size. Added mocked LLM tests and ADR-009.
Evidence: `compileall -q src tests` → passed. pytest/ruff/mypy and runtime answer checks → NOT RUN because Pydantic and other declared packages are not installed; official PyPI resolution stalled.
Files: `src/ara/rag/answer.py`, `src/ara/config.py`, `config.yaml`, `.env.example`, `tests/test_answer.py`, `tests/test_config.py`, `docs/state/DECISIONS.md`, `docs/state/TODO.md`.
Notes: P1.8 remains blocked until its tests run successfully. The default evidence floor is an RRF heuristic; it must be calibrated during P1.10 evaluation.
