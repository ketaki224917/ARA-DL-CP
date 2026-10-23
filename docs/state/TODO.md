# ARA Master TODO

Status: `[ ]` todo, `[>]` in progress, `[x]` done, `[!]` blocked, `[~]` dropped.

## Phase 0 — Foundations
- [x] P0.1 Create repo skeleton, pyproject, uv lock, Makefile, ruff/mypy/pytest config (uv.lock created; full tests, Ruff, and mypy pass)
- [x] P0.2 Create `docs/state/*` from templates; write `AGENTS.md` from supplied prompt
- [x] P0.3 Write CONVENTIONS.md (style, naming, logging, error handling, commit format)
- [x] P0.4 config.py (pydantic settings) + config.yaml + .env.example (tests pass)
- [x] P0.5 logging_setup.py (tests pass)
- [!] P0.6 Hardware detection + ENVIRONMENT.md + model choice ADR (CPU and RAM detected; supported GPU not detected; VRAM details remain unknown)
- [x] P0.7 llm/client.py (chat, structured-output w/ pydantic retry, streaming, tool-call helper) + tests (tests pass)
- [x] P0.8 Build/choose sample corpus (15–30 open-licensed docs on ONE niche topic; record sources & licenses in `data/sample_corpus/SOURCES.md`)

## Phase 1 — RAG
- [x] P1.1 Loaders (pdf, docx, md, txt, html) + tests (tests pass)
- [x] P1.2 Chunking (recursive + optional semantic; configurable) + metadata + tests (tests pass)
- [x] P1.3 Embeddings wrapper (cached, batched; tests pass; live Ollama call not run)
- [x] P1.4 Vector store interface + Chroma impl (+ Qdrant stub; tests pass)
- [x] P1.5 BM25 index (persisted; tests pass)
- [x] P1.6 Hybrid retriever with RRF (tests pass)
- [x] P1.7 Reranker (lazy CrossEncoder adapter; tests pass; model weights not installed)
- [x] P1.8 answer() with citations + abstention (tests pass)
- [x] P1.9 Eval set ≥ 40 Q/A (52 rows; factoid, multi-hop, and unanswerable with validated gold chunk IDs)
- [!] P1.10 Eval harness + comparison table (metrics implemented; real four-system comparison blocked by unavailable Ollama and model weights)
- [x] P1.11 `make ingest` idempotent; CLI `ara ingest`/`ara ask` (tests pass; live Ollama CLI run not available)

## Phase 2 — MCP
- [x] P2.1 mcp_servers/common.py (validation, errors, logging; tests pass)
- [x] P2.2 rag_server + tests via MCP client (official v2 in-memory client tests pass)
- [x] P2.3 web_search_server + sanitization + caching + tests (115 tests pass; Ruff and mypy pass)
- [x] P2.4 dl_model_server stub (typed `score_chunks` not-ready response; 118 tests pass; Ruff and mypy pass)
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

