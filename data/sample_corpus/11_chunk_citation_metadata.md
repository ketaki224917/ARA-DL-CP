# Chunk identifiers preserve citation provenance

Each indexed passage needs a stable identifier that connects it to its source text. Useful metadata includes the source path or URL, page when available, and character offsets in the extracted document. A citation ID should be deterministic for the same source and chunking settings so an evaluation set can continue to point to the same evidence.

When a report cites a chunk, validate that the ID exists in the evidence store. Resolve the ID to the stored text and metadata before the critic checks the claim. This turns a citation from decorative text into a verifiable link between a statement and the passage offered as support.

Reference: [Chroma Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get); ARA corpus note, original text licensed under CC BY 4.0.

