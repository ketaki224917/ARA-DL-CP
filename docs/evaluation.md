# Retrieval evaluation

The fixed query set is [`data/eval_sets/rag_eval.jsonl`](../data/eval_sets/rag_eval.jsonl): 52 questions with gold chunk IDs from the checked-in sample corpus (34 factoid, 10 multi-hop, 8 unanswerable). The indexed corpus contains 21 documents and 33 chunks.

## Metrics

- **Recall@k:** for each answerable question, the fraction of its gold chunk IDs in the first `k` results; macro-averaged over answerable questions.
- **MRR:** reciprocal rank of the first gold chunk anywhere in the returned candidate ranking; macro-averaged over answerable questions.
- **nDCG@k:** binary relevance with logarithmic rank discount; macro-averaged over answerable questions.
- **Citation precision@k:** micro-averaged gold-chunk precision among the first `k` retrieved IDs across all questions. Gold hits on unanswerable questions are impossible because those questions have no gold IDs.

Citation precision here measures the purity of the retrieved candidate chunks; this retrieval-only comparison does not run the LLM answerer or measure generated-answer citation accuracy. Answer rate and unanswerable abstention are also not measured by this experiment.

## Reproduction and checkpoints

Run `make eval-rag ARGS=--fresh` to start from the first question. Run `make eval-rag` to resume from the last completed query. The runner compares dense retrieval, BM25, hybrid reciprocal-rank fusion, and hybrid RRF reranked by the pinned MiniLM cross-encoder. Each query's four ranked lists are atomically checkpointed to `outputs/rag_retrieval_evaluation/predictions.jsonl`.

The run metadata records hashes of the evaluation set and BM25 index, the indexed chunk-ID fingerprint, model names/revision, candidate depth, metric cutoff, and device. Resume rejects changed metadata. The aggregate output is `outputs/rag_retrieval_evaluation/metrics.json` and the Markdown table is `outputs/rag_retrieval_evaluation/metrics.md`.

## Measured comparison

Run on 2026-10-26 using the CPU-only Windows host, all 52 questions, 33 chunks, `embeddinggemma`, candidate depth 20, metric cutoff 5, and `cross-encoder/ms-marco-MiniLM-L6-v2` at revision `df500e56a59fc34f37322735a40eff666200312e`.

| System | Recall@5 | MRR | nDCG@5 | Citation precision@5 |
|---|---:|---:|---:|---:|
| Dense | 0.989 | 0.924 | 0.923 | 0.204 |
| BM25 | 0.977 | 0.943 | 0.935 | 0.200 |
| Hybrid RRF | 0.989 | 0.989 | 0.971 | 0.204 |
| Hybrid RRF + reranker | 0.989 | 1.000 | 0.982 | 0.204 |

On this small corpus, RRF improved MRR over both single retrievers, while adding the cross-encoder produced a further small MRR/nDCG gain and no recall or citation-precision change. These results are descriptive; the corpus is small, no uncertainty intervals were computed, and the measured citation precision is candidate-chunk precision rather than answer-level citation quality. The runner's query-level checkpoint and machine-readable result contain the full rankings and unrounded values.
