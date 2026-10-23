# Decisions

## ADR-001: Use a local-first Ollama-compatible LLM endpoint [ASSUMPTION] Date: 2026-10-22 Status: active
Context: The specification requires a free, local default and an interchangeable model client.
Options considered: Ollama HTTP API; direct Transformers integration; paid hosted API.
Decision: Start with Ollama's local HTTP API behind `llm/client.py`; keep model/base URL configurable. No paid API is required.
Consequences / how to reverse: The service must be installed separately and model smoke tests need a running local model. A different backend can be added behind the same client interface and logged as a superseding ADR.

## ADR-002: Default to a small Qwen model pending hardware detection [ASSUMPTION] Date: 2026-10-22 Status: superseded by ADR-015
Context: No Python, Ollama, GPU query access, or RAM query access is available in the current environment; the project must remain laptop-CPU-demoable.
Options considered: Defer model selection; default to a small CPU-feasible Qwen model; choose a larger model without confirmed hardware.
Decision: Set `qwen2.5:1.5b` as the configurable initial default. This is provisional, not evidence that it has been downloaded or run.
Consequences / how to reverse: Revisit after hardware access and model availability are checked. Record the final size/backend choice with measured environment evidence.

## ADR-015: Use the 1.5B Qwen model on the detected CPU-only host [DECISION] Date: 2026-10-23 Status: active
Context: P0.6 hardware probing now reports 18 logical processors and 15.52 GiB RAM, while finding no supported CUDA/MPS accelerator. Exact display hardware and VRAM remain unknown.
Options considered: Keep the provisional 1.5B model; move to 3B using system RAM capacity; choose a GPU-oriented model without a detected supported accelerator.
Decision: Keep `qwen2.5:1.5b` as the CPU default to stay laptop-demoable. Keep `embeddinggemma` configurable for embeddings. Neither model is installed or measured; the recommendation reflects the available CPU-only probe and project policy, not observed inference performance. This supersedes ADR-002.
Consequences / how to reverse: Re-run the hardware probe after adding an accessible GPU/runtime or on another host, then select and benchmark a model suited to the detected accelerator and RAM.

## ADR-003: Use original CC BY 4.0 notes as the sample corpus [ASSUMPTION] Date: 2026-10-22 Status: active
Context: P0.8 requires a small open-licensed corpus on one niche topic, and the constrained environment cannot download full upstream documents reliably.
Options considered: Bundle upstream docs verbatim; use a third-party dataset; write original concise notes with traceable references.
Decision: Write 19 original notes about local retrieval and evidence grounding, license those notes CC BY 4.0, and record the official references and upstream project licenses in `data/sample_corpus/SOURCES.md`. Do not redistribute upstream page text.
Consequences / how to reverse: The corpus is a curated instructional fixture rather than a snapshot of complete upstream documents. To replace it, add a source with explicit redistribution terms and update the manifest and license notice.

## ADR-004: Use Ollama's local embedding endpoint with a configurable model [ASSUMPTION] Date: 2026-10-22 Status: active
Context: Phase 1 needs batched dense embeddings that run locally and can be cached without a remote API.
Options considered: Sentence Transformers in-process; Ollama `/api/embed`; hosted embedding API.
Decision: Use Ollama `/api/embed` behind `OllamaEmbeddings`, default the configurable model name to `embeddinggemma`, and cache vectors by model plus text hash in SQLite. No source text is stored in the embedding cache.
Consequences / how to reverse: Ollama and the selected model must be installed for real embedding runs. A Sentence Transformers implementation can be added behind the same retriever-facing interface if local endpoint constraints or evaluations justify it.

## ADR-005: Use persistent Chroma with cosine distance behind a vector-store protocol [ASSUMPTION] Date: 2026-10-22 Status: active
Context: The RAG layer needs persistent dense retrieval and a replaceable backend; tests should not require a Chroma database or server.
Options considered: Couple retrieval directly to Chroma; use an in-memory-only index; define a protocol with a persistent local adapter.
Decision: Define a small `VectorStore` protocol, use Chroma's persistent client with cosine space for the default adapter, and retain an in-memory cosine implementation for small tests. Keep the Qdrant class as an explicit unimplemented placeholder.
Consequences / how to reverse: Chroma is the default storage dependency and local persistence format; retrieval callers can switch implementations through the protocol if later evaluations justify a different store.

