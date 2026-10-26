# Design decisions, trade-offs, and next steps

This document summarizes why ARA uses its current local models, retrieval approach, MCP boundaries, report workflow, and custom reranker. The binding ADRs are recorded in [`state/DECISIONS.md`](state/DECISIONS.md); measured results and limitations are linked below.

## Decisions at a glance

| Decision | Reason | Cost or limit |
|---|---|---|
| Local Ollama for chat and embeddings | Keeps private documents on the user's machine and avoids a paid API dependency. | Users install Ollama and pull weights; model behavior and speed depend on local hardware. The configured models were not live-tested on the current host. |
| Dense + BM25 retrieval with RRF | Semantic matching and lexical matching provide complementary candidate lists; RRF uses ranks instead of mixing scores with different scales. | Equal weights and `k=60` are baselines. ARA's fixed RAG evaluation is still `NOT RUN`, so fusion has not demonstrated a measured win here. |
| Separate stdio MCP servers | Keeps local RAG, public web access, and custom scoring as independently discoverable tools behind a standard client protocol. | More subprocesses, configuration, and startup work; Claude Desktop UI integration was not exercised. |
| Typed state and a hand-rolled sequential orchestrator | Makes plans, evidence IDs, budgets, run status, revisions, and traces explicit without a graph-framework dependency. | The flow is sequential. Parallel research and branching recovery could justify a graph framework later. |
| MiniLM cross-encoder for second-stage ranking | Reuses a compact public pair-scoring model and spends its inference cost only on a bounded candidate union. | It is only a ranking aid. It does not determine claim truth or source credibility, and current ranking metrics are from a small internal split. |
| Evidence IDs required on structured claims | Code can deterministically validate citation syntax and evidence membership before a report is accepted. | ID existence does not prove entailment; the critic's support assessment remains model-based. |
| Mermaid/SVG, Piper, and Python PDF generation | Produces diagrams, narration, HTML, and PDF with local/free components and CPU-friendly fallbacks. | Ollama and voice assets are needed for full live output. Stable Diffusion was an optional stretch and is not shipped. |

## Why these choices

### Local model service

The model client speaks Ollama's local HTTP API behind a small `OllamaClient` interface. The default chat model is `qwen2.5:1.5b`, selected after the hardware probe found 18 logical processors and 15.52 GiB RAM without a supported CUDA/MPS accelerator. `embeddinggemma` is the configurable dense embedding model. The defaults target a laptop-scale CPU path; they are not backed by live inference measurements from this host because Ollama and both model weights are absent here.

Local service calls keep source text inside the user's machine by default and keep the application independent of paid model APIs. The trade-off is an extra install/download step and variable response time/quality across machines. The client interface and configuration keep a future local provider replaceable; any provider switch should preserve lazy loading and structured-output validation.

### Hybrid retrieval and reciprocal-rank fusion

BM25 retrieves exact terms, names, and identifiers. Dense retrieval can find semantically related wording. ARA queries both and combines one-based ranks using weighted RRF (`k=60`, equal weights by default). RRF avoids adding cosine similarity values to BM25 scores that have unrelated scales. Chroma persists dense vectors; the local BM25 index stores versioned chunk data as JSON; a manifest records hashes and indexing configuration so unchanged ingestion can skip embedding work.

The chosen RRF weights and constant are a starting point, not an ARA benchmark result. The project has 52 labeled questions over 19 sample notes, but dense, BM25, hybrid, and hybrid-plus-reranker metrics are all still `NOT RUN`. The metric definitions and required comparison are in [`evaluation.md`](evaluation.md). The next retrieval task is to run all four systems against that fixed set and report recall, MRR, nDCG, citation precision, answer rate, and unanswerable abstention together.

### MCP boundaries

The official MCP Python SDK owns stdio framing and client lifecycle. ARA keeps three server processes: `rag` for local search and chunk lookup, `web-search` for bounded public search/fetch, and `dl-model` for optional relevance scoring. The Researcher calls them only through the named `MCPClient` wrapper, which bounds request time/retries and handles subprocess cleanup. This gives each tool domain a typed boundary and lets a generic client discover tools without importing agent internals.

