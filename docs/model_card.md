# ARA MiniLM Evidence Reranker — Model Card

**Version:** 1.0  
**Status:** Experimental research component  
**Last updated:** 2026-10-27

## Summary

ARA fine-tunes the English `cross-encoder/ms-marco-MiniLM-L6-v2` checkpoint to rank a query and a candidate passage for evidence relevance. The scorer is used after BM25+dense retrieval; it does not search the corpus itself, determine whether a scientific claim is true, or replace citations and human review.

On a 208-query internal SciFact test split, the fine-tuned model ties the generic and random-negative systems on recall@10 and improves MRR/nDCG over the RRF and generic baselines. The random-negative control scores slightly higher on MRR/nDCG than the fine-tuned model, so hard-negative fine-tuning has not shown a win over that ablation. Results are descriptive; no confidence intervals or significance tests were computed.

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

The training/evaluation corpus uses all 693 eligible claims from the labeled `train` and `dev` portions of the [AllenAI SciFact release](https://github.com/allenai/scifact) whose evidence documents are present in the pinned corpus. The upstream official test claims were excluded. Claims and evidence annotations are CC BY 4.0; the S2ORC abstracts are ODC-By 1.0. See [`data/dl_data/SOURCES.md`](../data/dl_data/SOURCES.md) and [`scifact_subset/metadata.json`](../data/dl_data/scifact_subset/metadata.json) for attribution, archive SHA-256, and preparation details.

| Split | Queries | Documents |
|---|---:|---:|
| Train | 415 | 3,083 |
| Validation | 70 | 508 |
| Internal test | 208 | 1,592 |
| **Total** | **693** | **5,183** |

Claims sharing a labeled evidence document are assigned to the same split; remaining abstracts are assigned by a seeded SHA-256 bucket. The prepared split has no document-ID overlap. Both SUPPORT and CONTRADICT evidence abstracts are positive retrieval labels. All other candidates are treated as non-relevant for the ranking metrics, although the dataset does not establish that every unannotated abstract is truly irrelevant.

### Training pairs

The expanded main run used 934 training examples and 155 validation examples, including 64 deterministic offline query/passage rows from the repository's original sample-corpus notes. The sample notes are licensed CC BY 4.0; see [`data/sample_corpus/SOURCES.md`](../data/sample_corpus/SOURCES.md). The offline queries are extractive, not live-LLM generated. BM25-mined negatives are drawn only from the train or validation document partition. The test partition was not loaded during training or checkpoint selection.

BM25-mined negatives are unjudged, so some may contain relevant evidence. This can make the training labels noisy. The random-negative ablation replaces mined negatives with deterministic random passages; it is a control, not an independently validated training dataset.

## Training procedure

- Initialization: pinned MS MARCO MiniLM cross-encoder checkpoint above.
- Objective: binary cross-entropy with logits for relevance.
- Optimizer: AdamW, learning rate `2e-5`, weight decay `0.01`.
- Seed: `42`.
- Batch size: `4`; maximum sequence length: `256` tokens.
- Maximum epochs: `3`; validation-loss patience: `2`; select the checkpoint by validation BCE only.
- Hardware: CPU-only laptop runtime, 18 logical processors, 15.52 GiB RAM; no supported CUDA/MPS accelerator was detected.

The expanded training run selected epoch 1 by validation BCE and stopped after epoch 3 when validation loss failed to improve for the configured patience:

| Epoch | Train BCE | Validation BCE |
|---:|---:|---:|
| 1 | 0.593809 | 0.407094 |
| 2 | 0.370783 | 0.418369 |
| 3 | 0.256068 | 0.459412 |

The tracked history is [`outputs/dl_training_metrics.json`](../outputs/dl_training_metrics.json), with the loss curve at [`outputs/dl_training_loss.png`](../outputs/dl_training_loss.png). BCE improvement is training evidence only; it does not show superiority on ranking metrics.

## Evaluation

Evaluation used 208 labeled queries in the internal test partition, not the official SciFact test set. For each query, BM25 and the pinned `sentence-transformers/all-MiniLM-L6-v2` dense encoder retrieved their top 20 documents; their union was fused with RRF constant 60. Candidate recall@20 was `0.9981`, with a mean union of `33.38` documents. The dense model is Apache-2.0 under its [upstream card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41); its pinned revision and mean-pooling setup are recorded in ADR-034 and the expanded split protocol in ADR-061.

Metrics are macro averages across the 208 queries. Recall@10 is the fraction of a query's annotated relevant documents found in the top 10; MRR uses the rank of the first relevant document; nDCG@10 uses binary relevance. No confidence intervals or statistical significance tests were computed.

| System | Recall@10 | MRR | nDCG@10 |
|---|---:|---:|---:|
| BM25 + dense RRF, no reranker | 0.9923 | 0.9027 | 0.9236 |
| Generic MS MARCO cross-encoder | 0.9933 | 0.9282 | 0.9433 |
| **Fine-tuned cross-encoder** | **0.9933** | **0.9390** | **0.9504** |
| Random-negative control | 0.9933 | 0.9424 | 0.9530 |

The fine-tuned model improves on RRF by `0.0363` MRR and `0.0268` nDCG@10; it improves on the generic cross-encoder by `0.0108` MRR and `0.0070` nDCG@10. The random-negative control is slightly higher than the fine-tuned model by `0.0035` MRR and `0.0026` nDCG@10 while matching recall@10. The model therefore shows a ranking improvement over the retrieval and generic baselines on this internal split, but hard-negative training does not beat the random-negative control. Full values are in [`outputs/dl_evaluation_metrics.json`](../outputs/dl_evaluation_metrics.json) and [`outputs/dl_evaluation_metrics.md`](../outputs/dl_evaluation_metrics.md).

### Random-negative ablation

The random-negative control used the same 934/155 train/validation row counts and selected epoch 2 by validation BCE (`0.019427`; epoch 1 was `0.048701`, epoch 3 was `0.020603`). On the held-out ranking comparison it reached recall@10 `0.9933`, MRR `0.9424`, and nDCG@10 `0.9530`, slightly exceeding the hard-negative model on MRR/nDCG. Its lower validation loss should not be compared directly with the main run because random negatives differ in difficulty from BM25-mined negatives.

## Error review

The fine-tuned system did not rank a gold document first for 20 of the 208 test queries. Twelve first relevant documents were at rank 2; three were at rank 3; two were at rank 4; and one each was at ranks 7, 10, and 16. Candidate recall@20 was complete in 19 cases; the remaining case had candidate recall 0.60. Thus most reviewed failures arose from ranking closely related distractors above present gold evidence, while one case also had incomplete candidate coverage:

| Query ID | Claim | First relevant rank | Candidate recall@20 |
|---|---|---:|---:|
| `scifact:1138` | TRAP+ osteoclasts regulate mature osteoblast maintenance. | 16 | 1.00 |
| `scifact:463` | Genomic aberrations of metastases provide information for targeted therapy. | 10 | 1.00 |
| `scifact:469` | Glial calcium waves influence seizures. | 7 | 1.00 |
| `scifact:1266` | The risk of breast cancer among parous women increases with placental weight of pregnancies, and this association is strongest for premenopausal breast cancer. | 4 | 1.00 |
| `scifact:756` | Many proteins in human cells can be post-translationally modified at lysine residues via acetylation. | 4 | 1.00 |
| `scifact:1265` | The risk of breast cancer among parous women decreases with placental weight of pregnancies. | 3 | 1.00 |
| `scifact:22` | 76-85% of people with severe mental disorder receive no treatment in low and middle income countries. | 3 | 1.00 |
| `scifact:48` | A total of 1,000 people in the UK are asymptomatic carriers of vCJD infection. | 3 | 1.00 |
| `scifact:1119` | Sympathetic nerve activity is elevated throughout normal pregnancy. | 2 | 1.00 |
| `scifact:1169` | The M2-phenotype in brown adipose tissue macrophages increases brown adipose tissue thermogenic activity. | 2 | 1.00 |
| `scifact:1221` | The genomic aberrations found in matasteses are very similar to those found in the primary tumor. | 2 | 1.00 |
| `scifact:1224` | The latent infection of myeloid cells with human cytomegalovirus induces a number of changes in gene expression. | 2 | 1.00 |
| `scifact:342` | Diabetic patients with acute coronary syndrome experience decreased short-term and long-term risk for bleeding events. | 2 | 1.00 |
| `scifact:343` | Diabetic patients with acute coronary syndrome experience increased short-term and long-term risk for bleeding events. | 2 | 1.00 |
| `scifact:385` | Epigenetic modulating agents (EMAs) modulate antitumor immune response in a cancer model system. | 2 | 1.00 |
| `scifact:394` | Excess gestational weight gain is associated with obesity-related pregnancy outcomes. | 2 | 1.00 |
| `scifact:568` | In a naive state, blocking Wingless-Int-1 secretion from mouse embryonic stem cells inhibits self-renewal of the mouse embryonic stem cells. | 2 | 1.00 |
| `scifact:79` | Active caspase-11 promotes pyroptosis. | 2 | 1.00 |
| `scifact:873` | Obesity is determined solely by environmental factors. | 2 | 0.60 |
| `scifact:942` | Phase information is useful for predicting donor-recipient matches in organ transplantation. | 2 | 1.00 |

All 20 rows are observed first-rank failures; none were added as successful examples. Nineteen had full candidate recall, and their top-five abstracts commonly share the query's disease, tissue, pathway, or intervention terms while addressing a different endpoint or population. The severe tail includes ranks 7, 10, and 16; most misses are near-ties at rank 2. The detailed top-five candidates and model scores are in [`outputs/dl_error_analysis.json`](../outputs/dl_error_analysis.json). Unannotated SciFact abstracts may contain relevant evidence, so these labels are retrieval-judgment failures rather than proof that every distractor is irrelevant.

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
