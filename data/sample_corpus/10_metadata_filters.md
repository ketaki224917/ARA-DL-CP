# Metadata filters narrow the searchable evidence

Metadata describes a record with fields such as source file, page, publication date, or document type. A filter can restrict a similarity query to records whose metadata meets a condition. A document-text filter can also search for text conditions, but it is not a substitute for semantic similarity ranking.

Filters are useful for user constraints such as “search only this folder” or “use documents from this year.” Validate filter keys and values before passing them to a storage backend. Keep the original metadata available in results so the report can cite the source and location that produced each claim.

Reference: [Chroma Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get).

