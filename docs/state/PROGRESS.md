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

### 2026-10-23 — P2.6 — Add Claude Desktop setup and stdio verification
Done: Added a portable three-server Claude Desktop JSON sample with absolute-path placeholders, an integration test that starts all three servers as real stdio subprocesses, and a verification note with results and limitations. Confirmed tool discovery and the DL model not-ready response through the SDK client.
Evidence: `uv run --locked --no-sync pytest tests/test_mcp_stdio_servers.py` → 1 passed; full suite → 121 passed; JSON sample parsed with `python -m json.tool`; Ruff and mypy clean; `git diff --check` passed.
Files: `docs/claude_desktop_config.example.json`, `docs/stdio_verification.md`, `tests/test_mcp_stdio_servers.py`, and state files.
Notes: Claude Desktop itself was not launched in this environment; the protocol-level stdio checks do not claim UI integration.

### 2026-10-23 — P3.1 — Add typed orchestration state
Done: Added shared Pydantic models for planner subtasks, citation-ready local/web evidence, critiques, run metadata, and `AgentState`. Added cross-field validation, JSON round-trip, evidence deduplication/conflict detection, atomic batch insertion, and revision-cap tests. Logged ADR-020.
Evidence: `.tools/uv/uv.exe run --locked --no-sync pytest` → 141 passed; `.tools/uv/uv.exe run --locked --no-sync ruff check .` → clean; `.tools/uv/uv.exe run --locked --no-sync mypy src` → no issues in 28 source files; `git diff --check` → passed.
Files: `src/ara/agents/state.py`, `src/ara/agents/__init__.py`, `tests/test_agent_state.py`, and state files.
Notes: Plan is empty before planning and must contain 3-8 tasks once populated. All evidence is marked untrusted regardless of local or web provenance.

### 2026-10-24 — P3.2 — Add validated research planner
Done: Added a planner prompt and strict structured-output schema for 3-8 research tasks. Validated unique task IDs, same-plan dependencies, and an acyclic dependency graph; converted accepted tasks to pending `PlanTask` objects. Reused the Ollama client's bounded schema retry and JSON repair behavior. Logged ADR-021.
Evidence: `.tools/uv/uv.exe run --locked --no-sync pytest` → 152 passed; `.tools/uv/uv.exe run --locked --no-sync ruff check .` → clean; `.tools/uv/uv.exe run --locked --no-sync mypy src` → no issues in 31 source files; `git diff --check` → passed.
Files: `src/ara/agents/planner.py`, `src/ara/agents/prompts/`, `tests/test_planner.py`, and state files.
Notes: Tests used an in-memory HTTP transport; no live Ollama service or model was available for generation.

### 2026-10-24 — P3.3 — Add MCP-backed researcher
Done: Added the researcher tool catalog and prompt, validated local-search/web-search/page-fetch calls, named MCP routing with retries disabled, dependency ordering, and per-run call/evidence-count/character budgets. Added local and fetched web evidence to `AgentState` with stable-ID deduplication; search snippets remain untrusted navigation observations. Added tests for tool selection, invalid calls, dependency order, MCP errors, deduplication, and budget exhaustion. Logged ADR-022.
Evidence: `.tools/uv/uv.exe run --locked --no-sync pytest` → 164 passed; `.tools/uv/uv.exe run --locked --no-sync ruff check .` → clean; `.tools/uv/uv.exe run --locked --no-sync mypy src` → no issues in 33 source files; `git diff --check` → passed.
Files: `src/ara/agents/researcher.py`, `src/ara/agents/prompts/researcher.py`, `tests/test_researcher.py`, and state files.
Notes: MCP and LLM behavior were mocked for researcher unit tests; no live Ollama call, indexed-corpus search, or external web query was run.

### 2026-10-24 — P3.4 — Add orchestration and JSONL traces
Done: Added a hand-rolled async orchestrator for plan/research lifecycle, plan reuse, run status updates, and failure recording. Added validated append-only `TraceEvent` JSONL output with safe run IDs and bounded tool arguments/results. Added researcher task, tool-selection, and tool-call events with latency. Logged ADR-023.
Evidence: `.tools/uv/uv.exe run --locked --no-sync pytest` → 173 passed; `.tools/uv/uv.exe run --locked --no-sync ruff check .` → clean; `.tools/uv/uv.exe run --locked --no-sync mypy src` → no issues in 35 source files; `git diff --check` → passed.
Files: `src/ara/agents/orchestrator.py`, `src/ara/agents/trace.py`, researcher trace hooks, `tests/test_orchestrator.py`, and state files.
Notes: Orchestration tests inject mocked planner/researcher components and use temporary trace directories. No live Ollama or MCP-backed research run was available.

### 2026-10-24 — P3.5 — Add prompt-injection test fixtures
Done: Added synthetic malicious local-document, web-search snippet, and fetched-page fixtures. Tests pass each through the researcher observation path, confirm the model receives data-only/untrusted framing, and make the mocked model request an unapproved tool; the researcher rejects it before MCP execution. Retrieved fixture text remains marked untrusted in evidence.
Evidence: `.tools/uv/uv.exe run --locked --no-sync pytest` → 176 passed; `.tools/uv/uv.exe run --locked --no-sync ruff check .` → clean; `.tools/uv/uv.exe run --locked --no-sync mypy src` → no issues in 35 source files; `git diff --check` → passed.
Files: `tests/fixtures/prompt_injection/`, `tests/test_researcher.py`.
Notes: The examples are synthetic and test tool-policy enforcement; they do not claim to measure how a live model responds to prompt injection.

### 2026-10-24 — P3.6 — Complete offline plan/research gate
Done: Added a runnable offline demo with the real structured-output Planner, Researcher, MCPClient stdio transport, Orchestrator, and JSONL trace writer. The demo uses a deterministic mocked Ollama response and a clearly synthetic MCP server, verifies all three tasks complete with one evidence item, and saves `traces/sample_research_run.jsonl`. Documented the command and limitations in README. Logged ADR-024.
Evidence: `uv run python scripts/offline_e2e_demo.py --trace-dir traces --run-id sample_research_run` → status completed; 3 tasks completed; 1 synthetic evidence item. `.tools/uv/uv.exe run --locked --no-sync pytest` → 178 passed; `.tools/uv/uv.exe run --locked --no-sync ruff check .` → clean; `.tools/uv/uv.exe run --locked --no-sync mypy src scripts` → no issues in 37 source files; `git diff --check` → passed.
Files: `scripts/offline_e2e_demo.py`, `scripts/offline_research_mcp_server.py`, `tests/test_end_to_end_research.py`, `traces/sample_research_run.jsonl`, README, and state files.
Notes: This is an offline software integration run, not live model generation or real research. ENV-002 remains open for Ollama/model weights, real retrieval evaluation, and live end-to-end validation. Phase 3 acceptance is complete for the implemented offline path.

### 2026-10-24 — P4.1 — Add evidence-grounded report writer
Done: Added a fixed-section structured report schema with claim-level evidence IDs, bounded score-ordered evidence context, untrusted-data framing, deterministic inline citation rendering, model/no-evidence abstention, and fail-closed behavior for citations outside the supplied context. The writer stores its Markdown draft in `AgentState`. Logged ADR-025.
Evidence: `.tools/uv/uv.exe run --locked --no-sync pytest` → 187 passed; `.tools/uv/uv.exe run --locked --no-sync ruff check .` → clean; `.tools/uv/uv.exe run --locked --no-sync mypy src scripts` → no issues in 39 source files; `git diff --check` → passed.
Files: `src/ara/agents/writer.py`, `src/ara/agents/prompts/writer.py`, `tests/test_writer.py`, and state files.
Notes: Writer tests use mocked structured output. No live Ollama generation was run; claim support still requires the P4.3 critic, and P4.2 adds a standalone rendered-citation validator.

### 2026-10-24 — P4.2 — Add deterministic citation parsing and validation
Done: Added `validate_citations` for `[chunk:<id>]` and `[web:<id>]` markers. It returns unique IDs in report order, separates unknown evidence IDs from malformed markers, accepts ordinary bracketed Markdown, and treats nested citation-looking brackets as one malformed marker. Logged ADR-026.
Evidence: `.tools/uv/uv.exe run --locked --no-sync pytest` → 199 passed; `.tools/uv/uv.exe run --locked --no-sync ruff check .` → clean; `.tools/uv/uv.exe run --locked --no-sync mypy src scripts` → no issues in 40 source files; `git diff --check` → passed.
Files: `src/ara/agents/citations.py`, `tests/test_citations.py`, and state files.
Notes: Validation checks citation syntax and membership in the supplied evidence keys; it does not decide whether the cited text supports a claim. The P4.3 critic handles claim-level support review. No live model was needed for this deterministic utility.

