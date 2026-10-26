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
- [x] P2.5 mcp_client wrapper (stdio lifecycle, tool listing/calls, timeout/retry; 120 tests pass)
- [x] P2.6 Claude Desktop sample config + stdio verification note (all three subprocess servers launch; 121 tests pass)

## Phase 3 — Orchestration
- [x] P3.1 AgentState (Pydantic): typed plan/evidence/draft/critique/run state, validation and JSON round-trip tests
- [x] P3.2 Planner + prompts + JSON validation/retry + tests (3-8 task plans, dependency validation, bounded retries; 152 tests pass)
- [x] P3.3 Researcher (LLM tool selection through MCP; evidence dedupe; call/item/character budgets; mocked tests; 164 tests pass)
- [x] P3.4 Orchestrator + JSONL trace lifecycle, tool metadata/latency, and run status tests (173 tests pass)
- [x] P3.5 Prompt-injection fixtures for local documents, web snippets, and fetched pages; all remain data and disallowed tools are rejected (176 tests pass)
- [x] P3.6 Offline end-to-end plan/research gate with real Planner/Researcher/Orchestrator, stdio MCP fixture, and saved synthetic trace (178 tests pass; live Ollama remains under ENV-002)

## Phase 4 — Writer/Critic
- [x] P4.1 Writer (bounded evidence-only sectioned output, structured claim IDs, inline citation rendering, deterministic abstention; 187 tests pass)
- [x] P4.2 Citation parser/validator (deterministic check that cited IDs exist; handles chunk/web markers, malformed syntax, and unknown IDs; 199 tests pass)
- [x] P4.3 Critic (claim-level verification vs cited chunk, gap and contradiction checks, strict structured schema, state updates; 209 tests pass)
- [x] P4.4 Revision loop + stopping logic + per-iteration stats (writer consumes bounded critic feedback; stops clean/abstained/unchanged/cap; 221 tests pass)
- [x] P4.5 Loop-effect experiment on ≥ 3 topics; table in PROGRESS.md (scripted controlled demonstration; live-model quality effect remains NOT RUN under ENV-002)

## Phase 5 — Custom DL model
- [x] P5.1 Synthetic data generator (queries, positives, hard negatives via BM25/dense mining) + quality filtering (local-LLM path implemented and mocked; offline fallback dataset committed; live generation NOT RUN under ENV-002)
- [x] P5.2 Public dataset subset integration + doc-level splits (SciFact; 200 labeled queries; evidence-linked document splits validated with no overlap)
- [x] P5.3 Dataset/Dataloader + model.py (split-safe pair batches, pinned MiniLM relevance scorer, optional masked credibility head; CPU inference verified)
- [x] P5.4 train.py (config-driven AdamW/BCE training, seeded split loaders, validation early stopping, atomic best checkpoint, JSON metrics, PNG loss curve; 3-epoch CPU run completed)
- [x] P5.5 evaluate.py vs baselines + ablations + error analysis (30-query internal SciFact test split; fine-tuned model ties recall and improves MRR/nDCG slightly over RRF; only four first-rank failures existed, all four reviewed)
- [x] P5.6 export + load in dl_model_server (`score_chunks`) + tests (atomic inference bundle; lazy scorer; real MCP client smoke returned ordered relevance probabilities; 251 tests pass)
- [x] P5.7 Integrate in researcher; A/B end-to-end comparison (optional MCP-only scoring with validated IDs/fallback; real local model moved gold evidence rank 2→1 on one controlled fixture)
- [x] P5.8 docs/model_card.md (training, internal held-out evaluation, four observed ranking failures, integration fixture, and limitations documented; checks pass)

## Phase 6 — Generative layer
- [x] P6.1 Diagram generation (constrained Mermaid flowchart) + Graphviz/SVG rendering + syntax validation/retry (11 focused tests; built-in SVG used because Graphviz/Mermaid CLI are absent; live Ollama generation NOT RUN)
- [x] P6.2 TTS narration script generation + audio synthesis (Pydantic 170–260 word script; pinned local Piper voice; 185-word CPU smoke rendered 68.79-second WAV; live Ollama script generation NOT RUN)
- [x] P6.3 report_builder (Markdown/HTML/PDF, figures, references, audio link; 10 focused tests; full suite 289 passed)
- [~] P6.4 Stable Diffusion illustration flag - dropped: optional stretch is outside the CPU-first acceptance path; Mermaid diagrams and Piper narration cover required generated visuals/audio.

## Phase 7 — Polish & ship
- [x] P7.1 CLI polish, Makefile targets (`setup|ingest|serve|run|eval|train|test`); command help and delegation tests pass (full suite 293 passed; GNU Make unavailable on host)
- [ ] P7.2 README (Mermaid architecture, real results, usage, troubleshooting)
- [ ] P7.3 docs/design_decisions.md + architecture.md
- [ ] P7.4 Three finished example reports in outputs/
- [ ] P7.5 Full regression: fresh clone → `make setup && make ingest && make run TOPIC="..."` works
- [ ] P7.6 (stretch) LoRA fine-tune for report style, with before/after comparison
- [ ] P7.7 Final Acceptance Checklist verification

