# Rerank a shortlist instead of the whole corpus

A reranker receives a query and a smaller set of retrieved passages, scores their relevance, and sorts that set again. A bi-encoder can embed each query and passage separately for efficient retrieval. A cross-encoder reads the query and candidate together, allowing a more direct relevance comparison at greater per-pair cost.

This division is useful when the corpus is too large to score every passage with a cross-encoder. The fast retriever creates a shortlist; the slower model refines its order. Reranking can improve precision at the top, but cannot add a passage that is absent from the shortlist.

Reference: [Sentence Transformers retrieve and rerank](https://sbert.net/examples/applications/retrieve_rerank/README.html); [Qdrant hybrid search with reranking](https://qdrant.tech/documentation/tutorials-basics/reranking-hybrid-search/).