### 2026-10-24 — P4.3 — Add structured evidence critic
Done: Added Markdown claim extraction, deterministic missing/malformed/unknown citation findings, bounded untrusted evidence context, structured per-claim support judgments, plan-gap and contradiction findings, cross-reference validation, and replacement of `AgentState.critiques` only after a valid review. The result includes reviewed, supported, unsupported, gap, and contradiction counts for P4.4. Logged ADR-027.
Evidence: `.tools/uv/uv.exe run --locked --no-sync pytest` → 209 passed; `.tools/uv/uv.exe run --locked --no-sync ruff check .` → clean; `.tools/uv/uv.exe run --locked --no-sync mypy src scripts` → no issues in 42 source files; `git diff --check` → passed.
Files: `src/ara/agents/critic.py`, `src/ara/agents/prompts/critic.py`, `tests/test_critic.py`, and state files.
Notes: Tests use deterministic mocked structured output. No live Ollama critique was run because Ollama and model weights remain unavailable under ENV-002.

### 2026-10-24 — P4.4 — Add capped writer/critic revision loop
Done: Added `RevisionLoop`, which starts from a fresh research state, drafts once, reviews each draft, sends the previous draft and bounded high-severity-first critic feedback into rewrites, and stops on abstention, a clean review, an unchanged draft, or `run_metadata.max_revisions`. It returns per-iteration reviewed/supported/unsupported/gap/contradiction/finding counts and can emit bounded JSONL trace events through a callback. Logged ADR-028.
Evidence: `.tools/uv/uv.exe run --locked --no-sync pytest` → 221 passed; `.tools/uv/uv.exe run --locked --no-sync ruff check .` → clean; `.tools/uv/uv.exe run --locked --no-sync mypy src scripts` → no issues in 43 source files; `git diff --check` → passed.
Files: `src/ara/agents/revision.py`, `src/ara/agents/prompts/writer.py`, `src/ara/agents/writer.py`, `src/ara/agents/trace.py`, `tests/test_revision.py`, `tests/test_writer.py`, and state files.
Notes: Convergence and trace tests use deterministic mocks, including one real Writer/Critic integration with scripted model outputs. Live reduction in unsupported claims has not been measured; P4.5 will first record an offline three-topic controlled demonstration, with live model validation remaining unavailable under ENV-002.

### 2026-10-25 — P4.5 — Add scripted three-topic revision-loop demonstration
Done: Added a reproducible CLI that loads three separate sample-corpus notes and runs the actual `Writer`, `Critic`, and `RevisionLoop` components with scripted structured responses. It checks prior-draft and critic-feedback propagation, iteration counts, stop reason, and trace events. Logged ADR-029.
Evidence: `.tools/uv/uv.exe run --locked --no-sync python scripts/offline_revision_demo.py` produced:

| Topic | Unsupported before | Unsupported after | Reduction | Revisions | Stop reason |
|---|---:|---:|---:|---:|---|
| What can hybrid retrieval do, and what should be evaluated? | 1 | 0 | 100% | 1 | clean |
| How should report citations preserve and verify provenance? | 1 | 0 | 100% | 1 | clean |
| How should a research agent handle instructions inside retrieved text? | 1 | 0 | 100% | 1 | clean |

The script labels these as a scripted offline demonstration, not a live-model quality measurement. `.tools/uv/uv.exe run --locked --no-sync pytest` → 222 passed; Ruff clean; mypy → no issues in 44 source files; `git diff --check` → passed.
Files: `scripts/offline_revision_demo.py`, `tests/test_revision_demo.py`, and state files.
Notes: The initial unsupported judgments and revisions are deliberately scripted. Live-model effect measurement is NOT RUN because Ollama and weights are unavailable (ENV-002); the controlled result verifies software behavior only. Code/test commit: `033be55`.

### 2026-10-25 — P5.1 — Add synthetic reranker pair generator
Done: Added structured local-Ollama question generation with untrusted-passage framing and schema validation, a deterministic heading/keyword fallback, BM25 hard-negative mining, an optional dense candidate adapter, source/near-duplicate filters, stable seeded selection, provenance-rich pair records, and atomic JSONL export. Added config values and tests. Logged ADR-030.
Evidence: `.tools/uv/uv.exe run --locked --no-sync python -m ara.dl.data_gen --offline --output data/dl_data/synthetic_pairs_offline.jsonl` → 33 chunks; 32 generated examples; 1 query rejected because its positive was not retrieved; 0 examples lacked negatives; all 32 queries were unique, query origin was `extractive`, mining method was BM25, and no positive/negative pair shared a source. `.tools/uv/uv.exe run --locked --no-sync pytest` → 229 passed; Ruff clean; mypy → no issues in 45 source files; `git diff --check` → passed.
Files: `src/ara/dl/data_gen.py`, `config.yaml`, `src/ara/config.py`, `tests/test_data_gen.py`, `tests/test_config.py`, `data/dl_data/synthetic_pairs_offline.jsonl`, and state files.
Notes: This run used the explicit offline fallback. The local Ollama question-generation path is covered with a scripted client but NOT RUN against a live model; dense mining is optional and NOT RUN because no Ollama embeddings/Chroma index are available. The 32-example artifact is a small reproducible baseline, not a validated training set. Code/data/test commit: `fa6ba18`.

### 2026-10-25 — P5.2 — Add a public SciFact subset with document-level splits
Done: Added an explicit downloader with HTTPS host and pinned SHA-256 verification, an archive parser for labeled SciFact train/dev claims and the S2ORC abstract corpus, deterministic 200-query selection, support/contradict relevance mapping, rationale preservation, evidence-linked component splits, seeded assignment of remaining documents, overlap validation, and JSONL/metadata export. Added license/source attribution and configuration. Logged ADR-031.
Evidence: `.tools/uv/uv.exe run --locked --no-sync python -m ara.dl.public_data --download` → downloaded and verified the 3,115,079-byte official archive, SHA-256 `11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be`; prepared 200 labeled claims and 5,183 corpus documents. Query counts: train 140, validation 30, test 30. Document counts: train 3,602, validation 759, test 822. The component split created 175 evidence-linked groups; document IDs are pairwise disjoint, and every query's positive documents are in that query's split. `.tools/uv/uv.exe run --locked --no-sync pytest` → 233 passed; Ruff clean; mypy → no issues in 46 source files; `git diff --check` → passed.
Files: `src/ara/dl/public_data.py`, config, `tests/test_public_data.py`, `tests/test_config.py`, `data/dl_data/SOURCES.md`, and `data/dl_data/scifact_subset/`.
Notes: Claims and evidence annotations are CC BY 4.0; abstracts are ODC-By 1.0. The internal held-out test split is not the original SciFact test set. Dataset preparation is reproducible from the pinned archive; the downloaded archive cache is ignored by Git. Code/data/test commit: `d5db624`.

### 2026-10-25 — P5.3 — Add CPU-capable reranker dataset and model
Done: Added the optional PyTorch CPU/Transformers dependency set, config/env controls, split-safe SciFact pair construction with deterministic BM25 mined negatives, train-only P5.1 pair augmentation, a reproducible zero-worker DataLoader, and a pinned MiniLM cross-encoder with binary relevance loss plus an optional masked credibility head. Logged ADR-032.
Evidence:
- Pair audit: `$env:UV_SYSTEM_CERTS='true'; $env:UV_CACHE_DIR='.tools/uv-cache'; $env:UV_PROJECT_ENVIRONMENT='.tools/dl-venv'; .tools/uv/uv.exe run --locked --extra dev --extra dl python -c "from ara.config import load_settings; from ara.dl.dataset import build_pair_examples; s=load_settings(); rows=[(split, (r:=build_pair_examples(s.dl_public_data_dir, split, candidate_k=s.dl_candidate_k, negative_pool_size=s.dl_negative_pool_size, seed=s.dl_seed, include_synthetic_train=(split == 'train'), synthetic_path='data/dl_data/synthetic_pairs_offline.jsonl')).query_count, r.positive_pair_count, r.mined_negative_count, r.synthetic_pair_count, r.queries_without_negatives) for split in ('train','validation','test')]; print(rows)"` → train 140 queries / 154 labeled positives / 140 mined negatives / 32 synthetic pairs; validation 30 / 32 / 30 / 0; test 30 / 31 / 30 / 0; zero queries without mined negatives in all splits.
- Model smoke: `$env:UV_SYSTEM_CERTS='true'; $env:UV_CACHE_DIR='.tools/uv-cache'; $env:UV_PROJECT_ENVIRONMENT='.tools/dl-venv'; .tools/uv/uv.exe run --locked --extra dev --extra dl python -c "import truststore; truststore.inject_into_ssl(); from ara.config import load_settings; from ara.dl.model import CrossEncoderScorer, load_pair_tokenizer; import torch; s=load_settings(); m=CrossEncoderScorer.from_pretrained(s).eval(); t=load_pair_tokenizer(s); x=t(['What is the reported health effect?'], ['A short abstract reports an observed health effect.'], return_tensors='pt', truncation=True, max_length=64); y=m(**x); print(f'checkpoint={s.reranker_model}@{s.dl_model_revision} device=cpu torch={torch.__version__} logits={y.relevance_logits.tolist()}')"` → checkpoint loaded at pinned revision with `torch=2.14.1+cpu`; logit `[4.512841701507568]`.
- Full test suite: `$env:UV_SYSTEM_CERTS='true'; $env:UV_CACHE_DIR='.tools/uv-cache'; $env:UV_PROJECT_ENVIRONMENT='.tools/dl-venv'; .tools/uv/uv.exe run --locked --extra dev --extra dl pytest` → 240 passed in 56.65s. Ruff → clean; mypy → no issues in 48 source files; `git diff --check` → passed.
Files: `src/ara/dl/dataset.py`, `src/ara/dl/model.py`, `pyproject.toml`, `uv.lock`, config/env examples, and tests. Weights and tokenizer cache are ignored by Git.
Notes: CUDA/MPS were not available; training quality and baseline comparison remain P5.4/P5.5 work. The credibility head remains disabled because neither current dataset has source-credibility labels. SciFact BM25 negatives are unjudged candidates and may contain relevant evidence; evaluation uses its retained labeled positives. Hugging Face download needed `truststore.inject_into_ssl()` to use Windows system certificates; TLS verification remained enabled. Code/test commit: `b63c711`.

