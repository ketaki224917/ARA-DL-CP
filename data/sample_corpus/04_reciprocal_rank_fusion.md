# Reciprocal Rank Fusion

Reciprocal Rank Fusion (RRF) combines ranked lists using the positions of shared candidates rather than adding raw scores. With one-indexed ranks, a common form is `score(d) = Σ 1 / (k + rank(d))`, summed over result lists where document `d` appears. The constant `k` controls how quickly lower ranks lose influence.

This is helpful when retrievers use score scales that do not mean the same thing. A cosine similarity and a BM25 score should not be added as if one unit represented the same evidence strength in both systems. RRF still depends on the component rankings and candidate cutoffs, so record those settings during evaluation.

Reference: [Qdrant hybrid query fusion](https://qdrant.tech/documentation/search/hybrid-queries/).

