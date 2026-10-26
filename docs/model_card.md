# ARA MiniLM Evidence Reranker — Model Card

**Version:** 1.0  
**Status:** Experimental research component  
**Last updated:** 2026-10-26

## Summary

ARA fine-tunes the English `cross-encoder/ms-marco-MiniLM-L6-v2` checkpoint to rank a query and a candidate passage for evidence relevance. The scorer is used after BM25+dense retrieval; it does not search the corpus itself, determine whether a scientific claim is true, or replace citations and human review.

The model ties the BM25+dense RRF baseline on recall@10 on a 30-query internal SciFact test split. It has slightly higher MRR and nDCG@10 on that split, but the random-negative control matches the retrieval baseline. These results are descriptive and do not establish a reliable generalization gain.

## Model details

| Field | Value |
|---|---|
| Architecture | MiniLM cross-encoder sequence classifier with one relevance logit |
| Base checkpoint | `cross-encoder/ms-marco-MiniLM-L6-v2` |
| Pinned revision | `df500e56a59fc34f37322735a40eff666200312e` |
| Base model license | Apache-2.0, as declared by the [upstream model card](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2/tree/df500e56a59fc34f37322735a40eff666200312e) |
| Inference input | One English query and one passage per pair; maximum length 256 tokens by default |
| Output | Relevance logit for ranking; the MCP service returns its sigmoid value |
| Credibility head | Disabled; no source-credibility labels were available |
| Runtime | PyTorch CPU is supported; tested on Python 3.12.15, PyTorch 2.14.1+cpu, Transformers 4.57.6 |

The sigmoid output is **not calibrated confidence**. It is exposed for convenient ordering only and should not be interpreted as the probability that a claim is true, that a source is credible, or that a passage entails a claim.

## Intended use and limits

Use the model to reorder a small set of already retrieved local passages for a research query. ARA preserves each passage's chunk ID and provenance. The researcher calls the model only through the `dl-model` MCP server; enable it with `ARA_DL_USE_SCORER=true` after training, exporting, and connecting that server. The feature is disabled by default and falls back to retrieval order when scoring is not ready or its response is invalid.

Do not use this model as a fact checker, citation validator, source-credibility classifier, medical decision system, or substitute for reading the cited source. It has only been evaluated for evidence-document ranking on a small SciFact-derived split. Do not treat its score as support/contradiction polarity: both annotated SUPPORT and CONTRADICT documents count as relevant retrieval evidence.

## Training data

### Public SciFact subset