### 2026-10-25 — P5.4 — Add seeded cross-encoder training
Done: Added config-driven AdamW/BCE training with Python/Torch seeding, train and validation split loaders, validation-loss early stopping, atomic best-checkpoint writes, JSON history, and a PNG train/validation loss curve. Added the `matplotlib` DL-extra dependency and set the configured synthetic-pair path to the committed P5.1 offline artifact. The trainer never loads the test split. Logged ADR-033.
Evidence:
- `.tools/uv/uv.exe lock` → resolved 146 packages and added Matplotlib 3.11.2; `$env:UV_SYSTEM_CERTS='true'; $env:UV_CACHE_DIR='.tools/uv-cache'; $env:UV_PROJECT_ENVIRONMENT='.tools/dl-venv'; .tools/uv/uv.exe sync --locked --extra dev --extra dl` → installed the plotting dependency.
- Full run: `$env:UV_SYSTEM_CERTS='true'; $env:UV_CACHE_DIR='.tools/uv-cache'; $env:UV_PROJECT_ENVIRONMENT='.tools/dl-venv'; $env:HF_HUB_OFFLINE='1'; .tools/uv/uv.exe run --locked --extra dev --extra dl python -m ara.dl.train` → 3 epochs, 358 training examples (294 SciFact positive/mined-negative examples plus 64 synthetic examples), 62 validation examples; epoch train/validation BCE: `0.684900/0.416132`, `0.437026/0.335476`, `0.321357/0.309428`; best epoch 3. It took about 8m35s on CPU. The 30-query held-out test split was not loaded.
- Reload check: `$env:UV_SYSTEM_CERTS='true'; $env:UV_CACHE_DIR='.tools/uv-cache'; $env:UV_PROJECT_ENVIRONMENT='.tools/dl-venv'; $env:HF_HUB_OFFLINE='1'; .tools/uv/uv.exe run --locked --extra dev --extra dl python -c "from ara.config import load_settings; from ara.dl.model import CrossEncoderScorer; import torch; s=load_settings(); payload=torch.load(s.dl_checkpoint_path, map_location='cpu', weights_only=True); model=CrossEncoderScorer.from_pretrained(s); model.load_state_dict(payload['model_state_dict']); print('checkpoint_format', payload['format_version'], 'best_epoch', payload['best_epoch'], 'best_validation_loss', round(payload['best_validation_loss'], 6), 'tensors', len(payload['model_state_dict']))"` → format 1, best epoch 3, validation loss `0.309428`, 105 tensors loaded.
- `$env:UV_SYSTEM_CERTS='true'; $env:UV_CACHE_DIR='.tools/uv-cache'; $env:UV_PROJECT_ENVIRONMENT='.tools/dl-venv'; .tools/uv/uv.exe run --locked --extra dev --extra dl pytest` → 241 passed in 40.50s; Ruff clean; mypy → no issues in 49 source files; `git diff --check` → passed.
Files: `src/ara/dl/train.py`, config/env settings, `pyproject.toml`, `uv.lock`, `tests/test_training.py`, `outputs/dl_training_metrics.json`, and `outputs/dl_training_loss.png`. The generated learned checkpoint is ignored at `models/checkpoints/reranker.pt`.
Notes: This is a training/validation run, not an evaluation against baselines. Validation loss uses BM25 mined, unjudged documents as negatives. The tracked curve and metrics show optimization progress only; P5.5 will score held-out labeled relevance and compare baselines. Code/test/artifact commit: `0e89284`.

### 2026-10-25 — P5.5 — Evaluate the reranker against held-out baselines
Done: Added a cached, pinned dense encoder and a held-out evaluation harness comparing BM25+dense RRF, the generic MiniLM cross-encoder, the P5.4 fine-tuned model, and a separately trained random-negative control. The test partition is loaded only after control training and is used only for ranking metrics and error review. Logged ADR-034.
Evidence: `$env:UV_SYSTEM_CERTS='true'; $env:UV_CACHE_DIR='.tools/uv-cache'; $env:UV_PROJECT_ENVIRONMENT='.tools/dl-venv'; .tools/uv/uv.exe run --locked --extra dev --extra dl python -m ara.dl.evaluate` → 30 internal held-out SciFact queries; candidate recall@20 `1.0000`; mean RRF candidate union `32.73`.

| System | Recall@10 | MRR | nDCG@10 |
|---|---:|---:|---:|
| BM25+dense RRF | 0.9667 | 0.9026 | 0.9175 |
| Generic MS MARCO cross-encoder | 0.9667 | 0.8854 | 0.9052 |
| Fine-tuned cross-encoder | 0.9667 | 0.9194 | 0.9298 |
| Random-negative control | 0.9667 | 0.9026 | 0.9175 |

The fine-tuned checkpoint ties RRF on recall@10 and modestly improves MRR (`+0.0169`) and nDCG@10 (`+0.0123`) on this small split. The generic model is below RRF on both rank-quality metrics, and the random-negative control matches RRF. The fine-tuned model had four first-rank failures among 30 queries; all four are reviewed in `outputs/dl_error_analysis.json`. The requested 20 failure cases did not exist in this test set, so no successful queries were mislabeled or added to reach 20. This internal split is not the official SciFact test set, and the result is descriptive rather than statistically conclusive.
Control training: 358 training and 62 validation examples; best validation BCE `0.050674` at epoch 1 (`0.065077` at epoch 2, `0.058376` at epoch 3); the best checkpoint was retained. Test suite: 246 passed in 69.43s; Ruff clean; mypy clean for 52 source files; `git diff --check` passed (Git reported expected LF-to-CRLF working-copy notices).
Files: `src/ara/dl/dense.py`, `src/ara/dl/hf_compat.py`, `src/ara/dl/evaluate.py`, config/env settings, `pyproject.toml`, `uv.lock`, tests, and `outputs/dl_evaluation_metrics.{json,md}`, `outputs/dl_error_analysis.json`, `outputs/dl_training_metrics_random_negatives.json`, and `outputs/dl_training_loss_random_negatives.png`.
Notes: Both model checkpoints and the dense document-embedding cache are ignored local artifacts and must be regenerated in a fresh checkout. The pinned dense and cross-encoder weights are cached locally. Evaluation and training run on CPU. Code/test/artifact commit: `482adf4`.

### 2026-10-26 — P5.6 — Export the scorer and load it through the DL MCP server
Done: Added an atomic inference bundle exporter with checkpoint/model/revision validation and a configurable export path. Replaced the P2.4 not-ready-only stub with a lazy local service that loads the exported weights/tokenizer on first scoring, fetches indexed chunks by ID, batches inference using `dl_batch_size`, returns sigmoid relevance and optional credibility probabilities, preserves requested order, and returns explicit not-ready or not-found responses. Added config coverage, exporter tests, injected-model MCP tests, and isolated the stdio cold-start test from local model artifacts. Logged ADR-035.
Evidence:
- `$env:UV_SYSTEM_CERTS='true'; $env:UV_CACHE_DIR='.tools/uv-cache'; $env:UV_PROJECT_ENVIRONMENT='.tools/dl-venv'; $env:HF_HUB_OFFLINE='1'; .tools/uv/uv.exe run --locked --extra dev --extra dl python -m ara.dl.export` → atomically wrote `models/exported/reranker.pt` (90,891,152 bytes) from the existing trained checkpoint.
- Real MCP client smoke using the locally cached checkpoint and an in-memory vector store, with `dl_batch_size=1`, scored two chunks in request order. Response status `ready`; relevance probabilities were `0.994798` and `0.000506`; credibility scores were null because the model has no supervised credibility head. No network access was needed.
- Full DL-extra suite: `.tools/uv/uv.exe run --locked --extra dev --extra dl pytest` → 251 passed in 29.76s. Ruff → clean; MyPy → no issues in 53 source files; `git diff --check` → passed (Git emitted only LF-to-CRLF notices).
Files: `src/ara/dl/export.py`, `src/ara/mcp_servers/dl_model_server.py`, config/env files, `.gitignore`, and exporter/MCP/config/stdio tests. The exported bundle is ignored and reproducible from the locally trained checkpoint.
Notes: `ara-dl-model-mcp` remains available without importing PyTorch/Transformers at startup; model weights load only when scoring and a valid exported bundle exists. Source/test commit: `23a58b3`.

