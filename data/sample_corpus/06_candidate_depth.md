# Candidate depth sets a ceiling for later ranking stages

Fusion and reranking operate on candidates returned by earlier searches. If a relevant passage is below the retrieval cutoff, later stages cannot promote it. Increasing the cutoff may expose more relevant passages, but it also increases the work required for fusion, storage, or model-based reranking.

Tune candidate depth with a fixed query set. Measure whether relevant items enter the shortlist before spending time on reranker settings. If recall stops improving as depth grows, investigate indexing, query formulation, filters, and corpus coverage rather than assuming that a slower ranking model will find missing evidence.

Reference: [Qdrant hybrid search tuning](https://qdrant.tech/documentation/search-tuning/how-to-tune-hybrid-search/); [Qdrant reranking tutorial](https://qdrant.tech/documentation/tutorials-basics/reranking-hybrid-search/).