The cost is process management and path/configuration work for desktop clients. The local stdio test did launch each real server subprocess and list its tools, but Claude Desktop itself was not opened. The current [config example](claude_desktop_config.example.json) uses absolute-path placeholders; see [`stdio_verification.md`](stdio_verification.md).

### Typed agents, citations, and the revision loop

`AgentState` stores the topic, validated 3-8 task plan, citation-keyed evidence, draft, critiques, and revision metadata. Plans are checked for duplicate IDs and invalid/cyclic dependencies before research begins. Retrieved local and web evidence is marked untrusted; tool names, arguments, result counts, evidence sizes, and per-run budgets are bounded.

The writer returns structured claims with evidence IDs, and code renders citations as `[chunk:<id>]` or `[web:<id>]`. A separate deterministic parser rejects malformed or unknown IDs. The critic checks citation membership before reviewing claim support, plan gaps, and contradictions. The revision loop defaults to at most three revisions and records per-iteration unsupported counts. This is easier to inspect than free-form recursive prompting, though claim support remains an LLM judgment rather than a formal proof.

The three-topic reduction experiment used the production Writer, Critic, and RevisionLoop with deliberately scripted drafts and critic responses. It reduced one scripted unsupported claim to zero per topic. That confirms feedback propagation and counters; it is not a live-model quality result. Live measurement remains unavailable until Ollama is running.

### Why the custom MiniLM model

The custom ranker is a fine-tuned `cross-encoder/ms-marco-MiniLM-L6-v2` sequence-pair model. A cross-encoder scores a query and passage together, which is more suitable for reordering a bounded candidate list than embedding an entire corpus again. The base revision is pinned; training uses seeded AdamW and a small document-disjoint SciFact-derived set. CPU PyTorch supports the detected laptop environment. A separate credibility head is present as an option but remains disabled because no source-credibility labels were available.

On 30 queries from an internal SciFact test split, the fine-tuned model tied BM25+dense RRF on recall@10 (0.9667) and had MRR 0.9194 versus 0.9026 and nDCG@10 0.9298 versus 0.9175. The generic cross-encoder scored lower on MRR/nDCG, while a random-negative control matched RRF. There are no confidence intervals or significance tests. The observed gains are small and descriptive; the correct conclusion is **ties recall, improves two ranking metrics on this split, and has not shown a reliable generalization gain**. The [model card](model_card.md) includes split construction, licenses, training details, error cases, and limitations.

The integration demo moved one synthetic gold passage from rank 2 to rank 1 and required one additional MCP call. It validates the scorer wiring and fallback path, not user-facing report quality. Relevance scores are uncalibrated and do not identify support versus contradiction.

### Diagrams, audio, and report files

Diagram output accepts a restricted Mermaid flowchart grammar, validates model output, and uses a built-in SVG renderer when Graphviz is unavailable. Narration uses a pinned local Piper voice; the package is an optional GPL-3.0-or-later extra, and the selected voice's model card identifies its training-data license. The report builder uses Markdown-it, ReportLab, and svglib for cited Markdown/HTML/PDF output and local SVG/WAV assets. Raw HTML and unsafe external SVG resources are rejected.

This keeps the required generated report path runnable without a browser-based PDF renderer. It still needs a local chat model to create a real diagram/narration script and the downloaded Piper voice to synthesize audio. Stable Diffusion was deferred because it is outside the required acceptance path and would add a large unverified model/runtime to the CPU-first setup.

## Measured results and what they mean