## ADR-006: Implement BM25 locally and persist its source chunks as versioned JSON [ASSUMPTION] Date: 2026-10-22 Status: active
Context: Phase 1 needs a portable persisted lexical index, while package-index access is currently unavailable.
Options considered: Add a third-party BM25 package; store only serialized posting lists; persist chunks and rebuild lexical statistics on load.
Decision: Implement the standard BM25 scoring formula with case-folded Unicode word tokens, and save chunk records plus `k1`/`b` parameters in a versioned JSON file using an atomic same-directory rename. Rebuild postings and term statistics when loading.
Consequences / how to reverse: No extra runtime dependency is needed, and the persisted format is inspectable. Large corpora will use more disk and load time than compact posting-list serialization; retrieval evaluation can justify a later format change.

## ADR-007: Fuse dense and lexical retrieval with weighted RRF [ASSUMPTION] Date: 2026-10-22 Status: active
Context: Dense cosine scores and BM25 scores have different scales, so direct addition needs calibration.
Options considered: Normalize and add raw scores; train a fusion model; fuse the candidate ranks without score calibration.
Decision: Use weighted reciprocal-rank fusion with equal default weights and `k=60`; retain each source rank and score for evaluation. The original RRF paper defines the reciprocal-rank sum and reports fixing `k=60` in its pilot investigation ([Cormack, Clarke, and Büttcher, 2009](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf)). Treat equal weights and the constant as a baseline to evaluate on ARA's own corpus.
Consequences / how to reverse: Fusion does not require dense and lexical scores to share a scale. The chosen weights and candidate depth can be tuned or replaced after retrieval metrics are collected.

## ADR-008: Use a lazy optional Sentence Transformers CrossEncoder reranker [ASSUMPTION] Date: 2026-10-22 Status: active
Context: Hybrid retrieval needs a second-stage relevance scorer for a bounded candidate list, but model loading must not block imports or require the extra in every environment.
Options considered: Use the chat LLM to judge candidates; add a CrossEncoder as a required dependency; make a CrossEncoder adapter optional and lazy.
Decision: Add `CrossEncoderReranker` using Sentence Transformers' `CrossEncoder.predict`, keep the `sentence-transformers` package in an optional `rerank` extra, and defer library/model loading until a non-empty rerank request. Default to the configurable `cross-encoder/ms-marco-MiniLM-L-6-v2` model. Sentence Transformers documents CrossEncoders as a second-stage reranker over a limited candidate set ([quickstart](https://sbert.net/docs/quickstart.html), [retrieve and rerank guide](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)).
Consequences / how to reverse: The base install stays smaller and imports remain offline-safe; first scoring requires the optional package and accessible local weights. A different compatible scorer can be injected through the same `predict` contract.

## ADR-009: Require citation-bearing atomic claims and a configurable RRF evidence floor [ASSUMPTION] Date: 2026-10-22 Status: active
Context: Fluent answers can state unsupported facts even when retrieval returned irrelevant candidates; citation IDs also need deterministic validation.
Options considered: Ask the model for a free-form answer and parse inline citations; require structured atomic claims with evidence IDs; always answer and rely on a later critic.
Decision: Generate validated structured claims, append citations in code, reject any claim citing an ID outside the retrieved candidate set, and abstain before generation when no candidate meets the score floor. Use a configurable default floor of `0.012` with equal-weight RRF `k=60`; a one-source rank-1 contribution is `1/61` and passes, while sufficiently low-ranked single-source results can be filtered. The floor is a baseline heuristic to tune against evaluation data, not a measured relevance guarantee.
Consequences / how to reverse: Output has machine-checkable citations and fails closed on unknown IDs. A poor score threshold can create false abstentions or admit weak evidence; tune it and report the trade-off during retrieval evaluation.

## ADR-010: Pin evaluation gold IDs to the default chunking of the sample corpus [ASSUMPTION] Date: 2026-10-22 Status: active
Context: Retrieval metrics require stable relevance labels that point to real indexed passages.
Options considered: Store document-level answers only; manually write opaque chunk IDs; derive chunk IDs from the checked-in notes using the production chunker.
Decision: Store 52 questions as JSONL and derive every answerable gold ID from `data/sample_corpus` with the current default chunk size (900) and overlap (120). Include 34 factoid, 10 multi-hop, and 8 unanswerable queries; validate IDs against recomputed corpus chunks. Treat the binary labels as a baseline set, not a broad benchmark.
Consequences / how to reverse: Corpus edits or chunking/source-name changes require regenerating and reviewing the gold IDs. The small, single-topic sample supports project comparisons but does not establish general retrieval quality.

