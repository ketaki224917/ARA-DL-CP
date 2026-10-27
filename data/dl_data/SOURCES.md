# Public reranker data sources

## SciFact subset

ARA uses all 693 eligible claims from the labeled `claims_train.jsonl` and
`claims_dev.jsonl` files in the official [AllenAI SciFact repository](https://github.com/allenai/scifact).
Eligibility requires every annotated evidence document to be present in the pinned corpus.
The archive URL, SHA-256 digest, selected query counts, split counts, and document counts are
recorded in `scifact_subset/metadata.json`. The deterministic seed-42 split targets 60% train,
10% validation, and 30% internal test; claims sharing evidence documents stay together, and
the generated partitions have zero document overlap. The downloaded archive is not committed; run
`uv run python -m ara.dl.public_data --download` to fetch and verify it, then prepare the
same subset from the configured seed and query limit.

The upstream [SciFact data format](https://github.com/allenai/scifact/blob/master/doc/data.md)
provides claim IDs, claim text, annotated evidence document IDs, support/contradict labels,
and rationale sentence indices. For relevance training, both `SUPPORT` and `CONTRADICT`
documents receive relevance `1`; the original verdict and rationale sentence IDs remain in
each record. Official test claims are excluded because this subset creates its own internal
held-out splits from labeled train/dev claims.

## Licenses and attribution

The upstream [license file](https://github.com/allenai/scifact/blob/master/LICENSE.md)
states that claims and evidence annotations are CC BY 4.0. The abstracts in the corpus come
from S2ORC and are licensed ODC-By 1.0. The [SciFact paper](https://aclanthology.org/2020.emnlp-main.609/)
is by David Wadden, Shanchuan Lin, Kyle Lo, Lucy Lu Wang, Madeleine van Zuylen, Arman Cohan,
and Hannaneh Hajishirzi (EMNLP 2020). Keep this attribution and the per-record source IDs if
the prepared data is redistributed.

## Split method

Claims linked by shared evidence document IDs are grouped into one connected component and
assigned wholly to train, validation, or test. This prevents a positive abstract from
appearing in multiple splits. Remaining corpus documents are assigned using the configured
seed and a SHA-256 bucket. `metadata.json` records the split counts and the preparation
script validates that document-ID sets are disjoint and every query's positives belong to
its split.
