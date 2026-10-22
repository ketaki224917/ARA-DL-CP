# ARA Master TODO

Status: `[ ]` todo, `[>]` in progress, `[x]` done, `[!]` blocked, `[~]` dropped.

## Phase 0 — Foundations
- [!] P0.1 Create repo skeleton, pyproject, uv lock, Makefile, ruff/mypy/pytest config (scaffold is present; uv lock is blocked by PyPI timeout)
- [x] P0.2 Create `docs/state/*` from templates; write `AGENTS.md` from supplied prompt
- [x] P0.3 Write CONVENTIONS.md (style, naming, logging, error handling, commit format)
- [!] P0.4 config.py (pydantic settings) + config.yaml + .env.example (code/tests written; pytest blocked by PyPI access)
- [!] P0.5 logging_setup.py (code/tests written; pytest blocked by PyPI access)
- [!] P0.6 Hardware detection + ENVIRONMENT.md + model choice ADR (probe code written; RAM/GPU inventory and dependency-backed check unavailable)
- [!] P0.7 llm/client.py (chat, structured-output w/ pydantic retry, streaming, tool-call helper) + tests (code/tests written; pytest blocked by PyPI access)
- [x] P0.8 Build/choose sample corpus (15–30 open-licensed docs on ONE niche topic; record sources & licenses in `data/sample_corpus/SOURCES.md`)

## Phase 1 — RAG
- [!] P1.1 Loaders (pdf, docx, md, txt, html) + tests (implementation and tests written; test run blocked by PyPI)
- [!] P1.2 Chunking (recursive + optional semantic; configurable) + metadata + tests (implementation and tests written; test run blocked by PyPI)
- [!] P1.3 Embeddings wrapper (cached, batched; implementation and tests written, test run blocked by PyPI)
- [!] P1.4 Vector store interface + Chroma impl (+ Qdrant stub; implementation/tests drafted, pytest blocked by PyPI)
- [!] P1.5 BM25 index (persisted; implementation/tests drafted, pytest blocked by PyPI)
- [!] P1.6 Hybrid retriever with RRF (implementation/tests drafted; pytest blocked by PyPI)
- [ ] P1.7 Reranker
- [ ] P1.8 answer() with citations + abstention
- [ ] P1.9 Eval set ≥ 40 Q/A (gold chunk IDs; mix of factoid, multi-hop, unanswerable)
- [ ] P1.10 Eval harness + comparison table; record in PROGRESS.md
- [ ] P1.11 `make ingest` idempotent; CLI `ara ingest`/`ara ask`

## Phase 2 — MCP
- [ ] P2.1 mcp_servers/common.py (validation, errors, logging)
- [ ] P2.2 rag_server + tests via MCP client
- [ ] P2.3 web_search_server + sanitization + caching + tests
- [ ] P2.4 dl_model_server stub
- [ ] P2.5 mcp_client wrapper (spawn stdio servers, list tools, call, timeout/retry)
- [ ] P2.6 Claude Desktop sample config + manual verification note

## Phase 3 — Orchestration
- [ ] P3.1 AgentState (pydantic): topic, plan, evidence store, draft, critiques, revision count, run metadata
- [ ] P3.2 Planner + prompts + JSON validation/retry + tests
- [ ] P3.3 Researcher (tool selection via LLM tool-calling through MCP client; dedupe; budget limits) + tests
- [ ] P3.4 Orchestrator graph + trace JSONL
- [ ] P3.5 Prompt-injection test fixtures
- [ ] P3.6 Gate: end-to-end plan+research run, saved sample trace

## Phase 4 — Writer/Critic
- [ ] P4.1 Writer (evidence-only, inline citations, section templates)
- [ ] P4.2 Citation parser/validator (deterministic check that cited IDs exist)
- [ ] P4.3 Critic (claim-level verification vs cited chunk, gap and contradiction checks) + JSON schema
- [ ] P4.4 Revision loop + stopping logic + per-iteration stats
- [ ] P4.5 Loop-effect experiment on ≥ 3 topics; table in PROGRESS.md

## Phase 5 — Custom DL model
- [ ] P5.1 Synthetic data generator (queries, positives, hard negatives via BM25/dense mining) + quality filtering
- [ ] P5.2 Public dataset subset integration + doc-level splits
- [ ] P5.3 Dataset/Dataloader + model.py (cross-encoder + optional credibility head)
- [ ] P5.4 train.py (config, seed, early stop, checkpoints, curves)
- [ ] P5.5 evaluate.py vs baselines + ablations + error analysis
- [ ] P5.6 export + load in dl_model_server (`score_chunks`) + tests
- [ ] P5.7 Integrate in researcher; A/B end-to-end comparison
- [ ] P5.8 docs/model_card.md

## Phase 6 — Generative layer
- [ ] P6.1 Diagram generation (Mermaid/Graphviz) + render + validate/retry
- [ ] P6.2 TTS narration script generation + audio synthesis
- [ ] P6.3 report_builder (MD/HTML/PDF, figures, references, audio link)
- [ ] P6.4 (stretch) Stable Diffusion illustration flag

## Phase 7 — Polish & ship
- [ ] P7.1 CLI polish, Makefile targets (`setup|ingest|serve|run|eval|train|test`)
- [ ] P7.2 README (Mermaid architecture, real results, usage, troubleshooting)
- [ ] P7.3 docs/design_decisions.md + architecture.md
- [ ] P7.4 Three finished example reports in outputs/
- [ ] P7.5 Full regression: fresh clone → `make setup && make ingest && make run TOPIC="..."` works
- [ ] P7.6 (stretch) LoRA fine-tune for report style, with before/after comparison
- [ ] P7.7 Final Acceptance Checklist verification