The training/evaluation corpus is a deterministic 200-claim subset from the labeled `train` and `dev` portions of the [AllenAI SciFact release](https://github.com/allenai/scifact). The upstream official test claims were excluded. Claims and evidence annotations are CC BY 4.0; the S2ORC abstracts are ODC-By 1.0. See [`data/dl_data/SOURCES.md`](../data/dl_data/SOURCES.md) and [`scifact_subset/metadata.json`](../data/dl_data/scifact_subset/metadata.json) for attribution, archive SHA-256, and preparation details.

| Split | Queries | Documents |
|---|---:|---:|
| Train | 140 | 3,602 |
| Validation | 30 | 759 |
| Internal test | 30 | 822 |
| **Total** | **200** | **5,183** |

Claims sharing a labeled evidence document are assigned to the same split; remaining abstracts are assigned by a seeded SHA-256 bucket. The prepared split has no document-ID overlap. Both SUPPORT and CONTRADICT evidence abstracts are positive retrieval labels. All other candidates are treated as non-relevant for the ranking metrics, although the dataset does not establish that every unannotated abstract is truly irrelevant.

### Training pairs

The main run used 358 training examples: 154 labeled positive SciFact pairs, 140 BM25-mined negative pairs, and 64 rows from 32 deterministic offline query/passage pairs based on the repository's original sample-corpus notes. The sample notes are licensed CC BY 4.0; see [`data/sample_corpus/SOURCES.md`](../data/sample_corpus/SOURCES.md). The offline queries are extractive, not live-LLM generated. Validation used 32 positive and 30 mined-negative SciFact examples (62 total). The test partition was not loaded during training or checkpoint selection.

BM25-mined negatives are unjudged, so some may contain relevant evidence. This can make the training labels noisy. The random-negative ablation replaces mined negatives with deterministic random passages; it is a control, not an independently validated training dataset.

## Training procedure

- Initialization: pinned MS MARCO MiniLM cross-encoder checkpoint above.
- Objective: binary cross-entropy with logits for relevance.
- Optimizer: AdamW, learning rate `2e-5`, weight decay `0.01`.
- Seed: `42`.
- Batch size: `4`; maximum sequence length: `256` tokens.
- Maximum epochs: `3`; validation-loss patience: `2`; select the checkpoint by validation BCE only.
- Hardware: CPU-only laptop runtime, 18 logical processors, 15.52 GiB RAM; no supported CUDA/MPS accelerator was detected.

The full training run selected epoch 3 and did not stop early:

| Epoch | Train BCE | Validation BCE |
|---:|---:|---:|
| 1 | 0.684900 | 0.416132 |
| 2 | 0.437026 | 0.335476 |
| 3 | 0.321357 | 0.309428 |

The tracked history is [`outputs/dl_training_metrics.json`](../outputs/dl_training_metrics.json), with the loss curve at [`outputs/dl_training_loss.png`](../outputs/dl_training_loss.png). BCE improvement is training evidence only; it does not show superiority on ranking metrics.

## Evaluation

Evaluation used 30 labeled queries in the internal test partition, not the official SciFact test set. For each query, BM25 and the pinned `sentence-transformers/all-MiniLM-L6-v2` dense encoder retrieved their top 20 documents; their union was fused with RRF constant 60. Candidate recall@20 was `1.0000`, with a mean union of 32.73 documents. The dense model is Apache-2.0 under its [upstream card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41); its pinned revision and mean-pooling setup are recorded in ADR-034.

Metrics are macro averages across the 30 queries. Recall@10 is the fraction of a query's annotated relevant documents found in the top 10; MRR uses the rank of the first relevant document; nDCG@10 uses binary relevance. No confidence intervals or statistical significance tests were computed.

| System | Recall@10 | MRR | nDCG@10 |
|---|---:|---:|---:|
| BM25 + dense RRF, no reranker | 0.9667 | 0.9026 | 0.9175 |
| Generic MS MARCO cross-encoder | 0.9667 | 0.8854 | 0.9052 |
| **Fine-tuned cross-encoder** | **0.9667** | **0.9194** | **0.9298** |
| Random-negative control | 0.9667 | 0.9026 | 0.9175 |

The fine-tuned model ties RRF on recall@10 and improves MRR by `0.0169` and nDCG@10 by `0.0123` on this split. The generic checkpoint scores lower than RRF on MRR and nDCG; the random-negative control matches RRF. The sample is small, so these differences are not evidence of a statistically reliable gain. Full values are in [`outputs/dl_evaluation_metrics.json`](../outputs/dl_evaluation_metrics.json) and [`outputs/dl_evaluation_metrics.md`](../outputs/dl_evaluation_metrics.md).

### Random-negative ablation

The random-negative control used the same 358/62 train/validation row counts and selected epoch 1 by validation BCE (`0.050674`; epochs 2 and 3 were `0.065077` and `0.058376`). On the held-out ranking comparison it matched RRF at recall@10 `0.9667`, MRR `0.9026`, and nDCG@10 `0.9175`. Its lower validation loss should not be compared directly with the main run because the negative examples differ in difficulty.

## Error review

The fine-tuned system did not rank a gold document first for four of the 30 test queries. All four had candidate recall 1.0, so the observed problem was ranking within the candidate union:

| Query ID | Claim | First relevant rank |
|---|---|---:|
| `scifact:1138` | TRAP+ osteoclasts regulate mature osteoblast maintenance. | 12 |
| `scifact:645` | Intake of folic acid and vitamin B6 increases homocysteine levels. | 2 |
| `scifact:646` | Intake of folic acid and vitamin B6 reduces homocysteine levels. | 2 |
| `scifact:765` | Medications to treat obesity do not have side effects. | 2 |

The detailed top-five candidates and model scores are in [`outputs/dl_error_analysis.json`](../outputs/dl_error_analysis.json). The requested 20 failure examples did not exist; the artifact contains all four observed cases rather than adding successful queries to reach 20.

## Researcher integration

The scorer is an opt-in post-retrieval step, bounded to the configured local candidate count and MCP tool-call budget. In the controlled two-passage demo, the same locally trained model was called through the MCP SDK:

| System | Gold rank | Gold MRR | MCP calls |
|---|---:|---:|---:|
| Baseline | 2 | 0.5000 | 1 |
| DL scorer enabled | 1 | 1.0000 | 2 |

This single synthetic fixture verifies the integration path and fallback/order behavior; it is not an independent benchmark. Results are saved in [`outputs/dl_researcher_ab.md`](../outputs/dl_researcher_ab.md) and [`outputs/dl_researcher_ab.json`](../outputs/dl_researcher_ab.json).

## Reproducibility

From the repository root, with the locked `dl` extra installed and the SciFact subset prepared:

```powershell
.tools/uv/uv.exe run --locked --extra dev --extra dl python -m ara.dl.train
.tools/uv/uv.exe run --locked --extra dev --extra dl python -m ara.dl.evaluate
.tools/uv/uv.exe run --locked --extra dev --extra dl python -m ara.dl.export
.tools/uv/uv.exe run --locked --extra dev --extra dl pytest
```

`python -m ara.dl.evaluate` trains the random-negative control by default before loading the test partition. The checkpoint and export bundle under `models/checkpoints/` and `models/exported/` are generated artifacts and are not committed; the base checkpoints are pinned by revision in config. On the tested Windows host, set `UV_SYSTEM_CERTS=true`, `UV_CACHE_DIR=.tools/uv-cache`, and `UV_PROJECT_ENVIRONMENT=.tools/dl-venv` for `uv` commands. GNU Make was unavailable.

## Known limitations and risks

- Only 30 internal test queries were evaluated; the official SciFact test claims were excluded. No confidence intervals, significance tests, or multi-seed variance were measured.
- SciFact is a narrow scientific fact-verification dataset. Results may not transfer to other subjects, source types, long documents, multilingual queries, or private corpora.
- Unannotated documents are treated as non-relevant during ranking metrics even though labels may be incomplete. BM25-mined training negatives are also unjudged.
- SUPPORT and CONTRADICT documents are both retrieval-relevant. The model is not trained to distinguish support from contradiction.
- The random-negative control matches the RRF baseline; the observed fine-tuned MRR/nDCG differences are small and descriptive.
- The credibility head is disabled and no source-quality or credibility labels were available. Do not interpret relevance as credibility.
- MCP sigmoid values are uncalibrated ranking scores. No claim-level entailment, answer quality, citation correctness, or downstream report quality was evaluated here.
- The DL service needs the exported model bundle and base weights. If unavailable or malformed, the researcher falls back to the original local retrieval order.

## References

- Wadden et al. (2020), [Fact or Fiction: Verifying Scientific Claims](https://aclanthology.org/2020.emnlp-main.609/), and the [AllenAI SciFact dataset](https://github.com/allenai/scifact).
- [MS MARCO MiniLM cross-encoder model card](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2/tree/df500e56a59fc34f37322735a40eff666200312e).
- [all-MiniLM-L6-v2 dense model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41).
- See [`data/dl_data/SOURCES.md`](../data/dl_data/SOURCES.md) for data attribution and license details, and ADR-031–036 in [`docs/state/DECISIONS.md`](state/DECISIONS.md) for implementation decisions.
