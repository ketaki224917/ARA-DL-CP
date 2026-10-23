"""Async MCP client wrapper for launching and calling stdio servers."""

from __future__ import annotations

import asyncio
import json
import math
import re
from collections.abc import Awaitable, Callable, Mapping
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import NoReturn, TypeVar

from mcp import Client as SDKClient
from mcp import StdioServerParameters
from mcp.types import CallToolResult, Tool

from ara.mcp_servers.common import (
    ToolExecutionError,
    ToolInputError,
    ToolTimeoutError,
    get_server_logger,
    log_tool_call,
    require_int,
    require_text,
)

_SERVER_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
_TOOL_NAME_MAX_LENGTH = 128
_DEFAULT_TIMEOUT_SECONDS = 30.0
_DEFAULT_RETRIES = 1
_MAX_RETRIES = 5
_T = TypeVar("_T")


@dataclass
class _Connection:
    client: SDKClient
    exit_stack: AsyncExitStack


class MCPClient:
    """Manage named MCP stdio connections with bounded requests and retries."""

    def __init__(
        self,
        *,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        retries: int = _DEFAULT_RETRIES,
        retry_delay_seconds: float = 0.1,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a finite positive number")
        if (
            isinstance(retry_delay_seconds, bool)
            or not isinstance(retry_delay_seconds, (int, float))
            or not math.isfinite(retry_delay_seconds)
            or retry_delay_seconds < 0
        ):
            raise ValueError("retry_delay_seconds must be a finite non-negative number")
        self._timeout_seconds = timeout_seconds
        self._retries = require_int(retries, "retries", minimum=0, maximum=_MAX_RETRIES)
        self._retry_delay_seconds = retry_delay_seconds
        self._connections: dict[str, _Connection] = {}
        self._entered = False
        self._closing = False
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> MCPClient:
        if self._entered:
            raise RuntimeError("MCPClient is already open")
        self._entered = True
        self._closing = False
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    @property
    def connected_servers(self) -> tuple[str, ...]:
        """Names of the currently connected stdio servers."""
        return tuple(self._connections)

    async def connect(self, name: str, parameters: StdioServerParameters) -> None:
        """Launch a stdio server and keep its client connection until disconnect."""
        server_name = _validate_server_name(name)
        if not isinstance(parameters, StdioServerParameters):
            raise ToolInputError("parameters must be MCP stdio server parameters.")
        if not self._entered or self._closing:
            raise ToolInputError("MCPClient must be open before connecting a server.")
        async with self._lock:
            if server_name in self._connections:
                raise ToolInputError(f"MCP server {server_name!r} is already connected.")
            exit_stack = AsyncExitStack()
            await exit_stack.__aenter__()
            client = SDKClient(parameters, read_timeout_seconds=self._timeout_seconds)
            try:
                await asyncio.wait_for(
                    exit_stack.enter_async_context(client),
                    timeout=self._timeout_seconds,
                )
            except TimeoutError as exc:
                await exit_stack.aclose()
                raise ToolTimeoutError("Starting the MCP server timed out.") from exc
            except Exception as exc:
                await exit_stack.aclose()
                raise ToolExecutionError("The MCP server process could not be started.") from exc
            self._connections[server_name] = _Connection(client=client, exit_stack=exit_stack)

    async def disconnect(self, name: str) -> None:
        """Close one server connection and stop its stdio subprocess."""
        server_name = _validate_server_name(name)
        async with self._lock:
            connection = self._connections.pop(server_name, None)
        if connection is not None:
            try:
                await connection.exit_stack.aclose()
            except Exception as exc:
                raise ToolExecutionError("The MCP server process could not be stopped.") from exc

    async def aclose(self) -> None:
        """Close all child processes and mark this wrapper unavailable."""
        if not self._entered or self._closing:
            return
        self._closing = True
        for name in reversed(tuple(self._connections)):
            await self.disconnect(name)
        self._entered = False

    async def list_tools(
        self,
        server_name: str,
        *,
        timeout_seconds: float | None = None,
        retries: int | None = None,
    ) -> list[Tool]:
        """List all tools exposed by a connected server."""
        client = self._get_client(server_name)
        timeout, retry_count = self._request_limits(timeout_seconds, retries)
        logger = get_server_logger("client")
        try:
            with log_tool_call(logger, server_name="mcp-client", tool_name="list_tools"):
                response = await self._run_with_retry(
                    client.list_tools,
                    timeout_seconds=timeout,
                    retries=retry_count,
                )
        except Exception as exc:
            _raise_safe_request_error(exc)
        return response.tools

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Mapping[str, object],
        *,
        timeout_seconds: float | None = None,
        retries: int | None = None,
    ) -> CallToolResult:
        """Call a remote tool with a timeout and bounded transient retries.

        Protocol-level tool errors are returned to the caller. Errors whose text
        contains a valid ARA payload with `retryable: true` are retried first.
        """
        client = self._get_client(server_name)
        safe_tool_name = require_text(
            tool_name,
            "tool_name",
            max_length=_TOOL_NAME_MAX_LENGTH,
        )
        if not isinstance(arguments, Mapping):
            raise ToolInputError("tool arguments must be an object.")
        timeout, retry_count = self._request_limits(timeout_seconds, retries)
        request_arguments = dict(arguments)
        logger = get_server_logger("client")
        try:
            with log_tool_call(logger, server_name="mcp-client", tool_name="call_tool"):
                return await self._run_with_retry(
                    lambda: client.call_tool(safe_tool_name, request_arguments),
                    timeout_seconds=timeout,
                    retries=retry_count,
                    retryable_result=_is_retryable_tool_result,
                )
        except Exception as exc:
            _raise_safe_request_error(exc)

    def _get_client(self, server_name: str) -> SDKClient:
        name = _validate_server_name(server_name)
        if not self._entered or self._closing:
            raise ToolInputError("MCPClient is not open.")
        connection = self._connections.get(name)
        if connection is None:
            raise ToolInputError(f"MCP server {name!r} is not connected.")
        return connection.client

    def _request_limits(
        self,
        timeout_seconds: float | None,
        retries: int | None,
    ) -> tuple[float, int]:
        timeout = self._timeout_seconds if timeout_seconds is None else timeout_seconds
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool):
            raise ToolInputError("timeout_seconds must be a positive number.")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ToolInputError("timeout_seconds must be a finite positive number.")
        retry_count = self._retries if retries is None else require_int(
            retries,
            "retries",
            minimum=0,
            maximum=_MAX_RETRIES,
        )
        return float(timeout), retry_count

    async def _run_with_retry(
        self,
        operation: Callable[[], Awaitable[_T]],
        *,
        timeout_seconds: float,
        retries: int,
        retryable_result: Callable[[_T], bool] | None = None,
    ) -> _T:
        last_exception: Exception | None = None
        for attempt in range(retries + 1):
            try:
                result = await asyncio.wait_for(operation(), timeout=timeout_seconds)
            except TimeoutError as exc:
                last_exception = exc
                if attempt == retries:
                    raise ToolTimeoutError("The MCP request timed out.") from exc
            except Exception as exc:
                last_exception = exc
                if attempt == retries:
                    raise ToolExecutionError("The MCP request failed.", retryable=True) from exc
            else:
                if retryable_result is None or not retryable_result(result) or attempt == retries:
                    return result
            delay = min(self._retry_delay_seconds * (2**attempt), 1.0)
            if delay:
                await asyncio.sleep(delay)
        raise ToolExecutionError("The MCP request failed.", retryable=True) from last_exception


def _validate_server_name(value: str) -> str:
    name = require_text(value, "server_name", max_length=64)
    if not _SERVER_NAME_PATTERN.fullmatch(name):
        raise ToolInputError("server_name must use lowercase letters, digits, '_' or '-'.")
    return name


def _is_retryable_tool_result(result: object) -> bool:
    if not isinstance(result, CallToolResult) or not result.is_error:
        return False
    for block in result.content:
        error_text = getattr(block, "text", None)
        if not isinstance(error_text, str):
            continue
        json_error = re.search(r"\{.*\}\s*$", error_text, flags=re.DOTALL)
        if json_error is None:
            continue
        try:
            payload = json.loads(json_error.group())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("retryable") is True:
            return True
    return False


def _raise_safe_request_error(error: Exception) -> NoReturn:
    if isinstance(error, ToolInputError | ToolExecutionError | ToolTimeoutError):
        raise error
    raise ToolExecutionError("The MCP request failed.", retryable=True) from error
