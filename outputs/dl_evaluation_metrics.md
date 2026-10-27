# P5.5 Reranker Evaluation

SciFact internal held-out test partition; this is not the original official test set.
Gold relevance includes both SUPPORT and CONTRADICT evidence documents.
BM25+dense RRF candidate depth: top 20 from each retriever; candidate recall@20: 0.9981; mean union size: 33.38.

| System | Recall@10 | MRR | nDCG@10 | Queries |
|---|---:|---:|---:|---:|
| BM25+dense RRF (no reranker) | 0.9923 | 0.9027 | 0.9236 | 208 |
| Generic MS MARCO cross-encoder | 0.9933 | 0.9282 | 0.9433 | 208 |
| Fine-tuned cross-encoder | 0.9933 | 0.9390 | 0.9504 | 208 |
| Random-negative ablation | 0.9933 | 0.9424 | 0.9530 | 208 |

Failure review cases saved: 20. See `outputs\dl_error_analysis.json`.