### 2026-10-26 — P5.7 — Integrate the DL scorer into researcher ranking
Done: Added `dl.use_scorer` / `ARA_DL_USE_SCORER` (default false). When enabled, the researcher calls `dl-model.score_chunks` through MCP after local retrieval, validates status, probabilities, unique IDs and exact candidate coverage, then stable-sorts evidence while preserving IDs/provenance. Not-ready, MCP errors, or malformed responses fall back to original retrieval order; score calls count against the per-run tool budget and are traced. Added validation/fallback and controlled A/B tests plus a real-model MCP SDK demo. Logged ADR-036.
Evidence: `$env:UV_SYSTEM_CERTS='true'; $env:UV_CACHE_DIR='.tools/uv-cache'; $env:UV_PROJECT_ENVIRONMENT='.tools/dl-venv'; $env:HF_HUB_OFFLINE='1'; .tools/uv/uv.exe run --locked --extra dev --extra dl python scripts/dl_researcher_ab_demo.py` → baseline ranked `chunk:gold` at 2 with MRR `0.5000` (1 MCP call); scorer-enabled ranked it at 1 with MRR `1.0000` (2 MCP calls), scorer trace `status=ready; scored=2; evidence_reordered=true`. Artifacts: `outputs/dl_researcher_ab.json` and `.md`. This uses one synthetic two-passage fixture and is not a statistical quality evaluation.
- Full suite: `.tools/uv/uv.exe run --locked --extra dev --extra dl pytest` → 255 passed in 35.68s; Ruff clean; MyPy → no issues in 54 source files; `git diff --check` passed (only LF-to-CRLF notices).
Files: `src/ara/agents/researcher.py`, config/env files, `tests/test_researcher.py`, `tests/test_config.py`, `scripts/dl_researcher_ab_demo.py`, and the two A/B outputs.
Notes: Feature is opt-in because consumers must connect the named `dl-model` MCP server and export the trained bundle first. Source/test/demo commit: `ba8a332`.

### 2026-10-26 — P5.8 — Document the reranker model card
Done: Added `docs/model_card.md` with pinned model revisions, intended use, data sources/licenses and document-disjoint split counts, training setup and losses, held-out baseline/ablation metrics, all four observed first-rank failures, the P5.7 integration fixture, reproduction commands, and limitations. The card distinguishes retrieval relevance from support/contradiction and states that sigmoid scores are uncalibrated ranking scores. No new ADR was needed because this task records already measured results and decisions.
Evidence: Cross-checked the card against `outputs/dl_training_metrics.json`, `outputs/dl_training_metrics_random_negatives.json`, `outputs/dl_evaluation_metrics.json`, `outputs/dl_error_analysis.json`, `outputs/dl_researcher_ab.json`, `data/dl_data/SOURCES.md`, and the P5.3–P5.7 entries above. `.tools/uv/uv.exe run --locked --extra dev --extra dl pytest` → 255 passed in 30.74s; Ruff → clean; MyPy → no issues in 54 source files; `git diff --check` → passed.
Files: `docs/model_card.md` and state files. Model card commit: `c55b028`.
Notes: Evaluation remains a 30-query internal SciFact split, not the official test set; differences are descriptive without confidence intervals/significance tests. The four available first-rank failures are all documented; no successful queries were added to reach 20.

### 2026-10-26 — P6.1 — Generate and render report diagrams
Done: Added `ara.generative.diagrams` with a Pydantic response schema, untrusted-report prompt framing, a constrained Mermaid `flowchart TD` grammar, validation of node/edge structure and acyclicity, up to two syntax-correction retries, conversion to controlled DOT for optional Graphviz rendering, a deterministic standard-library SVG fallback, SVG validation, and atomic output writes. Added 11 focused tests for valid output, syntax retry/cap, injection framing, graph validation, output writing, Graphviz selection/fallback, and invalid settings. Logged ADR-037.
Evidence: `Get-Command dot,mmdc,node,npm` → all not found. `.tools/uv/uv.exe run --locked --extra dev --extra dl pytest tests/test_diagrams.py` → 11 passed; full `.tools/uv/uv.exe run --locked --extra dev --extra dl pytest` → 266 passed in 35.52s; Ruff → clean; MyPy → no issues in 56 source files; `git diff --check` → passed. The full test rendered and parsed an SVG with the built-in renderer. Live Ollama generation and rendering with a real Graphviz executable are NOT RUN.
Files: `src/ara/generative/__init__.py`, `src/ara/generative/diagrams.py`, `tests/test_diagrams.py`, and state files.
Notes: Only the explicitly supported Mermaid subset is accepted; unsupported syntax is sent back through bounded retries. The Graphviz adapter runs only on validated graphs compiled to internally generated DOT.

### 2026-10-26 — P6.2 — Generate narration and synthesize local audio
Done: Added Pydantic-validated 170–260 word report narration with untrusted-data framing, citation-token removal, and bounded structured-output retries. Added lazy Piper synthesis, WAV validation and atomic publication, and explicit voice download from pinned Hugging Face revision. Added TTS config/environment controls, an optional `tts` dependency extra, `make tts-model`/`make tts-smoke`, and a reproducible controlled synthesis script. Logged ADR-038.
Evidence:
- `.tools/uv/uv.exe sync --locked --extra dev --extra dl --extra tts` → clean `.tools/tts-venv` installed Piper `1.8.0`, ONNX Runtime `1.31.0`, Hugging Face Hub `0.36.2`, and truststore `0.10.5`.
- `.tools/uv/uv.exe run --locked --extra dev --extra dl --extra tts python -m ara.generative.tts --download-voice` → downloaded `en_US-sam-medium` at revision `b145f2ac26522d6a2ccde0164b7b0e48b1e3199c`; model size 62,950,044 bytes and JSON config 5,040 bytes. Files are ignored under `models/tts/`.
- `.tools/uv/uv.exe run --locked --extra dev --extra dl --extra tts python scripts/tts_synthesis_smoke.py` → wrote `outputs/generated/p6_2_voice_smoke.wav`; last run: 185 words, 68.79 seconds, 22,050 Hz, mono, 3,033,644 bytes. This uses a controlled transcript derived from the reranker model card, not a live LLM response. Live narration-script generation is NOT RUN because Ollama is unavailable under ENV-002.
- `.tools/uv/uv.exe run --locked --extra dev --extra dl --extra tts pytest` → 279 passed in 38.82s; Ruff → clean; MyPy → no issues in 58 source files; `git diff --check` → passed.
Files: `src/ara/generative/tts.py`, `scripts/tts_synthesis_smoke.py`, `tests/test_tts.py`, config, `.env.example`, `.gitignore`, `Makefile`, `pyproject.toml`, `uv.lock`, and state files.
Notes: GNU Make is unavailable on this host; the equivalent module and script commands above were run directly. Piper is an optional GPL-3.0-or-later package; voice files are not committed.

### 2026-10-26 - P6.3 - Build cited Markdown, HTML, and PDF reports
Done: Added `build_report()` with deterministic citation validation, references derived from cited evidence, relative diagram/WAV assets, Markdown and HTML outputs, and an A4 PDF with SVG figures, footer, and page numbering. Disabled raw HTML rendering and rejected unsafe SVG elements, event handlers, external URLs, external stylesheets, and CSS imports. Added 10 focused tests. Logged ADR-039.
Evidence: `.tools/reports-venv/Scripts/python.exe -m pytest -q` -> 289 passed in 72.30s. Ruff -> clean. MyPy -> no issues in 59 source files. `git diff --check` -> passed (Git reported only LF-to-CRLF notices). A local demo bundle at `outputs/generated/p6_3_demo/reranker-evaluation.pdf` is 63,671 bytes and contains one page; PDFium rendered it at 1.5x to `rendered/page-1.png` (118,959 bytes), which was visually inspected. Citation text, references, diagram, audio link, and footer were visible. Live local-LLM report generation remains NOT RUN because Ollama is unavailable under ENV-002.
Files: `src/ara/generative/report_builder.py`, `tests/test_report_builder.py`, `pyproject.toml`, `uv.lock`, and state files. Source commit: `4079d02`.
Notes: The demo uses two curated excerpts from `docs/model_card.md` and the controlled narration WAV from P6.2; it verifies the assembly path, not the complete live agent workflow. The generated bundle and QA PNG are ignored under `outputs/generated/`.

### 2026-10-26 - P6.4 - Defer Stable Diffusion stretch
Done: Marked the optional illustration flag dropped with reason. The host is CPU-only (ENVIRONMENT.md), and diagram rendering plus local narration already implement the required generative layer. Logged ADR-040.
Evidence: Hardware probe in ENVIRONMENT.md records no supported CUDA/MPS accelerator; P6.1 verified Mermaid-to-SVG and P6.2 verified local Piper WAV synthesis. No diffusion model was downloaded or run.
Files: `docs/state/TODO.md`, `docs/state/DECISIONS.md`, `docs/state/PROGRESS.md`, `docs/state/HANDOFF.md`, and `docs/state/SESSIONS.md`.
Notes: Reopen only after a pinned model/license review and a measured run on available hardware.

