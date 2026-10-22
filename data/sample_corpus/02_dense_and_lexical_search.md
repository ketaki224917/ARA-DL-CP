# Dense and lexical search find different evidence

Lexical search compares query terms with terms in the document. It is useful for exact names, codes, uncommon phrases, and version strings. Its weakness is vocabulary mismatch: a passage can express the same idea with different words and receive little lexical signal.

Dense search embeds a query and passages, then looks for nearby vectors. It can connect related wording, but a close vector match may still miss a precise identifier or treat two different numbers as similar. These methods make different errors, so a hybrid system can retrieve with both and combine their ranked candidates.

Reference: [Sentence Transformers retrieve and rerank](https://sbert.net/examples/applications/retrieve_rerank/README.html); [Qdrant text hybrid search](https://qdrant.tech/documentation/search/text-search/hybrid-search/).

