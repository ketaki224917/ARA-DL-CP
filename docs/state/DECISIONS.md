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
