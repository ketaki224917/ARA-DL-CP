# Sample-corpus retrieval evaluation

Queries: 52 | Chunks: 33
Candidate depth: 20 | Metrics cutoff: 5
Embedding model: `embeddinggemma`
Reranker: `cross-encoder/ms-marco-MiniLM-L6-v2` at `df500e56a59fc34f37322735a40eff666200312e`
Device: `cpu`

Citation precision@k treats the top-k retrieved chunk IDs as candidate citations and compares them with gold chunk IDs; no LLM answer generation is included.

| System | Recall@5 | MRR | nDCG@5 | Citation precision@5 |
|---|---:|---:|---:|---:|
| Dense | 0.989 | 0.924 | 0.923 | 0.204 |
| BM25 | 0.977 | 0.943 | 0.935 | 0.200 |
| Hybrid RRF | 0.989 | 0.989 | 0.971 | 0.204 |
| Hybrid RRF + reranker | 0.989 | 1.000 | 0.982 | 0.204 |
