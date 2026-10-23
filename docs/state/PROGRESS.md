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

### 2026-10-22 — P1.9 — Build the retrieval evaluation set
Done: Added 52 labeled questions over the 19-note corpus: 34 factoid, 10 multi-hop with multiple gold IDs, and 8 unanswerable. Added a schema/source note, an integrity test, and ADR-010.
Evidence: A standard-library validation using the production `chunk_document` defaults found 52 unique records, category counts 34/10/8, 27 corpus chunks, and no missing or invalid gold chunk IDs. Every multi-hop item has multiple gold IDs. `compileall -q src tests` → passed. pytest for the integrity test → NOT RUN because pytest is unavailable while PyPI resolution is blocked.
Files: `data/eval_sets/rag_eval.jsonl`, `data/eval_sets/README.md`, `tests/test_eval_set.py`, `docs/state/DECISIONS.md`, `docs/state/TODO.md`.
Notes: The integrity checks were run directly with CPython and the repository chunker; metric comparisons have not yet run.

### 2026-10-22 — P1.10 — Implement retrieval evaluation harness
Done: Added JSONL loading/validation, per-run recall@k, MRR, binary nDCG@k, citation precision, answer-rate and abstention metrics, named-run comparison, Markdown tables, and atomic JSON output. Documented metric definitions and the four-system comparison table, explicitly marked NOT RUN. Logged ADR-011.
Evidence: `compileall -q src tests` → passed; all 52 evaluation records loaded; synthetic three-query metric smoke check returned recall@2=0.750, MRR=0.750, nDCG@2=0.693, citation precision=0.750. These values validate formulas only. pytest/ruff/mypy and real dense/BM25/hybrid/hybrid+reranker runs → NOT RUN because dependencies, Ollama, and model weights are unavailable.
Files: `src/ara/rag/eval.py`, `tests/test_eval.py`, `docs/evaluation.md`, `docs/state/DECISIONS.md`, `docs/state/TODO.md`.
Notes: P1.10 remains blocked until the four actual retriever runs and metric table are recorded. Do not copy the synthetic smoke values into the comparison table.

### 2026-10-22 — P1.11 — Add idempotent ingestion and ask CLI
Done: Added manifest-based ingestion reconciliation across the dense and BM25 indexes, stable-ID listing/deletion, configured source/index paths, `ara ingest`, and evidence-grounded `ara ask`. Added optional `--rerank` for installations with the rerank extra and model weights. Logged ADR-012.
Evidence: `.tools/python/cpython-3.12.15-windows-x86_64-none/python.exe -m compileall -q src tests` → passed; `tomllib` parsed `pyproject.toml`; `git diff --check` passed; touched Python files have no lines over 100 characters. A dependency-free ingestion smoke check passed: first run indexed 4 chunks, unchanged second run skipped, changed content removed 4 stale IDs, and embedding-model change reindexed 5 chunks. pytest/ruff/mypy → NOT RUN because those packages are absent and the user confirmed no trusted internal PyPI mirror; live Ollama/Chroma CLI run → NOT RUN because those services are unavailable.
Files: `src/ara/cli.py`, `src/ara/rag/indexing.py`, `src/ara/rag/vectorstore.py`, `src/ara/rag/bm25.py`, config files, README, `tests/test_cli.py`, `tests/test_indexing.py`, `tests/test_vectorstore.py`, `tests/test_config.py`, and state files.
Notes: P1.11 implementation and dependency-free smoke checks are complete; acceptance remains blocked on dependency-backed tests and a real local model/store run.

### 2026-10-23 — P2.1 — Add shared MCP server support
Done: Added standard-library helpers to validate argument objects, bounded text, integers, and text lists; defined safe tool errors and sanitized payloads; and added structured-duration logging that omits tool arguments. Added focused pytest coverage and ADR-013.
Evidence: `.tools/python/cpython-3.12.15-windows-x86_64-none/python.exe -m compileall -q src tests` → passed; a direct runtime smoke check exercised success/failure validation, timeout retryability, safe error conversion, and call logging → passed; touched P2.1 files have no lines over 100 characters. pytest/ruff/mypy → NOT RUN because packages are absent and there is no trusted internal mirror.
Files: `src/ara/mcp_servers/__init__.py`, `src/ara/mcp_servers/common.py`, `tests/test_mcp_common.py`, `docs/state/DECISIONS.md`, and task state files.
Notes: P2.1 implementation is ready; test acceptance remains blocked until dev dependencies can be installed.

