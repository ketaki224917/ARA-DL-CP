# Hybrid retrieval combines independent candidate lists

A hybrid retriever runs more than one search method for the same question. A common pairing is dense semantic search and sparse lexical search. Dense search can surface a paraphrase, while lexical search can preserve a rare token or exact code. The combined candidate pool is then ordered by a fusion rule.

Fusion cannot recover a passage that none of the component searches returned. Candidate depth therefore matters: each retrieval leg must pass enough plausible results into the fusion stage. Evaluate the full pipeline on labeled questions; a hybrid label by itself does not demonstrate better retrieval.

Reference: [Qdrant hybrid queries](https://qdrant.tech/documentation/search/hybrid-queries/); [Qdrant text hybrid search](https://qdrant.tech/documentation/search/text-search/hybrid-search/).