### 2026-10-26 - P7.1 - Polish the CLI and Makefile targets
Done: Added `ara serve-mcp --server`, `ara run --topic` with research/report stopping points and bounded revision count, and `ara train`/`ara eval` argument forwarding to the existing DL entry points. Kept `ask` and `ingest`. Updated locked Makefile commands, added independent MCP-server targets and argument passthrough, and documented invocation in README. Logged ADR-041.
Evidence: `.tools/reports-venv/Scripts/python.exe -m pytest tests/test_cli.py -q` -> 7 passed. Full suite -> 293 passed in 62.27s. Ruff -> clean; MyPy -> no issues in 59 source files; `git diff --check` -> passed. `.tools/reports-venv/Scripts/ara.exe --help` listed the new commands; `python -m ara.cli eval --help` and `train --help` showed delegated module flags. GNU Make and a bundled Make executable were NOT FOUND, so Make targets could not be invoked here.
Files: `src/ara/cli.py`, `tests/test_cli.py`, `Makefile`, `README.md`, and state files. Source commit: `6b89e02`.
Notes: Live `ara run` was not executed because Ollama is unavailable under ENV-002. `ara eval` requires the prepared SciFact split and model weights; its default also trains the random-negative control.

### 2026-10-26 - P7.2 - Document architecture, usage, results, and limits
Done: Replaced the brief README with a Mermaid system diagram, locked setup/CLI/MCP instructions, report output layout, measured DL results, an explicitly NOT RUN RAG table, clearly labeled scripted demos, verification status, licenses/data links, and troubleshooting. Linked the configured Ollama models to official library pages and verified the EmbeddingGemma minimum version. Logged ADR-042.
Evidence: A local-link/anchor check resolved all 27 Markdown links. The README's 12 DL metric cells matched the four-system `outputs/dl_evaluation_metrics.json` source. `git diff --check` passed (only LF-to-CRLF notice). No source code changed, so the P7.1 full suite result remains 293 passed; tests were not rerun for this documentation-only task. RAG metric rows remain NOT RUN per `docs/evaluation.md`.
Files: `README.md` and state files. README commit: `f9c6a29`.
Notes: Official Ollama references: https://ollama.com/library/qwen2.5 and https://ollama.com/library/embeddinggemma. Live topic runs and the four-way RAG evaluation remain unverified under ENV-002.

### 2026-10-26 - P7.3 - Document architecture and design trade-offs
Done: Added a detailed architecture/data-flow document and an interview-defensible design decision guide covering local models, BM25+dense RRF, MCP, typed agents/citations, the MiniLM ranker, generated outputs, measured results, trade-offs, limits, and next steps. Linked both documents from README.
Evidence: Documentation QA resolved 43 Markdown links/anchors and balanced code fences; all 12 DL metric cells matched `outputs/dl_evaluation_metrics.json`. `.tools/reports-venv/Scripts/python.exe -m pytest -q` -> 293 passed in 37.84s; Ruff -> clean; MyPy -> no issues in 59 source files; `git diff --check` -> passed. Mermaid CLI/Node remain unavailable, so the diagrams were reviewed as Mermaid source but not rendered by an external CLI.
Files: `docs/architecture.md`, `docs/design_decisions.md`, `README.md`, and state files. Source commit: `8182727`.
Notes: RAG's 52-question four-way evaluation remains NOT RUN; the design document reports that gap explicitly and separates measured SciFact reranker results from scripted wiring demonstrations.

### 2026-10-26 - P7.4 - Build three complete example report bundles
Done: Added a deterministic generator that loads three original sample-corpus notes, chunks them with the production loader/chunker and configured settings, validates all report claims against real chunk IDs, and produces Markdown, HTML, PDF, constrained Mermaid/SVG diagrams, evidence JSON, and Piper narration WAVs. Added a bundle guide and README links. Kept PDF diagram/reference headings with their content after visual QA identified page-split issues; logged ADR-043.
Evidence: `.tools/uv/uv.exe run --locked --extra dev --extra dl --extra tts python scripts/generate_example_reports.py` -> generated 3 bundles and validated 4 unique citation IDs; `--validate-only` -> all 3 reports and assets valid. PDFium QA rendered six report pages; all PDFs were visually inspected and each is 2 pages. Narration duration in the PDFs: 71-73 seconds. Full pytest -> 295 passed in 62.19s; final focused report tests -> 12 passed in 3.54s; Ruff -> clean; MyPy -> no issues in 61 source files; `git diff --check` -> passed. Live Ollama generation is explicitly not claimed: diagrams are supplied through a deterministic client stub to the production Mermaid validator/renderer, and narration scripts are curated before local Piper synthesis.
Files: `src/ara/generative/example_reports.py`, `src/ara/generative/report_builder.py`, `scripts/generate_example_reports.py`, `tests/test_example_reports.py`, `tests/test_report_builder.py`, `outputs/examples/`, README and architecture/design docs. Source commit: `e225232`.
Notes: `outputs/examples/README.md` documents the rebuild command and CC BY 4.0 attribution. The 900-character chunking policy yields two evidence chunks for the prompt-injection note; both IDs appear in the claims and are retained in `evidence.json`. GNU Make/Ollama remain unavailable under ENV-002.

### 2026-10-26 - P7.5 - Probe the fresh-clone regression
Done: Created an ignored local shared clone at `.tools/p7_5_clone`, synced its fresh virtual environment from `uv.lock`, and exercised the CLI help, ingestion, and research entry points. The environment setup and parser path work, but the required end-to-end gate is blocked by the host prerequisites.
Evidence: `git clone --shared --local . .tools/p7_5_clone` -> clone created. In the clone, `.tools/uv/uv.exe sync --locked --extra dev --extra dl --extra tts` -> installed 137 packages; `.tools/uv/uv.exe run --locked ara --help` -> listed all six CLI commands. `ara ingest` -> loaded 21 source documents, then `httpx.ConnectError [WinError 10061]` for `localhost:11434` during embedding. `ara run --topic "Grid-scale battery storage" --until research` -> same refused connection during the first chat request. `Get-Command make,ollama` -> neither command found. The full regression is NOT RUN to completion; no output report is claimed. P7.5 remains `[!]` under ENV-002.
Files: `docs/state/TODO.md`, `docs/state/BLOCKERS.md`, `docs/state/ENVIRONMENT.md`, and state files.
Notes: The fresh clone also omits ignored voice/model weights. README documents the required Ollama model pulls and Piper voice download; those need to be present before the full report command can produce audio.

### 2026-10-26 - P7.6 - Defer optional report-style LoRA
Done: Dropped the stretch task for this pass under ADR-044. The core report acceptance path does not require LoRA; no adapter benefit is claimed without a pinned base model and measured before/after comparison.
Evidence: `docs/state/ENVIRONMENT.md` records CPU-only hardware; the configured Ollama chat model is not downloaded or running. No adapter was trained or evaluated.
Files: `docs/state/TODO.md`, `docs/state/DECISIONS.md`, `docs/state/PROGRESS.md`, and state files.

### 2026-10-26 - P7.7 - Audit final acceptance checklist
Done: Compared each final checklist item against committed artifacts and recorded commands. P7.7 audit is complete; the project is NOT marked complete because the full live report path, four-way RAG metrics, and 20-case failure review remain open.
Evidence: The earlier fresh-clone uv sync and `ara --help` succeeded; its ingest/research probes failed before Ollama was installed. Current-host GNU Make/Ollama setup and ingest now pass, and a live eight-task research phase added six evidence chunks. The writer's first structured draft failed schema validation after about 200 seconds; the retry timed out at 300 seconds. The last full project suite was 295 passed in 62.19s; Ruff passed; MyPy reported no issues in 61 source files. The report examples' deterministic citation validator resolves four IDs across three bundles, and all six PDF pages were visually reviewed. Only four first-rank failures appeared in the 30-query internal SciFact test split; all four are reviewed, but the specified 20-case failure analysis was not achieved.
Files: `docs/state/PROGRESS.md`, `docs/state/TODO.md`, `docs/state/BLOCKERS.md`, `docs/state/ENVIRONMENT.md`, and `docs/state/HANDOFF.md`.

#### Final Acceptance Checklist status
- [!] Fresh environment: `make setup && make ingest && make run TOPIC="..."` produces MD/HTML/PDF/diagrams/audio - Make setup and ingestion pass in the current checkout, but a clean clone at the current commit has not been run and the CPU writer retry exceeded 300 seconds before report assembly.
- [!] Dense/BM25/hybrid/hybrid+rerank evaluation table - 52-question protocol exists; real four-system metrics remain NOT RUN.
- [x] Three MCP servers independently verified over stdio with the official SDK client; Claude Desktop UI not launched (`docs/stdio_verification.md`).
- [x] Revision loop measured on three controlled topics; each scripted case moved from one unsupported claim to zero. Live-model quality effect remains NOT RUN.
- [x] Custom DL model trained and compared with baselines; model card and controlled researcher A/B are present. Results are descriptive on an internal 30-query SciFact split.
- [!] Phase 5 error review required 20 failure cases; only four first-rank errors existed in the internal test split, and all four were reviewed.
- [x] Every claim in the three checked-in example reports has a validated source chunk citation; all four cited IDs resolve.
- [x] Prompt-injection and failure-mode tests are in the suite; the last full run passed 295 tests.
- [x] `make test` and Ruff - `make test UV=.tools/uv/uv.exe` passed 295 tests in 60.71s; `make lint UV=.tools/uv/uv.exe` reported all Ruff checks passed.
- [x] README, `docs/design_decisions.md`, and `docs/architecture.md` are complete with Mermaid diagrams and documented limits.
- [!] State files are current, but `HANDOFF.md` cannot say PROJECT COMPLETE while the live-model, RAG evaluation, error-review, and P7.5 gates remain open.

