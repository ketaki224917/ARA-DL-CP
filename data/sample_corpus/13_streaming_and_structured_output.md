# Streaming and structured output solve different problems

Streaming lets a client receive generated content in pieces before the full answer is complete. This can reduce perceived wait time for an interactive user, but the client must handle partial output and completion events. A final report pipeline may prefer a non-streaming call when it needs to validate the whole response before using it.

Structured output asks the model for data in a specified format, such as JSON or a JSON Schema. The application should still parse the result, validate it against its own schema, and retry or fail visibly when validation fails. A format request helps constrain generation; it does not replace validation.

Reference: [Ollama chat API](https://docs.ollama.com/api/chat); [Pydantic models and validation](https://docs.pydantic.dev/latest/concepts/models/).

