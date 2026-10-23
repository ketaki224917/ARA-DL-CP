"""Lifecycle and retry tests for the stdio MCP client wrapper."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import psutil
import pytest
from mcp import StdioServerParameters

from ara.mcp_client.client import MCPClient
from ara.mcp_servers.common import ToolInputError, ToolTimeoutError

_FIXTURE_SERVER = Path(__file__).with_name("mcp_stdio_fixture.py")


def test_stdio_client_lists_calls_retries_times_out_and_cleans_up() -> None:
    async def exercise() -> None:
        server_pid: int | None = None
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-u", str(_FIXTURE_SERVER)],
            cwd=str(_FIXTURE_SERVER.parent.parent),
        )

        async with MCPClient(timeout_seconds=10, retries=1, retry_delay_seconds=0) as client:
            await client.connect("fixture", parameters)
            assert client.connected_servers == ("fixture",)
            tools = await client.list_tools("fixture")
            assert {tool.name for tool in tools} == {"ping", "retry_once", "slow"}

            pong = await client.call_tool("fixture", "ping", {})
            assert pong.is_error is False
            assert pong.content[0].text.startswith("pong:")
            server_pid = int(pong.content[0].text.split(":", 1)[1])

            retried = await client.call_tool("fixture", "retry_once", {}, retries=1)
            assert retried.is_error is False
            assert retried.content[0].text == "retried"

            with pytest.raises(ToolTimeoutError):
                await client.call_tool(
                    "fixture",
                    "slow",
                    {},
                    timeout_seconds=0.03,
                    retries=0,
                )
            await asyncio.sleep(0.25)
            still_connected = await client.call_tool("fixture", "ping", {})
            assert still_connected.is_error is False
            assert still_connected.content[0].text.startswith("pong:")

        assert client.connected_servers == ()
        assert server_pid is not None
        for _ in range(40):
            if not psutil.pid_exists(server_pid):
                break
            await asyncio.sleep(0.05)
        assert not psutil.pid_exists(server_pid)

    asyncio.run(exercise())


def test_client_requires_open_connection_and_valid_server_name() -> None:
    async def exercise() -> None:
        client = MCPClient()
        with pytest.raises(ToolInputError, match="must be open"):
            await client.connect(
                "fixture",
                StdioServerParameters(command=sys.executable, args=["-c", "pass"]),
            )
        async with client:
            with pytest.raises(ToolInputError, match="server_name"):
                await client.connect(
                    "../fixture",
                    StdioServerParameters(command=sys.executable, args=["-c", "pass"]),
                )

    asyncio.run(exercise())
