# Interpreting cross-encoder scores

A cross-encoder score is a model output used to order query-passage pairs. Its numeric value is not automatically a calibrated probability, and scores from different reranker models may use different ranges. Ranking within a candidate set is often the intended use; a universal threshold requires calibration on representative labeled data.

A small shortlist controls inference cost because the model evaluates each query-passage pair. Track the number of candidates, model version, hardware, and latency alongside ranking quality. If the answer passage never reached the shortlist, a high score for another passage does not establish that the reranker is the cause of the miss.

Reference: [Sentence Transformers reranker documentation](https://sbert.net/examples/applications/retrieve_rerank/README.html); [Sentence Transformers cross-encoder rerankers](https://sbert.net/examples/cross_encoder/training/rerankers/).