### 2026-10-23 — P2.2 — Add the RAG MCP server
Done: Added `search_knowledge_base` and `get_chunk` MCP tools backed by the hybrid retriever and vector store, bounded strict input validation, structured citation/provenance output, safe tool errors, and the `ara-rag-mcp` stdio entry point. Added tests using the official SDK's in-memory Client and logged ADR-014.
Evidence: `.tools/python/cpython-3.12.15-windows-x86_64-none/python.exe -m compileall -q src tests` → passed; `tomllib` confirmed the `mcp>=2,<3` dependency and script entry point; P2.1 stdlib validation/error/logging smoke check passed. SDK import, pytest, in-memory protocol tests, Ruff, and mypy → NOT RUN because the MCP/dev packages are not installed and PyPI access remains blocked.
Files: `src/ara/mcp_servers/rag_server.py`, `src/ara/mcp_servers/common.py`, `tests/test_mcp_rag_server.py`, `tests/test_mcp_common.py`, `pyproject.toml`, README, and state files.
Notes: The server implementation and protocol tests are drafted but remain blocked from runtime validation until the official SDK can be installed.

### 2026-10-23 — ENV-004 — Restore package access and run the regression suite
Done: Resolved the project with uv, created `uv.lock`, installed the dev environment and MCP SDK, and fixed the lint/type/test findings exposed by the first complete run.
Evidence: `.tools/uv/uv.exe lock --verbose` with `UV_SYSTEM_CERTS=true` → 154 packages resolved; `.tools/uv/uv.exe sync --extra dev` → 111 packages installed; `.tools/uv/uv.exe run --locked pytest` → 99 passed; `ruff check .` → clean; `mypy src` → no issues in 22 source files.
Files: `uv.lock`, `pyproject.toml`, settings, evaluation, retrieval, indexing, chunking, and test modules.
Notes: A custom uv cache under `.tools/uv-cache` avoids an access-denied lock in the default AppData cache. Real Ollama retrieval runs remain unavailable.

### 2026-10-23 — P0.5 — Validate application logging
Done: The standard logging setup and its invalid-level/configuration tests run successfully in the installed environment.
Evidence: Full `.tools/uv/uv.exe run --locked pytest` → logging tests passed as part of 99 passing tests; Ruff and mypy are clean.
Files: `src/ara/logging_setup.py`, `tests/test_logging_setup.py`.
Notes: Logging setup is complete; the module does not attach duplicate handlers.

### 2026-10-23 — P0.6 — Record detected hardware and model choice
Done: The hardware probe detected 18 logical processors, 15.52 GiB RAM, and no supported CUDA/MPS accelerator. Added ADR-015 selecting the CPU-friendly 1.5B Qwen default.
Evidence: `.tools/uv/uv.exe run --locked python -c "from ara.hardware import detect_hardware; print(detect_hardware())"` → `Windows 11`, Intel64 Family 6 Model 170 Stepping 4, 18 processors, 16,660,357,120 RAM bytes, accelerator `cpu`, no GPU name/VRAM. Hardware unit tests passed in the 99-test suite.
Files: `src/ara/hardware.py`, `tests/test_hardware.py`, `docs/state/ENVIRONMENT.md`, `docs/state/DECISIONS.md`.
Notes: `nvidia-smi` and PyTorch are unavailable, so exact display adapter and VRAM remain unknown; neither selected model has been pulled or benchmarked.

### 2026-10-23 — P0.7 — Validate the local Ollama client
Done: The chat, streaming, tool-call, and structured-output client unit tests pass with mocked HTTP responses.
Evidence: Full `.tools/uv/uv.exe run --locked pytest` → all six LLM client tests passed; Ruff and mypy are clean.
Files: `src/ara/llm/client.py`, `tests/test_llm_client.py`.
Notes: Ollama is not installed, so no live model request was made.

