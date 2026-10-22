# Retrieval evaluation needs relevance labels and a fixed protocol

An evaluation set maps each question to one or more gold passage IDs. Run each retriever on the same questions and record its ordered results. Recall at `k` checks whether a gold passage appears in the first `k`; MRR gives more credit when the first relevant passage is higher; NDCG supports graded relevance and discounts lower ranks.

Do not claim one retriever is better because it has a more complex name. Report the metric, cutoff, corpus version, model, candidate depth, and query split. Keep an unanswerable set too, so the answer stage can be evaluated for abstention rather than retrieval alone.

Reference: [scikit-learn NDCG score](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html); [Qdrant hybrid search tuning](https://qdrant.tech/documentation/search-tuning/how-to-tune-hybrid-search/).

