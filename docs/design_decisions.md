# Design decisions, trade-offs, and next steps

This document summarizes why ARA uses its current local models, retrieval approach, MCP boundaries, report workflow, and custom reranker. The binding ADRs are recorded in [`state/DECISIONS.md`](state/DECISIONS.md); measured results and limitations are linked below.

## Decisions at a glance

| Decision | Reason | Cost or limit |
|---|---|---|
| Local Ollama for chat and embeddings | Keeps private documents on the user's machine and avoids a paid API dependency. A full report run and 52-query embedding evaluation completed on the CPU host. | Users install Ollama and pull weights; model behavior and speed depend on local hardware. Small-model diagram and narration outputs needed deterministic fallbacks. |
| Dense + BM25 retrieval with RRF | Semantic matching and lexical matching provide complementary candidate lists; RRF uses ranks instead of mixing scores with different scales. The fixed 52-query run improved MRR from 0.924/0.943 to 0.989 over dense/BM25. | Equal weights and `k=60` are baselines. The result is descriptive on a small corpus; no uncertainty interval was measured. |
| Separate stdio MCP servers | Keeps local RAG, public web access, and custom scoring as independently discoverable tools behind a standard client protocol. | More subprocesses, configuration, and startup work; Claude Desktop UI integration was not exercised. |
| Typed state and a hand-rolled sequential orchestrator | Makes plans, evidence IDs, budgets, run status, revisions, and traces explicit without a graph-framework dependency. | The flow is sequential. Parallel research and branching recovery could justify a graph framework later. |
| MiniLM cross-encoder for second-stage ranking | Reuses a compact public pair-scoring model and spends its inference cost only on a bounded candidate union. | It is only a ranking aid. It does not determine claim truth or source credibility, and current ranking metrics are from a small internal split. |
| Evidence IDs required on structured claims | Code can deterministically validate citation syntax and evidence membership before a report is accepted. | ID existence does not prove entailment; the critic's support assessment remains model-based. |
| Mermaid/SVG, Piper, and Python PDF generation | Produces diagrams, narration, HTML, and PDF with local/free components and CPU-friendly fallbacks. | Ollama and voice assets are needed for full live output. Stable Diffusion was an optional stretch and is not shipped. |

## Why these choices

### Local model service

The model client speaks Ollama's local HTTP API behind a small `OllamaClient` interface. The default chat model is `qwen2.5:1.5b`, selected after the hardware probe found 18 logical processors and 15.52 GiB RAM without a supported CUDA/MPS accelerator. `embeddinggemma` is the configurable dense embedding model. Both models were exercised in live local report and retrieval runs. On this CPU host, the chat model produced invalid Mermaid and short narration that required the documented fallbacks.

Local service calls keep source text inside the user's machine by default and keep the application independent of paid model APIs. The trade-off is an extra install/download step and variable response time/quality across machines. The client interface and configuration keep a future local provider replaceable; any provider switch should preserve lazy loading and structured-output validation.

### Hybrid retrieval and reciprocal-rank fusion

BM25 retrieves exact terms, names, and identifiers. Dense retrieval can find semantically related wording. ARA queries both and combines one-based ranks using weighted RRF (`k=60`, equal weights by default). RRF avoids adding cosine similarity values to BM25 scores that have unrelated scales. Chroma persists dense vectors; the local BM25 index stores versioned chunk data as JSON; a manifest records hashes and indexing configuration so unchanged ingestion can skip embedding work.

The fixed evaluation has 52 labeled questions (34 factoid, 10 multi-hop, 8 unanswerable) over 21 documents and 33 chunks. At candidate depth 20 and cutoff 5, dense scored recall/MRR/nDCG 0.989/0.924/0.923; BM25 scored 0.977/0.943/0.935; RRF scored 0.989/0.989/0.971; and RRF plus MiniLM reranking scored 0.989/1.000/0.982. Candidate-chunk citation precision ranged from 0.200 to 0.204. The runner does not generate answers, so answer rate, abstention, and answer-level citation correctness remain unmeasured. See [`evaluation.md`](evaluation.md) for the run metadata and resume command. These metrics support RRF on this sample, not a general claim that fusion always wins.

### MCP boundaries