## ADR-011: Use macro answerable-query retrieval metrics and micro citation precision [ASSUMPTION] Date: 2026-10-22 Status: active
Context: Evaluation needs consistent treatment of answerable and unanswerable questions, retrieval rankings, and generated citations.
Options considered: Include unanswerable questions as retrieval misses; exclude them from retrieval metrics and score abstention separately; macro- or micro-average the retrieval measures.
Decision: Compute recall@k, MRR over the full returned ranking, and binary nDCG@k as macro averages over answerable queries only. Compute citation precision as a micro average over emitted citations across all queries, counting citations on unanswerable cases as incorrect. Report answerable response rate and unanswerable abstention rate separately. Missing predictions count as empty rankings and no citations.
Consequences / how to reverse: Metric definitions are explicit and repeatable across retrievers. The corpus has binary relevance labels, so graded relevance and broader confidence intervals require additional labels and queries.

## ADR-012: Reconcile ingestion from a content manifest and stable chunk IDs [DECISION] Date: 2026-10-22 Status: active
Context: Repeated ingestion must avoid unnecessary embedding work while keeping the dense and lexical indexes aligned when sources, chunk settings, or the embedding model change.
Options considered: Rebuild every run; trust only the manifest; compare the manifest with IDs in both indexes and reconcile stale dense IDs.
Decision: Persist a versioned manifest with source content hashes, chunk settings, embedding model, and sorted active chunk IDs. Skip only when the manifest and both indexes match. Otherwise upsert current chunks, remove stale dense IDs, rebuild BM25, and save BM25 and manifest files with atomic replacement. Model changes force vector regeneration and replacement. Keep cross-encoder reranking opt-in at the CLI because its package and weights are optional.
Consequences / how to reverse: Stable chunk IDs make same-corpus upserts repeatable and ID reconciliation removes obsolete records. Real Chroma/Ollama behavior and dependency-backed tests still need verification when the environment is available.

## ADR-013: Keep shared MCP validation and error handling independent of the SDK [DECISION] Date: 2026-10-23 Status: active
Context: MCP servers need consistent argument checks, safe caller-facing failures, and useful logs, while package-index access is blocked and server-specific fields vary.
Options considered: Couple shared helpers to SDK response classes; rely on server handlers to validate ad hoc; provide small standard-library helpers and map their error payloads into SDK results at the server boundary.
Decision: Use standard-library validators for object keys, bounded text/integers/lists, a typed tool error carrying stable code/message/retryability, a sanitized generic error payload, and a call context that logs server/tool/duration without logging arguments. Keep SDK-specific protocol objects in each server adapter.
Consequences / how to reverse: Helpers can be smoke-checked without the SDK and keep user input out of logs. The MCP SDK adapter must translate these payloads into the protocol's tool result/error form and add any SDK-specific validation before release.

## ADR-014: Use the official MCP Python SDK v2 for the RAG stdio server [DECISION] Date: 2026-10-23 Status: active
Context: Phase 2 requires an independently runnable RAG MCP server and client-level protocol tests; the SDK's stable API changed after v1.
Options considered: Implement JSON-RPC and stdio manually; use the older SDK v1 API; depend on the current official SDK v2 high-level server and client.
Decision: Add `mcp>=2,<3`, build tools with `mcp.server.MCPServer`, use typed Pydantic input/output models, and test through the SDK's in-memory `Client(server)` transport. Expose the default stdio runner as `ara-rag-mcp`. Translate shared ARA tool errors into the SDK's `ToolError` so callers receive safe, actionable tool failures.
Consequences / how to reverse: The implementation follows the SDK's current stable v2 line and stays within the stated Python 3.11+ support. The dependency and protocol tests still need a successful package install and execution; before changing API lines, review the official [installation and migration documentation](https://py.sdk.modelcontextprotocol.io/get-started/installation/) and [client transport documentation](https://py.sdk.modelcontextprotocol.io/client/transports/).

