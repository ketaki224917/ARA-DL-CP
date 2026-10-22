# Training data and batches make reranker experiments reproducible

Supervised reranker training needs examples that pair a query with a passage and a relevance label. Positive passages should contain useful evidence for the query. Hard negatives should be plausible candidates that retrieval might return but that do not answer the query. Split by source document before training so near-duplicate passages from one document do not leak across train and test.

A dataset stores samples and labels; a data loader batches them for the training loop. Keep the seed, split IDs, model configuration, and checkpoint path with the run. Evaluate against fixed retrieval and ranking baselines using the same held-out query set.

Reference: [PyTorch quickstart: datasets and data loaders](https://docs.pytorch.org/tutorials/beginner/basics/quickstart_tutorial.html); [Sentence Transformers reranker training examples](https://sbert.net/examples/cross_encoder/training/rerankers/).

