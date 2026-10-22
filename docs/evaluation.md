# Retrieval evaluation protocol

The fixed query set is [`data/eval_sets/rag_eval.jsonl`](../data/eval_sets/rag_eval.jsonl). It contains 34 answerable factoid questions, 10 answerable multi-hop questions, and 8 unanswerable questions with gold chunk IDs derived from the checked-in sample corpus.

## Metrics

- **Recall@k:** per answerable question, fraction of its gold IDs present in the first `k` ranked results; macro-averaged over answerable questions.
- **MRR:** reciprocal rank of the first gold ID anywhere in the returned ranking; macro-averaged over answerable questions.
- **nDCG@k:** binary relevance with logarithmic rank discount, macro-averaged over answerable questions.
- **Citation precision:** micro-averaged correct citations divided by emitted citations over all questions. Citations on unanswerable questions count as incorrect; no emitted citations gives 0.
- **Answer rate:** share of answerable questions not abstained on.
- **Unanswerable abstention:** share of unanswerable questions correctly abstained on.

The harness stores ranked IDs separately from cited IDs so retrieval quality and answer citation quality remain distinct. Missing predictions count as empty results. Duplicate result IDs are counted once at their first rank.

## Required comparison

Run all systems on the same corpus and question set, and record `k`, corpus version, model names, candidate depth, and split. The table below is intentionally unmeasured: package installation and model service access are currently blocked.

| System | Recall@k | MRR | nDCG@k | Citation precision | Answer rate | Unanswerable abstention |
|---|---:|---:|---:|---:|---:|---:|
| Dense | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| BM25 | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| Hybrid RRF | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| Hybrid RRF + reranker | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |

Use `ara.rag.eval.load_evaluation_set`, `compare_runs`, and `save_metrics_json` to score predictions. A metric smoke check with synthetic predictions validates the implementation; it does not substitute for these four real retrieval runs.
