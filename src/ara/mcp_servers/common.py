"""Shared MCP server input validation, error responses, and call logging."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager

_SERVER_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
_ERROR_CODE_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")


class MCPToolError(Exception):
    """Base for safe, machine-readable errors returned by an MCP tool."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        if not isinstance(code, str) or not _ERROR_CODE_PATTERN.fullmatch(code):
            raise ValueError("error code must be lowercase ASCII letters, digits, or underscores")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("error message must not be blank")
        super().__init__(message)
        self.code = code
        self.message = message.strip()
        self.retryable = retryable


class ToolInputError(MCPToolError):
    """Raised when a tool receives invalid caller-provided arguments."""

    def __init__(self, message: str) -> None:
        super().__init__("invalid_argument", message)


class ToolExecutionError(MCPToolError):
    """Raised for a safe, user-facing tool backend failure."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__("backend_error", message, retryable=retryable)


class ToolTimeoutError(ToolExecutionError):
    """Raised when an MCP tool exceeds its configured time limit."""

    def __init__(self, message: str = "The tool request timed out.") -> None:
        MCPToolError.__init__(self, "timeout", message, retryable=True)


def validate_arguments(
    arguments: object,
    *,
    required: Iterable[str] = (),
    optional: Iterable[str] = (),
) -> dict[str, object]:
    """Require an object with known keys and all required fields.

    Value-level checks are deliberately separate so each server can validate
    fields with the appropriate bounds before using them.
    """
    if not isinstance(arguments, Mapping):
        raise ToolInputError("Tool arguments must be an object.")
    required_keys = set(required)
    optional_keys = set(optional)
    if required_keys & optional_keys:
        raise ValueError("required and optional argument names must not overlap")
    if any(not isinstance(key, str) for key in arguments):
        raise ToolInputError("Tool argument names must be strings.")

    supplied_keys = set(arguments)
    missing = sorted(required_keys - supplied_keys)
    unexpected = sorted(supplied_keys - required_keys - optional_keys)
    if missing:
        raise ToolInputError(f"Missing required tool arguments: {', '.join(missing)}.")
    if unexpected:
        raise ToolInputError(f"Unexpected tool arguments: {', '.join(unexpected)}.")
    return dict(arguments)


def require_text(
    value: object,
    name: str,
    *,
    max_length: int,
    min_length: int = 1,
) -> str:
    """Return trimmed text after checking type, length, and NUL characters."""
    if max_length < 1 or min_length < 0 or min_length > max_length:
        raise ValueError("text length bounds are invalid")
    if not isinstance(value, str):
        raise ToolInputError(f"{name} must be text.")
    normalized = value.strip()
    if "\x00" in normalized:
        raise ToolInputError(f"{name} must not contain NUL characters.")
    if len(normalized) < min_length:
        raise ToolInputError(f"{name} must contain at least {min_length} characters.")
    if len(normalized) > max_length:
        raise ToolInputError(f"{name} must contain no more than {max_length} characters.")
    return normalized


def require_int(
    value: object,
    name: str,
    *,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    """Validate an integer while rejecting booleans and enforcing bounds."""
    if minimum < 0 or (maximum is not None and maximum < minimum):
        raise ValueError("integer bounds are invalid")
    if isinstance(value, bool) or not isinstance(value, int):
        raise ToolInputError(f"{name} must be an integer.")
    if value < minimum or (maximum is not None and value > maximum):
        upper = f" and no more than {maximum}" if maximum is not None else ""
        raise ToolInputError(f"{name} must be at least {minimum}{upper}.")
    return value


def require_text_list(
    value: object,
    name: str,
    *,
    max_items: int,
    max_item_length: int,
) -> list[str]:
    """Validate a bounded list of unique, non-blank text values."""
    if max_items < 1 or max_item_length < 1:
        raise ValueError("list bounds must be positive")
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ToolInputError(f"{name} must be a list of text values.")
    if not value:
        raise ToolInputError(f"{name} must contain at least one item.")
    if len(value) > max_items:
        raise ToolInputError(f"{name} must contain no more than {max_items} items.")

    items = [
        require_text(item, f"{name} items", max_length=max_item_length)
        for item in value
    ]
    if len(set(items)) != len(items):
        raise ToolInputError(f"{name} must not contain duplicate items.")
    return items


def get_server_logger(server_name: str) -> logging.Logger:
    """Return a logger in ARA's MCP namespace for a validated server name."""
    if not isinstance(server_name, str) or not _SERVER_NAME_PATTERN.fullmatch(server_name):
        raise ValueError("server_name must be 1-64 lowercase letters, digits, '_' or '-'")
    return logging.getLogger(f"ara.mcp.{server_name}")


def error_payload(error: Exception) -> dict[str, str | bool]:
    """Create a safe JSON-compatible error without leaking internal exceptions."""
    if isinstance(error, MCPToolError):
        return {
            "code": error.code,
            "message": error.message,
            "retryable": error.retryable,
        }
    return {
        "code": "internal_error",
        "message": "The tool failed unexpectedly.",
        "retryable": False,
    }


@contextmanager
def log_tool_call(
    logger: logging.Logger,
    *,
    server_name: str,
    tool_name: str,
) -> Iterator[None]:
    """Log an MCP tool's outcome and duration without logging its arguments."""
    if not isinstance(server_name, str) or not _SERVER_NAME_PATTERN.fullmatch(server_name):
        raise ValueError("server_name is invalid")
    if not isinstance(tool_name, str) or not _SERVER_NAME_PATTERN.fullmatch(tool_name):
        raise ValueError("tool_name is invalid")
    started = time.perf_counter()
    fields = {"mcp_server": server_name, "mcp_tool": tool_name}
    logger.debug("MCP tool started", extra=fields)
    try:
        yield
    except MCPToolError as exc:
        logger.warning(
            "MCP tool failed",
            extra={
                **fields,
                "mcp_error_code": exc.code,
                "mcp_duration_ms": _elapsed_ms(started),
            },
        )
        raise
    except Exception:
        logger.exception(
            "MCP tool failed unexpectedly",
            extra={
                **fields,
                "mcp_error_code": "internal_error",
                "mcp_duration_ms": _elapsed_ms(started),
            },
        )
        raise
    else:
        logger.info(
            "MCP tool completed",
            extra={**fields, "mcp_duration_ms": _elapsed_ms(started)},
        )


def _elapsed_ms(started: float) -> float:
    """Return elapsed wall time in milliseconds, rounded for logs."""
    return round((time.perf_counter() - started) * 1000, 3)
