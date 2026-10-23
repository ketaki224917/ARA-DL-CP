"""Unit tests for the Ollama client using an in-memory HTTP transport."""

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from pydantic import BaseModel

from ara.config import Settings
from ara.llm.client import OllamaClient, StructuredOutputError


class ShortAnswer(BaseModel):
    answer: str


def make_client(handler: Callable[[httpx.Request], httpx.Response]) -> OllamaClient:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return OllamaClient(Settings(_env_file=None), http_client=client)


def json_response(payload: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json=payload)


def test_chat_sends_configured_model_and_returns_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        assert request.read()
        return json_response({"message": {"content": "hello"}})

    client = make_client(handler)
    assert client.chat([{"role": "user", "content": "hi"}]) == "hello"
    client.close()


def test_structured_output_retries_with_validation_feedback() -> None:
    responses = iter(("{bad", '{"answer": "ready"}'))
    requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.read())
        requests.append(body)
        return json_response({"message": {"content": next(responses)}})

    client = make_client(handler)
    result = client.structured_output([{"role": "user", "content": "answer"}], ShortAnswer)

    assert result.answer == "ready"
    assert len(requests) == 2
    assert "validation" in requests[1]["messages"][-1]["content"].lower()
    client.close()


def test_structured_output_uses_json_repair_as_fallback() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return json_response({"message": {"content": '{"answer": "fixed",}'}})

    client = make_client(handler)
    result = client.structured_output(
        [{"role": "user", "content": "answer"}], ShortAnswer, max_retries=0
    )

    assert result.answer == "fixed"
    client.close()


def test_structured_output_fails_after_repair_and_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    class InvalidRepair:
        @staticmethod
        def repair_json(_: str, *, return_objects: bool) -> dict[str, str]:
            assert return_objects
            return {"wrong": "shape"}

    import sys

    monkeypatch.setitem(sys.modules, "json_repair", InvalidRepair)
    client = make_client(lambda _: json_response({"message": {"content": "{}"}}))

    with pytest.raises(StructuredOutputError):
        client.structured_output([], ShortAnswer, max_retries=1)
    client.close()


def test_stream_chat_yields_chunks() -> None:
    body = (
        '{"message":{"content":"first"},"done":false}\n'
        '{"message":{"content":" second"},"done":true}\n'
    )
    client = make_client(lambda _: httpx.Response(200, text=body))

    assert list(client.stream_chat([{"role": "user", "content": "hi"}])) == [
        "first",
        " second",
    ]
    client.close()


def test_tool_calls_are_parsed_but_not_executed() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "message": {
                    "tool_calls": [
                        {"function": {"name": "search", "arguments": '{"query":"x"}'}}
                    ]
                }
            }
        )

    client = make_client(handler)
    calls = client.tool_calls([{"role": "user", "content": "search"}], [])

    assert len(calls) == 1
    assert calls[0].name == "search"
    assert calls[0].arguments == {"query": "x"}
    client.close()

