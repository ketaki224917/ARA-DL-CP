# P5.5 Reranker Evaluation

SciFact internal held-out test partition; this is not the original official test set.
Gold relevance includes both SUPPORT and CONTRADICT evidence documents.
BM25+dense RRF candidate depth: top 20 from each retriever; candidate recall@20: 1.0000; mean union size: 32.73.

| System | Recall@10 | MRR | nDCG@10 | Queries |
|---|---:|---:|---:|---:|
| BM25+dense RRF (no reranker) | 0.9667 | 0.9026 | 0.9175 | 30 |
| Generic MS MARCO cross-encoder | 0.9667 | 0.8854 | 0.9052 | 30 |
| Fine-tuned cross-encoder | 0.9667 | 0.9194 | 0.9298 | 30 |
| Random-negative ablation | 0.9667 | 0.9026 | 0.9175 | 30 |

Failure review cases saved: 4. See `outputs\dl_error_analysis.json`.
These are all four test queries where the fine-tuned model did not rank a gold document first; this split did not contain 20 such failures.
