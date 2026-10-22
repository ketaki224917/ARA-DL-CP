# Retrieval evaluation set

`rag_eval.jsonl` contains 52 questions over the 19-note sample corpus: 34 factoid, 10 multi-hop, and 8 unanswerable. Answerable rows carry a short reference answer and one or more gold chunk IDs. Unanswerable rows have `answerable: false`, `expected_answer: null`, and no gold IDs.

Chunk IDs were generated from the corpus notes using `chunk_document` with the default 900-character chunk size and 120-character overlap. The `source` value is the note filename relative to `data/sample_corpus`. Recompute and review all gold IDs if corpus text, source naming, chunk settings, or the chunk-ID algorithm changes.

Each JSONL record uses these fields:

- `id`: stable question identifier.
- `category`: `factoid`, `multi_hop`, or `unanswerable`.
- `question`: query submitted to a retriever or answerer.
- `expected_answer`: short reference answer, or `null` for unanswerable cases.
- `answerable`: whether the sample corpus contains an answer.
- `gold_chunk_ids`: relevant passage IDs; empty for unanswerable cases.

The gold IDs are binary relevance labels. Do not treat this compact set as evidence that a particular retriever is better; use a fixed protocol and report per-method metrics.
