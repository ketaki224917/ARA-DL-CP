# Vector collection query and lookup are different operations

A vector query ranks records by similarity to a query embedding. A record lookup retrieves known IDs or filtered records without similarity ranking. Applications often need both: similarity search discovers candidate chunks, while lookup retrieves the stored text and metadata for selected chunk IDs.

Keep the query embedding dimension consistent with the collection. Store source identifiers and other citation metadata with each chunk, and request the fields needed by the next stage. A result can then carry its text, ID, and provenance together instead of requiring a separate guess about where it came from.

Reference: [Chroma Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get).

