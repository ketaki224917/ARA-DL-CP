"""Small stdio MCP server subprocess used by the MCP client tests."""

from __future__ import annotations

import json
import os
import time

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

server = MCPServer(name="ARA MCP client fixture")
_retry_calls = 0


@server.tool()
def ping() -> str:
    """Return a short fixture response."""
    return f"pong:{os.getpid()}"


@server.tool()
def retry_once() -> str:
    """Return one retryable error, then succeed."""
    global _retry_calls
    _retry_calls += 1
    if _retry_calls == 1:
        error = {"code": "timeout", "message": "Try again.", "retryable": True}
        raise ToolError(json.dumps(error))
    return "retried"


@server.tool()
def slow() -> str:
    """Sleep long enough to trigger a short client timeout."""
    time.sleep(0.2)
    return "slow"


if __name__ == "__main__":
    server.run()