Project status: incomplete pending RUN-001, the four-way RAG evaluation, and a larger held-out error set. Do not replace any `NOT RUN` result with a success claim until the required full report and evaluation runs are recorded.

### 2026-10-26 - P7.5 follow-up - Install local prerequisites and preserve tool-call history
Done: Installed GNU Make 4.4.1 through MSYS2 and Ollama 0.40.11; pulled the configured Qwen2.5 and EmbeddingGemma models; added their executable directories to the current user's PATH. Fixed the researcher conversation loop to retain assistant tool calls and pair MCP results with bounded, explicitly untrusted Ollama tool messages. Strengthened the prompt so web snippets are leads rather than report evidence. Logged ADR-045.
Evidence: `make setup UV=.tools/uv/uv.exe` -> locked sync resolved 153 packages successfully. `make ingest UV=.tools/uv/uv.exe` -> loaded 21 documents and indexed 33 chunks; both embedding requests returned HTTP 200. `ollama list` -> `qwen2.5:1.5b` and `embeddinggemma:latest`; `GET http://localhost:11434/api/version` -> `0.40.11`. Focused researcher/client tests -> 25 passed; full pytest -> 295 passed in 39.17s; Ruff -> clean; MyPy -> no issues in 61 source files. Exact Make targets: `make test UV=.tools/uv/uv.exe` -> 295 passed in 60.71s; `make lint UV=.tools/uv/uv.exe` -> all checks passed. A live `make run` research phase completed 8/8 tasks and added 6 evidence chunks; the first writer response failed schema validation and the retry timed out after 300s. No complete live report bundle is claimed. Under the unprivileged managed process, web-search TLS could not read the Windows certificate store; the verified-certificate retry reached search providers successfully.
Files: `src/ara/agents/researcher.py`, `src/ara/agents/prompts/researcher.py`, `src/ara/llm/client.py`, `tests/test_researcher.py`, `README.md`, and `docs/state/*`.
Notes: ENV-002 is resolved for the current host. P7.5 remains in progress under RUN-001; the four-way RAG evaluation and required 20-case held-out review are still open.

### 2026-10-26 — P7.5 — Bound CPU writer output and citations
Done: Added configurable Ollama `num_predict` (default 768) and schema-constrained structured output. Reduced the report input to eight evidence items/10,000 characters, limited each report to one summary claim and at most one claim per section (180 characters each), constrained every claim to one ID present in the selected evidence, and reject incomplete claim sentences. Abstaining drafts discard any accompanying title or claims. Updated the writer prompt for partial evidence and the scripted LLM interfaces.
Evidence: `make test UV=.tools/uv/uv.exe` → 298 passed in 28.77s; `make lint UV=.tools/uv/uv.exe` → all checks passed; `.tools/uv/uv.exe run --locked mypy src/ara` → no issues in 55 source files. A direct live writer call over five retrieved chunks returned a valid abstention on the MCP topic; it did not produce the complete report bundle. The full live run remains NOT PASSED under RUN-001.
Files: `src/ara/config.py`, `src/ara/llm/client.py`, `src/ara/agents/writer.py`, `src/ara/agents/prompts/writer.py`, tests, `.env.example`, `config.yaml`, and state files.
Notes: D: has 147.9 GiB free; the checkout is approximately 6.57 GiB and the Ollama model store 1.50 GiB. The user asked to relocate the project, Ollama, and project runtime to D:; do that next before continuing P7.5.

### 2026-10-26 — ENV-005 — Relocate project and local runtime to D:
Done: Copied the complete checkout, including `.git`, ignored weights, Piper voice files, and virtual environments, to `D:\DL CP`; relocated Ollama 0.40.11, both models, user data, app data, MSYS2/Make, uv cache, and managed Python to D:. Updated user PATH, `OLLAMA_MODELS`, uv variables, and Ollama/MSYS2 shortcuts. Replaced old runtime paths with C: compatibility junctions; the OneDrive checkout removal follows after the state commit.
Evidence: D: project copy matched 175,002 files/6.568 GiB in the Robocopy verification (the locked disposable `.pytest_cache` was excluded and recreated on D:). `D:\msys64\usr\bin\make.exe --version` → GNU Make 4.4.1. Ollama `/api/version` → 0.40.11; `qwen2.5:1.5b` generated a response; `embeddinggemma:latest` returned a 768-dimensional embedding. `make ingest` → 21 sources/documents, 33 chunks, skipped as current. After the researcher change, `make test` → 299 passed in 30.46s, `make lint` → all checks passed, and `uv run --locked mypy src/ara` → no issues in 55 source files.
Files: User environment/shortcuts; `docs/state/ENVIRONMENT.md`, `docs/state/TODO.md`, and runtime locations on D:.
Notes: The sandbox denied pytest's default C: temp directory, so verification set the current process `TEMP`/`TMP` to `D:\DL CP\.tools\pytest-tmp`; those general Windows temp variables were not changed in the user profile. The old C: runtime payloads remain only in temporary migration backups until the final cleanup.

### 2026-10-26 — P7.5 — Ensure web-only research can recover local evidence
Done: Added one bounded MCP `search_knowledge_base` fallback when a task uses web search, adds no citable evidence, and has not already searched local documents. Added a trace marker and a regression test.
Evidence: `python -m pytest -q tests/test_researcher.py` → 20 passed; full `make test` → 299 passed in 30.46s; Ruff clean; MyPy clean in 55 files. The live RRF run gathered six local chunks across three tasks, but the writer request timed out after 300 seconds; the report bundle remains NOT RUN/NOT PASSED.
Files: `src/ara/agents/researcher.py`, `tests/test_researcher.py`, `docs/state/DECISIONS.md`, and `docs/state/BLOCKERS.md`.
Notes: Local evidence retrieval is fixed, but writer prompt/runtime bounds still need work for this CPU host. See RUN-001.

### 2026-10-26 — ENV-006 — Retire the duplicate OneDrive checkout
Status: BLOCKED after D: migration was committed and runtime data backups were removed.
Evidence: `Remove-Item -LiteralPath 'C:\Users\ketaki more\OneDrive\Documents\DL CP' -Recurse -Force` stopped at `.pytest_cache` with Access Denied. `icacls` on the parent reports an inherited `Everyone` deny for deleting children; `Get-Acl` on the cache returns unauthorized operation. All C: Ollama/MSYS2/uv compatibility junctions point to D:, and the D: checkout at commit `a9acee5` is clean and verified. No ACL changes were made.
Files: `docs/state/ENVIRONMENT.md`, `docs/state/TODO.md`, `docs/state/BLOCKERS.md`, and `docs/state/HANDOFF.md`.
Notes: The D: copy is canonical and usable; the C: OneDrive copy remains until that deny is resolved or the folder is removed through OneDrive itself.

### 2026-10-26 — P7.5 — Bound writer work for the CPU runtime
Done: Kept the 768-token shared LLM setting for planning/research; added a configurable 384-token writer cap; reduced the writer's default evidence context from eight items/10,000 characters to four items/3,600 characters.
Evidence: `make test` → 302 passed in 25.49s; `make lint` → all checks passed; `mypy src/ara` → no issues in 55 source files. Targeted writer/client/config regression tests → 28 passed. Live RRF rerun → NOT RUN yet; RUN-001 remains open pending the end-to-end output check.
Files: `config.yaml`, `.env.example`, `src/ara/config.py`, `src/ara/llm/client.py`, `src/ara/agents/writer.py`, `src/ara/cli.py`, tests, and state files.
Notes: The separate cap affects only the report writer; prompts remain evidence-only and citations remain schema-constrained. Two test doubles were updated to accept the optional cap.

### 2026-10-26 — P7.5 — Measure live writer output caps
Done: Ran two live RRF research/report attempts on D: with reduced writer evidence context and distinct writer output caps; both completed the research stage and reached the writer.
Evidence: `make run TOPIC="Explain reciprocal rank fusion and compare it with score-based fusion."` with `ARA_LLM_WRITER_NUM_PREDICT=384` → trace `ba7f2991d03d4a20aa2d4bd74062d81d`, three tasks completed, five evidence chunks, writer JSON truncated at 1,353 characters in all four attempts; no report artifacts. Same command with cap `640` → trace `7949dbe60cba4ecd8a4d0dd7afa6be78`, three tasks completed in 118 seconds, five chunks, incomplete claim sentences in all four attempts; no report artifacts.
Files: `traces/ba7f2991d03d4a20aa2d4bd74062d81d.jsonl`, `traces/7949dbe60cba4ecd8a4d0dd7afa6be78.jsonl`, `docs/state/BLOCKERS.md`, and `docs/state/TODO.md`.
Notes: Keep claim validation fail-closed; the next experiment raises only the writer output cap while retaining the reduced context.

