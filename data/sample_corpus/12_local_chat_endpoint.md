# A local chat endpoint keeps model choice configurable

Ollama exposes a chat endpoint that accepts a model name and a sequence of role/content messages. Its response includes an assistant message. The request can also include generation options, tool definitions, a response format, and a streaming preference.

An application should keep the endpoint URL, model name, timeout, and temperature in configuration. It should create its HTTP client only when a request is made, report endpoint errors clearly, and avoid treating a successful HTTP response as proof that the content is valid. Structured responses still need schema validation in the application.

Reference: [Ollama chat API](https://docs.ollama.com/api/chat).