## ADR-016: Use DDGS for free metasearch and return bounded untrusted web text [DECISION] Date: 2026-10-23 Status: active
Context: P2.3 needs free web search, citation-ready web IDs, and page text that can be used as evidence without treating remote content as instructions.
Options considered: Add a paid search API; scrape search engines directly; use a maintained free metasearch package while owning page fetching, sanitization, limits, and caching.
Decision: Add `ddgs>=9,<10` and call `DDGS(timeout=8).text(query, max_results=..., safesearch="moderate")`. Fetch pages separately with redirects disabled and revalidated, standard ports only, public-address checks, no environment proxy, an 8-second timeout, a 1 MB response cap, and a 20,000-character extracted-text cap. Accept HTML/XHTML/plain text, reject compressed responses, remove active and hidden HTML, return `web:<sha256>` citation IDs, and mark all search/fetch text `is_untrusted`. Cache sanitized results for five minutes with a 128-entry capacity. The provider contract is documented in the [DDGS repository](https://github.com/deedy5/ddgs) and [PyPI project page](https://pypi.org/project/ddgs/).
Consequences / how to reverse: Search depends on external metasearch providers and page fetching requires internet access; tests inject the provider and HTTP transport so safety behavior remains testable offline. Web content stays untrusted and must be wrapped by the researcher before inclusion in model prompts.

## ADR-017: Define a typed not-ready contract for the custom scorer MCP server [DECISION] Date: 2026-10-23 Status: active
Context: Phase 2 needs all three MCP servers available before the custom cross-encoder is trained in Phase 5, and orchestration needs a predictable response while the scorer is absent.
Options considered: Omit the third server until training; return an unstructured error; expose the planned `score_chunks(query, chunk_ids)` interface and a typed not-ready status.
Decision: Add `ara-dl-model-mcp` and expose `score_chunks` with strict query and bounded unique chunk-ID validation. Return a structured `status="not_ready"`, an empty score list, and a safe message until the custom model is trained and loaded. Define each future score with `chunk_id`, `relevance_score`, and optional `credibility_score` fields.
Consequences / how to reverse: MCP clients can discover and call the planned interface before model training without interpreting an exception. P5.6 must replace the placeholder result with actual validated scores while preserving the response schema.

## ADR-018: Use the SDK Client for managed stdio MCP subprocesses [DECISION] Date: 2026-10-23 Status: active
Context: P2.5 needs one client wrapper that can launch independent MCP servers, list their tools, call tools with deadlines, retry only bounded requests, and stop child processes reliably.
Options considered: Implement JSON-RPC and subprocess handling directly; manage low-level stdio streams and sessions; wrap the official SDK `Client` with `StdioServerParameters` and async context managers.
Decision: Use the official SDK v2 high-level client, keep named per-server async contexts, and close each context on disconnect or wrapper shutdown. Bound connect and call time, allow at most five retries, and retry protocol tool errors only when their safe JSON payload explicitly sets `retryable` to true. Return ordinary protocol tool errors unchanged so callers can inspect `CallToolResult.is_error`. The transport lifecycle follows the official [stdio client documentation](https://py.sdk.modelcontextprotocol.io/client/transports/).
Consequences / how to reverse: The SDK owns stdio framing and subprocess shutdown, while ARA supplies named connection management, bounded retry policy, and safe error conversion. Callers must use the wrapper as an async context manager and inspect returned tool results.

## ADR-019: Keep the Claude Desktop sample portable and verify local stdio independently [DECISION] Date: 2026-10-23 Status: active
Context: P2.6 needs a usable example for three local MCP servers without committing user-specific executable or project paths, plus evidence that each server starts over stdio.
Options considered: Commit the current workspace's absolute paths; rely on Desktop extensions only; provide a JSON config with explicit path placeholders and test the stdio protocol separately from the Desktop UI.
Decision: Add a three-server `mcpServers` JSON sample using `uv run --project` and clear absolute-path placeholders. Verify each actual server subprocess through the SDK `Client(StdioServerParameters(...))` wrapper, list its tools, and call the DL stub. Record that this validates stdio protocol behavior but does not verify a Claude Desktop UI session.
Consequences / how to reverse: The sample can be copied without exposing or baking in a machine path, but the user must replace placeholders and ensure Desktop can resolve uv. A future release can package the servers as Desktop extensions if distribution requires it.