### 2026-10-26 — P7.5 — Shorten writer claims after live validation failures
Done: Kept fail-closed sentence validation, limited each claim to 120 characters and 14 prompted words, and set the configurable writer-only output budget to 768 tokens. Updated the controlled revision example to satisfy the concise claim limit.
Evidence: `make test` → 303 passed in 25.30s; `make lint` → all checks passed; `mypy src/ara` → no issues in 55 source files. Targeted writer/config/client tests → 29 passed. Live 768-token run → NOT RUN yet.
Files: `src/ara/agents/writer.py`, `src/ara/agents/prompts/writer.py`, `src/ara/config.py`, `config.yaml`, `.env.example`, `scripts/offline_revision_demo.py`, writer/config tests, and state files.
Notes: ADR-050 supersedes ADR-049's 384-token writer default. No claims about live report quality are made until the next run returns a valid report bundle.

### 2026-10-26 — P7.5 — Tighten the writer claim bound after the 768-token run
Done: Kept a separate 768-token writer output cap and shortened the schema/prompt claim maximum to 80 characters/10 words. Updated controlled example summaries to remain within the shared claim validator.
Evidence: Live RRF run `e51717ee0a864ef695045fac2151705b` completed three research tasks in about 153 seconds and collected five local chunks. With the 768-token cap and previous 120-character schema, all four writer attempts produced claims without terminal punctuation and validation failed; no output bundle was emitted. After the change: `make test` → 303 passed in 24.18s; `make lint` → all checks passed; `mypy src/ara` → no issues in 55 source files. Live run with 80-character claims → NOT RUN.
Files: `src/ara/agents/writer.py`, `src/ara/agents/prompts/writer.py`, `scripts/offline_revision_demo.py`, tests, and state files.
Notes: ADR-051 supersedes ADR-050's 120-character/14-word limit. Keep sentence validation and citation checks fail-closed.

### 2026-10-26 — P7.5 — Make sentence punctuation a schema constraint
Done: Added a JSON Schema `pattern` and matching Pydantic `Field` constraint requiring claims to end in `.`, `!`, or `?`. The 80-character/10-word bound and 768-token writer budget remain.
Evidence: `make test` → 303 passed in 23.59s; `make lint` → all checks passed; `mypy src/ara` → no issues in 55 source files; focused writer/revision tests → 18 passed. Live test with the punctuation pattern → NOT RUN.
Files: `src/ara/agents/writer.py`, `tests/test_writer.py`, and state files.
Notes: ADR-052 records the change. Previous live failures show the model reaching the claim bound without punctuation; this pattern is exposed in its JSON Schema before the next run.

### 2026-10-26 — P7.5 — Validate the writer with schema-visible punctuation
Done: Increased the writer claim bound to 256 characters/30 words while keeping the 768-token cap, four-item/3,600-character context, and the JSON Schema terminal-punctuation pattern.
Evidence: A direct call to the configured Qwen model using two passages from `data/sample_corpus/04_reciprocal_rank_fusion.md`, `Writer(max_retries=0, num_predict=768)`, returned a five-section cited report with both known chunk IDs and no abstention in about 20 seconds. `make test` → 303 passed in 27.30s; `make lint` → all checks passed; `mypy src/ara` → no issues in 55 files; targeted writer/revision tests → 18 passed. Full MCP report bundle → NOT RUN yet.
Files: `src/ara/agents/writer.py`, `src/ara/agents/prompts/writer.py`, writer tests, and state files.
Notes: ADR-053 supersedes ADR-051's 80-character limit. The direct writer result demonstrates only the writer stage, not full pipeline acceptance.

### 2026-10-26 — P7.5 — Separate executive-summary claim bound
Done: Kept section claims at 256 characters/30 words, and added `WriterSummaryClaim` at 512 characters/50 words with the same citation and punctuation constraints. The full-run failure showed only the summary exceeded its cap.
Evidence: Full run `3c2fb03854514cc6bff9ef540a20663e` completed three research tasks in 129 seconds and stored five chunks; all four writer attempts failed because the summary exceeded 256 characters; no output bundle. A direct Qwen writer call over two real RRF corpus passages now returns a complete five-section report with valid citations to `chunk:live-rrf-1` and `chunk:live-rrf-2` in about 15 seconds. `make test` → 303 passed in 20.58s; `make lint` → all checks passed; `mypy src/ara` → no issues in 55 files; focused writer/revision tests → 28 passed.
Files: `src/ara/agents/writer.py`, writer prompt, `scripts/offline_revision_demo.py`, tests, and state files.
Notes: ADR-054 keeps the model-visible punctuation pattern from ADR-052 and splits the larger summary bound from section claims. The full end-to-end run remains unverified.

### 2026-10-26 — P7.5 — Recheck split summary schema
Done: Updated writer, revision tests, and controlled demo to use the summary-specific claim type while section claims remain constrained to their own schema.
Evidence: `make test` → 303 passed in 20.42s; `make lint` → all checks passed; `mypy src/ara` → no issues in 55 files. A real Qwen direct call returned a valid five-section report with both supplied citation IDs.
Files: Writer and revision modules/tests, offline demo, and project state files.
Notes: The full `ara run` report after the separate-summary fix remains the next P7.5 gate.

### 2026-10-26 — P7.5 — Keep report generation moving after Mermaid errors
Done: Retained constrained Mermaid validation and retries, then added a deterministic validated diagram from report headings when the model returns invalid syntax or cannot produce structured output. Diagram artifacts now identify whether their diagram came from the model or report structure.
Evidence: `pytest tests/test_diagrams.py` → 12 passed; full `pytest` → 304 passed in 22.04s; Ruff → all checks passed; MyPy → no issues in 55 source files. Run `b873b03a2c72427199eb6732c7925305` completed research/writing with five chunks but failed diagram validation after three attempts. Follow-up run `ffb3c61542014d55814699761c1abda8` stored five chunks; critic found four of five claims supported, but the revision writer abstained and produced only the abstention report bundle, so the diagram fallback was not reached.
Files: `src/ara/generative/diagrams.py`, `tests/test_diagrams.py`, `docs/state/TODO.md`, `docs/state/BLOCKERS.md`, and this state log.
Notes: ADR-055 records that the fallback is structural, not a model-inferred relationship diagram. RUN-001 remains open until a substantive cited bundle is inspected; next, keep supported claims when revision generation abstains.

### 2026-10-26 — P7.5 — Preserve supported claims on revision abstention
Done: Added a deterministic recovery path for revision abstentions. It removes only lines that exactly match critic findings marked unsupported, miscited, contradicted, or unclear, then keeps the draft only when a cited claim remains and every ID exists in the evidence store. Added a recovery trace event.
Evidence: Targeted `pytest tests/test_revision.py` → 11 passed; full `pytest` → 305 passed in 22.11s; Ruff → all checks passed; MyPy → no issues in 55 source files. The trigger was live run `ffb3c61542014d55814699761c1abda8`: four of five claims were supported, but the revision writer abstained. Recovery has not yet been exercised in a live run.
Files: `src/ara/agents/revision.py`, `tests/test_revision.py`, and project state files.
Notes: ADR-056 documents the conservative fallback. The next live run must verify the recovered draft and continue through diagrams, TTS, PDF, and citation validation.

### 2026-10-26 — P7.5 — Bound web-only researcher continuations
Done: When a web search adds no citable evidence and earlier tasks already populated the evidence store, the researcher now calls local RAG through MCP directly and completes that task without another model-selection request. The existing model-selected path remains for initial searches with no prior evidence.
Evidence: Researcher tests → 21 passed; full `pytest` → 306 passed in 21.07s; Ruff → all checks passed; MyPy → no issues in 55 source files. Live run `084e0be2b2a049e1998725436a71eaa7` retrieved five local chunks, then timed out during a later tool-selection request after web search; the new path has not yet been live-verified.
Files: `src/ara/agents/researcher.py`, `tests/test_researcher.py`, and project state files.
Notes: ADR-057 records the bounded local fallback. RUN-001 remains open pending a substantive complete report bundle.

### 2026-10-26 — P7.5 — Recover short report narration
Done: Kept the 170–260 word narration requirement and added a deterministic fallback that strips headings/citation IDs and expands only citation-grounded report sentences with neutral restatements when model narration fails validation. Reports without citations still fail closed.
Evidence: `pytest tests/test_tts.py` → 13 passed; full `pytest` → 307 passed in 29.00s; Ruff → all checks passed; MyPy → no issues in 55 source files. Live run `6f77b0bac8064a98a4e26ec746075863` completed research with five chunks, reduced critic unsupported claims `1 → 0`, and rendered the structural diagram fallback. Narration returned 90 words on all four attempts and failed; the new fallback has not yet been run live.
Files: `src/ara/generative/tts.py`, `tests/test_tts.py`, and project state files.
Notes: ADR-058 records that fallback speech repeats only report-backed content. RUN-001 remains open until the full cited MD/HTML/PDF/SVG/WAV bundle is inspected.

