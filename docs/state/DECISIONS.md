# Decisions

## ADR-001: Use a local-first Ollama-compatible LLM endpoint [ASSUMPTION] Date: 2026-10-22 Status: active
Context: The specification requires a free, local default and an interchangeable model client.
Options considered: Ollama HTTP API; direct Transformers integration; paid hosted API.
Decision: Start with Ollama's local HTTP API behind `llm/client.py`; keep model/base URL configurable. No paid API is required.
Consequences / how to reverse: The service must be installed separately and model smoke tests need a running local model. A different backend can be added behind the same client interface and logged as a superseding ADR.

## ADR-002: Default to a small Qwen model pending hardware detection [ASSUMPTION] Date: 2026-10-22 Status: active
Context: No Python, Ollama, GPU query access, or RAM query access is available in the current environment; the project must remain laptop-CPU-demoable.
Options considered: Defer model selection; default to a small CPU-feasible Qwen model; choose a larger model without confirmed hardware.
Decision: Set `qwen2.5:1.5b` as the configurable initial default. This is provisional, not evidence that it has been downloaded or run.
Consequences / how to reverse: Revisit after hardware access and model availability are checked. Record the final size/backend choice with measured environment evidence.

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
