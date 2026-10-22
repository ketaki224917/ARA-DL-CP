# Fusion choices need an empirical comparison

RRF uses rank positions and discards score magnitudes. Distribution-Based Score Fusion (DBSF) instead normalizes score distributions within each result list before combining them. The two methods preserve different information: RRF is less sensitive to incompatible scales, while distribution-based fusion lets relative score gaps affect the result.

Neither rule is guaranteed to win for every corpus. Compare them on the same held-out questions, using the same component retrievers, candidate depths, and relevance labels. Keep a simple dense-only and lexical-only baseline so a fused ranking can be judged against the evidence each component already finds.

Reference: [Qdrant fundamentals on RRF and DBSF](https://qdrant.tech/documentation/faq/); [Qdrant hybrid search tuning](https://qdrant.tech/documentation/search-tuning/how-to-tune-hybrid-search/).

