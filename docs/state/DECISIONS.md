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