### 2026-10-23 — Phase 1 — Validate RAG implementation tests
Done: Dependency-backed tests now pass for loaders, chunking, embeddings/cache, vector stores, BM25, RRF, reranking, cited answers, evaluation metrics, and idempotent indexing.
Evidence: Full `.tools/uv/uv.exe run --locked pytest` → all applicable tests passed; Ruff and mypy are clean. The changed-corpus indexing fixture was corrected to keep before/after passage lengths equivalent.
Files: `tests/test_ingest.py`, `tests/test_indexing.py`, and RAG modules with lint/type fixes.
Notes: The real four-way retrieval metric comparison is still NOT RUN because Ollama and model weights are unavailable.

### 2026-10-23 — P2.1/P2.2 — Validate MCP tools through the SDK client
Done: Shared MCP support and the RAG server passed dependency-backed tests; the in-memory SDK client successfully called search and chunk lookup and observed safe error results.
Evidence: `pytest tests/test_mcp_common.py tests/test_mcp_rag_server.py` → 18 passed; full suite → 99 passed; `ruff check .` and `mypy src` → clean.
Files: `src/ara/mcp_servers/common.py`, `src/ara/mcp_servers/rag_server.py`, `tests/test_mcp_common.py`, `tests/test_mcp_rag_server.py`.
Notes: The stdio server process and Claude Desktop host have not yet been manually exercised; that check belongs to P2.6.

### 2026-10-23 — P2.3 — Add web search MCP tools
Done: Added the free DDGS search backend, `web_search` and `fetch_page` MCP tools, stable `web:<hash>` IDs, bounded public-page fetching, redirect and URL checks, HTML sanitization, explicit untrusted-content markers, and a bounded TTL/LRU cache. Added offline MCP-client and safety tests, the `ara-web-search-mcp` entry point, README usage, and ADR-016.
Evidence: `.tools/uv/uv.exe run --locked pytest` → 115 passed; `.tools/uv/uv.exe run --locked ruff check .` → clean; `.tools/uv/uv.exe run --locked mypy src` → no issues in 23 source files; `git diff --check` → passed.
Files: `src/ara/mcp_servers/web_search_server.py`, `tests/test_mcp_web_search_server.py`, `pyproject.toml`, `uv.lock`, README, and state files.
Notes: Tests use an injected search backend and HTTP mock transport; a live metasearch request and stdio/Claude Desktop check were not run. Search snippets and fetched content are external untrusted data.

### 2026-10-23 — P2.4 — Add the typed custom-model MCP stub
Done: Added `score_chunks(query, chunk_ids)` to `ara-dl-model-mcp` with bounded unique-ID validation and a structured `not_ready` response until P5.6 trains and loads the custom scorer. Added in-memory MCP-client tests, the stdio entry point, README usage, and ADR-017.
Evidence: `.tools/uv/uv.exe run --locked --no-sync pytest` → 118 passed; `.tools/uv/uv.exe run --locked --no-sync ruff check .` → clean; `.tools/uv/uv.exe run --locked --no-sync mypy src` → no issues in 24 source files; `git diff --check` → passed.
Files: `src/ara/mcp_servers/dl_model_server.py`, `tests/test_mcp_dl_model_server.py`, `pyproject.toml`, README, and state files.
Notes: The response intentionally contains no synthetic or placeholder scores; training and loading remain part of P5.6.

### 2026-10-23 — P2.5 — Add the stdio MCP client wrapper
Done: Added an async wrapper for named stdio server connections, tool discovery, tool calls, bounded timeouts/retries, retryable MCP error payloads, and deterministic process cleanup. Added a local fixture server and subprocess tests for listing, calling, retry, timeout, continued connection use, and child exit. Logged ADR-018.
Evidence: `.tools/uv/uv.exe run --locked --no-sync pytest` → 120 passed; `.tools/uv/uv.exe run --locked --no-sync ruff check .` → clean; `.tools/uv/uv.exe run --locked --no-sync mypy src` → no issues in 26 source files; `git diff --check` → passed.
Files: `src/ara/mcp_client/client.py`, `src/ara/mcp_client/__init__.py`, `tests/mcp_stdio_fixture.py`, `tests/test_mcp_client.py`, and state files.
Notes: A protocol tool error is returned to the caller unless its JSON payload explicitly marks it retryable. Server subprocess stderr inherits the parent process as documented by the SDK.
