# NDCG rewards relevant passages near the top

Normalized Discounted Cumulative Gain (NDCG) evaluates a ranked list when relevance labels can have multiple grades. It gives more weight to items near the top, discounts items farther down, then normalizes by the score of an ideal ordering. This makes values from different queries more comparable than raw discounted gain alone.

NDCG complements recall and reciprocal rank. Recall measures how much of the known relevant set was retrieved; reciprocal rank focuses on the first relevant item; NDCG considers the ordering of graded relevance. Choose the cutoff `k` to match the number of passages the application actually presents or uses.

Reference: [scikit-learn `ndcg_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html).