The official MCP Python SDK owns stdio framing and client lifecycle. ARA keeps three server processes: `rag` for local search and chunk lookup, `web-search` for bounded public search/fetch, and `dl-model` for optional relevance scoring. The Researcher calls them only through the named `MCPClient` wrapper, which bounds request time/retries and handles subprocess cleanup. This gives each tool domain a typed boundary and lets a generic client discover tools without importing agent internals.

The cost is process management and path/configuration work for desktop clients. The local stdio test did launch each real server subprocess and list its tools, but Claude Desktop itself was not opened. The current [config example](claude_desktop_config.example.json) uses absolute-path placeholders; see [`stdio_verification.md`](stdio_verification.md).

### Typed agents, citations, and the revision loop

`AgentState` stores the topic, validated 3-8 task plan, citation-keyed evidence, draft, critiques, and revision metadata. Plans are checked for duplicate IDs and invalid/cyclic dependencies before research begins. Retrieved local and web evidence is marked untrusted; tool names, arguments, result counts, evidence sizes, and per-run budgets are bounded.

The writer returns structured claims with evidence IDs, and code renders citations as `[chunk:<id>]` or `[web:<id>]`. A separate deterministic parser rejects malformed or unknown IDs. The critic checks citation membership before reviewing claim support, plan gaps, and contradictions. The revision loop defaults to at most three revisions and records per-iteration unsupported counts. This is easier to inspect than free-form recursive prompting, though claim support remains an LLM judgment rather than a formal proof.

The three-topic reduction experiment used the production Writer, Critic, and RevisionLoop with deliberately scripted drafts and critic responses. It reduced one scripted unsupported claim to zero per topic, confirming feedback propagation and counters. A separate live report run also removed one critic-flagged claim and re-reviewed the remaining four with zero unsupported; the required live three-topic quality comparison is still open.

### Why the custom MiniLM model

The custom ranker is a fine-tuned `cross-encoder/ms-marco-MiniLM-L6-v2` sequence-pair model. A cross-encoder scores a query and passage together, which is more suitable for reordering a bounded candidate list than embedding an entire corpus again. The base revision is pinned; training uses seeded AdamW and a small document-disjoint SciFact-derived set. CPU PyTorch supports the detected laptop environment. A separate credibility head is present as an option but remains disabled because no source-credibility labels were available.

On 208 queries from the expanded internal SciFact test split, the fine-tuned model scored recall@10 0.9933, MRR 0.9390, and nDCG@10 0.9504; RRF scored 0.9923, 0.9027, and 0.9236. The generic cross-encoder scored 0.9933, 0.9282, and 0.9433. A random-negative control scored 0.9933, 0.9424, and 0.9530, slightly exceeding the fine-tuned model on MRR/nDCG. There are no confidence intervals or significance tests. The result shows ranking gains over RRF and the generic checkpoint on this split, but no advantage over the random-negative control and no reliable generalization claim. The [model card](model_card.md) includes split construction, licenses, training details, error cases, and limitations.

The integration demo moved one synthetic gold passage from rank 2 to rank 1 and required one additional MCP call. It validates the scorer wiring and fallback path, not user-facing report quality. Relevance scores are uncalibrated and do not identify support versus contradiction.

### Diagrams, audio, and report files

Diagram output accepts a restricted Mermaid flowchart grammar, validates model output, and uses a built-in SVG renderer when Graphviz is unavailable. Narration uses a pinned local Piper voice; the package is an optional GPL-3.0-or-later extra, and the selected voice's model card identifies its training-data license. The report builder uses Markdown-it, ReportLab, and svglib for cited Markdown/HTML/PDF output and local SVG/WAV assets. Raw HTML and unsafe external SVG resources are rejected.

This keeps the required generated report path runnable without a browser-based PDF renderer. It still needs a local chat model to create a real diagram/narration script and the downloaded Piper voice to synthesize audio. Stable Diffusion was deferred because it is outside the required acceptance path and would add a large unverified model/runtime to the CPU-first setup.

## Measured results and what they mean