### 2026-10-26 — P7.5 — Inspect live bundle and keep tall diagram headings together
Done: Live run `cb9bbc9da4d9495eb76f87fe1543d78c` produced the full report bundle. Inspected citations/references, HTML/SVG/audio assets, WAV metadata, and rendered every PDF page. Fixed the stranded `Diagrams` heading by reserving PDF vertical space for figure overhead; rebuilt the same validated bundle and re-rendered it.
Evidence: `tests/test_report_builder.py` → 11 passed; full `pytest` → 308 passed in 24.57s; Ruff → all checks passed; MyPy → no issues in 55 source files. The complete live bundle has one inline citation ID matching one reference, a 73.28-second/22,050-Hz/mono narration WAV, and an SVG built from report headings after three invalid model Mermaid responses. PDF before fix: 4 pages, with the diagram heading alone on page 2; after fix: 3 pages, with heading and diagram together on page 2 and no clipped content on visual inspection.
Files: `src/ara/generative/report_builder.py`, `tests/test_report_builder.py`, `outputs/cb9bbc9da4d9495eb76f87fe1543d78c/`, and state files.
Notes: ADR-059 records the figure scaling rule. RUN-001 is resolved. CLONE-001 remains open until the fresh-clone `make setup && make ingest && make run` regression passes.

### 2026-10-26 — P7.5 — Pass the fresh-clone report regression
Done: Cloned the committed repository to `.tools/p7_5_clean`, installed its locked environment, ingested the corpus, and ran the full RRF report topic through `make run`. The clone generated Markdown, HTML, PDF, SVG, and WAV assets.
Evidence: `git clone --no-local "D:\DL CP" "D:\DL CP\.tools\p7_5_clean"` → clean clone at `0dfd734`; `make setup` → 137 locked packages installed; `make ingest` → 21 documents indexed into 33 chunks; `make "TOPIC=Explain reciprocal rank fusion and compare it with score-based fusion." run` → report written to `outputs/c34e48eb635b499d814eb3e507eb9a74/report.pdf`. Bundle validation → one inline citation ID equals the reference ID; PDF has three pages with the diagram heading and figure on the same page; WAV is 68.82 seconds, 22,050 Hz, mono. Trace shows the critic removed one unsupported claim, then reviewed four retained claims with zero unsupported.
Files: `.tools/p7_5_clean/outputs/c34e48eb635b499d814eb3e507eb9a74/` (ignored QA clone), `docs/state/BLOCKERS.md`, `docs/state/TODO.md`, and this state log.
Notes: The clone reused the running D: Ollama service/model store and the ignored Piper voice file; its `.venv` and retrieval indexes were fresh. CLONE-001 and P7.5 are resolved. P1.10 is now the next active evaluation task.

### 2026-10-26 — P1.10 — Measure all four RAG retrievers
Done: Added a resumable CPU-compatible retrieval runner and `ara rag-eval` / `make eval-rag` entry points without changing the existing DL `ara eval` command. The runner saves all four rankings after each query and rejects resume attempts with changed evaluation/model/index metadata.
Evidence: `make eval-rag ARGS=--fresh` → 52/52 queries evaluated over 33 chunks at candidate depth 20 and cutoff 5. Dense: recall@5 0.989, MRR 0.924, nDCG@5 0.923, candidate citation precision@5 0.204. BM25: 0.977, 0.943, 0.935, 0.200. Hybrid RRF: 0.989, 0.989, 0.971, 0.204. Hybrid RRF + MiniLM: 0.989, 1.000, 0.982, 0.204. `make eval-rag` → resumed all 52 saved queries without recomputation. Full `pytest` → 311 passed in 32.64s; Ruff → all checks passed; MyPy → no issues in 56 source files; `git diff --check` and local Markdown links in updated docs → passed.
Files: `src/ara/rag/evaluation_runner.py`, CLI/Make targets, focused tests, `outputs/rag_retrieval_evaluation/{metadata.json,predictions.jsonl,metrics.json,metrics.md}`, README, evaluation/design/architecture docs, and project state files.
Notes: ADR-060 records why citation precision is measured as gold evidence among retrieved top-k candidates; no LLM answers were generated, so answer-level citation accuracy, answer rate, and abstention remain unmeasured. RRF improved MRR on this fixed small corpus; the reranker added a small MRR/nDCG gain without changing recall or candidate citation precision. P1.10 is complete. Continue with live three-topic P4.5.

### 2026-10-27 - P4.5 - Measure the live critic loop across three topics
Done: Completed three full local-model report runs on distinct corpus topics and compared first and final critic unsupported-claim counts. The first run exposed and removed one unsupported claim; the other two were already clean and stopped without unnecessary rewrites. All three runs completed report assembly using the existing diagram and narration fallbacks where Qwen output failed validation.

| Topic | Run ID | First review | Final review | Result |
|---|---|---:|---:|---|
| Reciprocal rank fusion vs. score-based fusion | 6f77b0bac8064a98a4e26ec746075863 | 1 unsupported / 5 reviewed | 0 / 4 reviewed | One flagged claim removed; retained claims passed re-review |
| Candidate depth and reranking quality | cec627423c774dbd8ce56c67d9d6729d | 0 / 5 reviewed | 0 / 5 reviewed | Stopped clean on first review |
| BM25 and dense retrieval in hybrid RAG | 5976f89dcf85481c9437f78e88cf656b | 0 / 5 reviewed | 0 / 5 reviewed | Stopped clean on first review |

Evidence: All three runs used make TOPIC="..." run with D: Ollama qwen2.5:1.5b; each produced Markdown, HTML, PDF, SVG, and WAV. JSONL traces show an aggregate first-review count of 1 unsupported claim and a final count of 0; only the RRF case required a rewrite, while the other two met the clean-stop rule. make test and lint will be recorded with the next project-wide regression run.
Files: traces/6f77b0bac8064a98a4e26ec746075863.jsonl, traces/cec627423c774dbd8ce56c67d9d6729d.jsonl, traces/5976f89dcf85481c9437f78e88cf656b.jsonl, outputs/cec627423c774dbd8ce56c67d9d6729d/, outputs/5976f89dcf85481c9437f78e88cf656b/, and project state files.
Notes: This is a small three-topic live demonstration, not a broad accuracy estimate. The two zero-to-zero cases show clean stopping rather than critic-driven reduction. P5.5 remains open because the 30-query held-out SciFact test set produced only four top-rank failures; expand the held-out error review without document leakage before claiming the requested 20-case analysis.

### 2026-10-27 - P5.5 - Evaluate the reranker on an expanded held-out set
Done: Expanded the deterministic SciFact subset to all 693 eligible labeled train/dev claims, using evidence-document components and a 60/10/30 split (415 train, 70 validation, 208 internal test; zero document overlap). Retrained the fine-tuned and random-negative models using train/validation only and evaluated four ranking systems across all 208 test queries. The error artifact now contains 20 genuine first-rank failures, without adding successful cases.
Evidence:
- The ignored probe split and all seven regenerated tracked data files had identical SHA-256 hashes; metadata records 693 claims and no document overlap.
- Expanded fine-tuning: 934 training examples, 155 validation examples, best epoch 1 with validation BCE 0.407094; early stopped after epoch 3. Random-negative control: same row counts, best epoch 2 with validation BCE 0.019427.
- make ARGS=--data-dir data/dl_data/scifact_subset eval -> 208 queries; candidate recall@20 0.9981; mean RRF candidate union 33.38. RRF: recall@10 0.9923, MRR 0.9027, nDCG@10 0.9236. Generic: 0.9933, 0.9282, 0.9433. Fine-tuned: 0.9933, 0.9390, 0.9504. Random-negative: 0.9933, 0.9424, 0.9530.
- Fine-tuning improved MRR/nDCG over RRF and the generic model, while the random-negative control exceeded it by 0.0035 MRR and 0.0026 nDCG@10. No confidence intervals or statistical tests were run.
- Error review: 20/208 first-rank failures; 12 relevant documents ranked second, 3 third, 2 fourth, and one each seventh, tenth, and sixteenth. Candidate recall was complete in 19 cases; one case had 0.60. Most errors were close-topic distractors above present evidence.
- Focused config/split tests -> 9 passed. Full pytest -> 311 passed in 45.34s. Ruff -> all checks passed. MyPy -> no issues in 56 files. git diff --check -> passed.
Files: src/ara/dl/public_data.py, src/ara/config.py, config.yaml, tests/test_public_data.py, tests/test_config.py, data/dl_data/scifact_subset/, data/dl_data/SOURCES.md, outputs/dl_training_metrics*, outputs/dl_evaluation_metrics*, outputs/dl_error_analysis.json, docs/model_card.md, docs/design_decisions.md, README.md, and project state files.
Notes: The internal split excludes the official SciFact test claims. The random-negative result means hard-negative training did not win its ablation; report that limitation directly. ADR-061 supersedes the original 200-claim / 30-query evaluation sizing decision while preserving the document-disjoint protocol.
