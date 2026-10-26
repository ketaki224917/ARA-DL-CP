"""Local Ollama chat client with validated structured output and tool-call parsing."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ara.config import Settings, load_settings

logger = logging.getLogger(__name__)
ModelT = TypeVar("ModelT", bound=BaseModel)
ChatMessage = Mapping[str, Any]


class LLMClientError(RuntimeError):
    """Raised when the local model endpoint fails or returns an invalid response."""


class StructuredOutputError(LLMClientError):
    """Raised when structured output cannot be parsed or validated."""


class ToolCall(BaseModel):
    """A validated function call requested by the model."""

    name: str
    arguments: dict[str, Any]


class OllamaClient:
    """Synchronous client for the Ollama `/api/chat` endpoint.

    The HTTP client is created lazily, so importing or constructing this class never
    starts a service, loads weights, or performs network access.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        resolved = settings or load_settings()
        self.base_url = str(resolved.llm_base_url).rstrip("/")
        self.model = resolved.llm_model
        self.timeout_seconds = resolved.llm_request_timeout_seconds
        self.temperature = resolved.llm_temperature
        self.num_predict = resolved.llm_num_predict
        self._http_client = http_client
        self._owns_http_client = http_client is None

    def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float | None = None,
        output_format: Mapping[str, Any] | str | None = None,
    ) -> str:
        """Send a non-streaming chat request and return assistant text."""
        response = self._post_chat(
            messages,
            stream=False,
            temperature=temperature,
            output_format=output_format,
        )
        message = response.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise LLMClientError("Ollama response did not contain assistant message text.")
        return content

    def structured_output(
        self,
        messages: Sequence[ChatMessage],
        schema: type[ModelT],
        *,
        max_retries: int = 3,
        json_schema: Mapping[str, Any] | None = None,
    ) -> ModelT:
        """Ask for JSON, validate it, retry with errors, then attempt JSON repair."""
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        schema_prompt = (
            "Return only a JSON object matching this JSON Schema. Do not add markdown.\n"
            + json.dumps(
                schema.model_json_schema() if json_schema is None else json_schema,
                ensure_ascii=False,
            )
        )
        retry_messages: list[ChatMessage] = [
            {"role": "system", "content": schema_prompt},
            *messages,
        ]
        last_content = ""
        for attempt in range(max_retries + 1):
            last_content = self.chat(
                retry_messages,
                temperature=0.0,
                output_format=(
                    schema.model_json_schema() if json_schema is None else json_schema
                ),
            )
            try:
                return schema.model_validate(_decode_json(last_content))
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                logger.warning(
                    "Structured response validation failed (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries + 1,
                    exc,
                )
                if attempt < max_retries:
                    retry_messages = [
                        *retry_messages,
                        {"role": "assistant", "content": last_content},
                        {
                            "role": "user",
                            "content": (
                                "Your previous response failed JSON/schema validation. "
                                f"Correct this error and return only valid JSON: {exc}"
                            ),
                        },
                    ]

        try:
            from json_repair import repair_json

            repaired = repair_json(last_content, return_objects=True)
            return schema.model_validate(repaired)
        except Exception as exc:
            logger.exception("JSON repair failed for structured response")
            raise StructuredOutputError(
                f"Could not produce valid {schema.__name__} after {max_retries + 1} attempts."
            ) from exc

    def stream_chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float | None = None,
    ) -> Iterable[str]:
        """Yield assistant text chunks from Ollama's newline-delimited response."""
        payload = self._chat_payload(messages, stream=True, temperature=temperature)
        try:
            with self._http().stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout_seconds,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    event = json.loads(line)
                    message = event.get("message", {})
                    content = message.get("content", "") if isinstance(message, dict) else ""
                    if content:
                        yield str(content)
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            logger.exception("Ollama streaming request failed")
            raise LLMClientError("Ollama streaming request failed.") from exc

    def tool_calls(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[Mapping[str, Any]],
        *,
        temperature: float | None = None,
    ) -> list[ToolCall]:
        """Return model-requested tool calls without executing them."""
        response = self._post_chat(
            messages,
            stream=False,
            temperature=temperature,
            tools=tools,
        )
        message = response.get("message", {})
        raw_calls = message.get("tool_calls", []) if isinstance(message, dict) else []
        if not isinstance(raw_calls, list):
            raise LLMClientError("Ollama returned malformed tool calls.")
        calls: list[ToolCall] = []
        for raw_call in raw_calls:
            function = raw_call.get("function", {}) if isinstance(raw_call, dict) else {}
            name = function.get("name") if isinstance(function, dict) else None
            raw_args = function.get("arguments", {}) if isinstance(function, dict) else {}
            if isinstance(raw_args, str):
                try:
                    raw_args = json.loads(raw_args)
                except json.JSONDecodeError as exc:
                    raise LLMClientError(f"Tool {name!r} returned invalid JSON arguments.") from exc
            if not isinstance(name, str) or not isinstance(raw_args, dict):
                raise LLMClientError("Ollama returned a malformed tool call.")
            calls.append(ToolCall(name=name, arguments=raw_args))
        return calls

    def close(self) -> None:
        """Close the internally owned HTTP client, if it has been created."""
        if self._owns_http_client and self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> OllamaClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _post_chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        stream: bool,
        temperature: float | None,
        tools: Sequence[Mapping[str, Any]] | None = None,
        output_format: Mapping[str, Any] | str | None = None,
    ) -> dict[str, Any]:
        payload = self._chat_payload(
            messages,
            stream=stream,
            temperature=temperature,
            output_format=output_format,
        )
        if tools is not None:
            payload["tools"] = list(tools)
        try:
            response = self._http().post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            result = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.exception("Ollama chat request failed")
            raise LLMClientError("Ollama chat request failed.") from exc
        if not isinstance(result, dict):
            raise LLMClientError("Ollama returned a non-object response.")
        return result

    def _chat_payload(
        self,
        messages: Sequence[ChatMessage],
        *,
        stream: bool,
        temperature: float | None,
        output_format: Mapping[str, Any] | str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [dict(message) for message in messages],
            "stream": stream,
            "options": {
                "temperature": self.temperature if temperature is None else temperature,
                "num_predict": self.num_predict,
            },
        }
        if output_format is not None:
            payload["format"] = (
                dict(output_format)
                if isinstance(output_format, Mapping)
                else output_format
            )
        return payload

    def _http(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=self.timeout_seconds)
        return self._http_client


def _decode_json(content: str) -> Any:
    """Parse model JSON, allowing a single fenced JSON block."""
    candidate = content.strip()
    if candidate.startswith("```"):
        candidate = candidate.removeprefix("```json").removeprefix("```")
        candidate = candidate.removesuffix("```").strip()
    return json.loads(candidate)

