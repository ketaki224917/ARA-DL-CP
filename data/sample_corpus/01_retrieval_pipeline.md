# A retrieval pipeline for evidence-grounded answers

A retrieval-augmented answer has two stages. First, a retriever selects passages that may support the question. Second, a language model drafts an answer from those passages. The retrieved passages should remain attached to the answer so a reader can inspect the evidence. This keeps retrieval errors visible: a fluent paragraph does not prove that the right source was found.

For a small research assistant, keep the pipeline explicit: ingest source files, assign stable chunk IDs, retrieve a candidate set, optionally rerank it, and ask the writer to use only that evidence. If the candidate set is empty or does not support the requested detail, the system should say so instead of filling gaps from model memory.

Reference: [Qdrant hybrid search](https://qdrant.tech/documentation/search/text-search/hybrid-search/); [Sentence Transformers retrieve and rerank](https://sbert.net/examples/applications/retrieve_rerank/README.html).