| Experiment | Result | Interpretation |
|---|---|---|
| BM25 + dense RRF, no reranker | recall@10 0.9667, MRR 0.9026, nDCG@10 0.9175 | Baseline over 30 internal SciFact queries. |
| Generic MS MARCO cross-encoder | recall@10 0.9667, MRR 0.8854, nDCG@10 0.9052 | Tied recall and ranked first relevant documents lower than RRF on average. |
| Fine-tuned cross-encoder | recall@10 0.9667, MRR 0.9194, nDCG@10 0.9298 | Tied recall and had small MRR/nDCG gains on this split; uncertainty was not measured. |
| Random-negative control | recall@10 0.9667, MRR 0.9026, nDCG@10 0.9175 | Matched RRF, so the fine-tuned differences are not evidence of a robust training win. |
| Three-topic Writer/Critic loop | Scripted unsupported counts 1 to 0, one revision each | Verifies loop mechanics; not live-model quality. |
| Researcher scorer A/B | Synthetic gold rank 2 to rank 1; MCP calls 1 to 2 | Verifies integration ordering; not a benchmark. |
| Four-way RAG evaluation | NOT RUN | No measured dense/BM25/RRF/RRF-plus-rerank comparison yet. |
| Full local Ollama report run | NOT RUN on the development host | Ollama and configured chat/embedding weights were unavailable. |

For full result tables and reproduction details, see [`outputs/dl_evaluation_metrics.md`](../outputs/dl_evaluation_metrics.md), [`outputs/dl_researcher_ab.md`](../outputs/dl_researcher_ab.md), [`state/PROGRESS.md`](state/PROGRESS.md), and [`state/BLOCKERS.md`](state/BLOCKERS.md).

## Trade-offs and limitations

- **Privacy vs. setup:** local models keep inputs local by default, but users must install Ollama and download chat, embedding, and optional reranker/TTS weights.
- **Complementary retrieval vs. unmeasured fusion:** dense/BM25/RRF has a clear score-scale rationale, but ARA's own four-way RAG comparison is still missing.
- **Auditable citations vs. semantic uncertainty:** citation IDs and provenance are deterministic; whether a cited passage truly supports a claim still requires model critique and human review.
- **Separate services vs. operational overhead:** MCP isolates tools and is protocol-tested, but each process and desktop-client path must be configured.
- **Small reranker vs. broad generalization:** the CPU-friendly MiniLM run used a narrow 30-query internal SciFact split with no multi-seed analysis or statistical tests.
- **Optional features vs. default footprint:** the custom scorer and Piper synthesis add separate weights/dependencies. Stable Diffusion remains out of scope for this pass.
- **Host validation gaps:** the full live Ollama path, Claude Desktop UI, and GNU Make targets could not be exercised on the current Windows host.

## What I would do next

1. Install Ollama and pull the configured chat/embedding models, then run `ara ingest` and `ara run --topic ...` from a fresh environment. Save the full generated bundle and trace.
2. Execute dense, BM25, hybrid RRF, and hybrid-plus-rerank on all 52 RAG questions with identical corpus/configuration; record the six metrics from [`evaluation.md`](evaluation.md), including abstention and citation precision.
3. Expand reranker evaluation to more queries and multiple seeds, quantify uncertainty, and add a source-credibility dataset before enabling the credibility head.
4. Verify the configuration in a live Claude Desktop UI session and test Makefile targets on a host with GNU Make.
5. Complete the fresh-environment CLI regression and final acceptance review when Ollama is available.

## Short interview answer

ARA combines local BM25 and dense retrieval because exact lexical matches and semantic matches cover different failure modes; it uses RRF to fuse their ranks without calibrating incomparable scores. The research agents share typed, citation-keyed state and call local RAG, public web, and optional reranking tools through independent MCP stdio servers. A custom MiniLM cross-encoder reranks only retrieved candidates. On a 30-query internal SciFact split it ties RRF recall and slightly improves MRR/nDCG, while a random-negative control matches the baseline, so the result is promising but inconclusive. The main engineering trade-offs are local setup/model cost, unmeasured RAG fusion, LLM-based claim checking, and limited benchmark size. The next steps are a real local end-to-end run, the fixed 52-question retrieval comparison, and broader multi-seed reranker evaluation.