| Experiment | Result | Interpretation |
|---|---|---|
| BM25 + dense RRF, no reranker | recall@10 0.9923, MRR 0.9027, nDCG@10 0.9236 | Baseline over 208 internal SciFact queries. |
| Generic MS MARCO cross-encoder | recall@10 0.9933, MRR 0.9282, nDCG@10 0.9433 | Improved ranking over RRF on this split. |
| Fine-tuned cross-encoder | recall@10 0.9933, MRR 0.9390, nDCG@10 0.9504 | Improved on RRF and generic ranking; uncertainty was not measured. |
| Random-negative control | recall@10 0.9933, MRR 0.9424, nDCG@10 0.9530 | Slightly exceeded the fine-tuned model, so hard-negative training did not win this ablation. |
| Three-topic Writer/Critic loop | Live unsupported counts 1 to 0, 0 to 0, and 0 to 0 | One claim was removed and re-reviewed; two topics were already clean. Small live demonstration, not a broad quality estimate. |
| Researcher scorer A/B | Synthetic gold rank 2 to rank 1; MCP calls 1 to 2 | Verifies integration ordering; not a benchmark. |
| Four-way RAG evaluation | 52 questions, 33 chunks; RRF MRR 0.989 vs. dense 0.924 and BM25 0.943; RRF+reranker MRR 1.000 | Small, CPU-only sample; citation precision is retrieved-candidate precision, and no statistical uncertainty was computed. |
| Full local Ollama report run | Fresh-clone setup/ingest/run passed; generated cited MD/HTML/PDF/SVG/WAV | Used a structural report-heading diagram and citation-grounded narration after the small model returned invalid Mermaid and short scripts. |

For full result tables and reproduction details, see [`outputs/dl_evaluation_metrics.md`](../outputs/dl_evaluation_metrics.md), [`outputs/dl_researcher_ab.md`](../outputs/dl_researcher_ab.md), [`state/PROGRESS.md`](state/PROGRESS.md), and [`state/BLOCKERS.md`](state/BLOCKERS.md).

## Trade-offs and limitations

- **Privacy vs. setup:** local models keep inputs local by default, but users must install Ollama and download chat, embedding, and optional reranker/TTS weights.
- **Complementary retrieval vs. small-sample evidence:** the 52-query run favors RRF on MRR/nDCG, but the 33-chunk corpus is small and the result has no uncertainty interval.
- **Candidate precision vs. answer citations:** the retrieval table measures gold evidence among top-k chunks; answer-level citation accuracy and abstention need an answerer evaluation.
- **Auditable citations vs. semantic uncertainty:** citation IDs and provenance are deterministic; whether a cited passage truly supports a claim still requires model critique and human review.
- **Separate services vs. operational overhead:** MCP isolates tools and is protocol-tested, but each process and desktop-client path must be configured.
- **Internal reranker split vs. broad generalization:** the CPU-friendly MiniLM run used 208 internal SciFact queries with no multi-seed analysis or statistical tests; the random-negative control slightly outscored the fine-tuned model.
- **Optional features vs. default footprint:** the custom scorer and Piper synthesis add separate weights/dependencies. Stable Diffusion remains out of scope for this pass.
- **Host validation gaps:** the live report, three-topic revision experiment, and Make targets passed on Windows; Claude Desktop's UI itself was not launched, though all MCP stdio servers were verified through the SDK.

## What I would do next

1. Run the live writer/critic loop on at least three distinct topics and record before/after unsupported-claim counts.
2. Expand held-out DL ranking evaluation until at least 20 meaningful error cases can be analyzed; quantify uncertainty across additional queries/seeds.
3. Evaluate generated-answer citation precision and abstention separately from retrieved-candidate precision.
4. Verify the configuration in a live Claude Desktop UI session.

## Short interview answer

ARA combines local BM25 and dense retrieval because exact lexical matches and semantic matches cover different failure modes; it uses RRF to fuse their ranks without calibrating incomparable scores. On 52 fixed questions and 33 chunks, RRF reached MRR 0.989 versus 0.924 for dense and 0.943 for BM25; MiniLM reranking reached 1.000 with unchanged recall. The evidence is descriptive and small, and the citation metric measures retrieved chunks rather than generated answers. The research agents share typed cited state and call local RAG, public web, and optional reranking tools through independent MCP stdio servers. The full local report path works with structural diagram and citation-grounded speech fallbacks. The remaining quality work is a live three-topic critic experiment and a larger DL error review.
