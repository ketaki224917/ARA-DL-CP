"""Tests for shared MCP server validation, errors, and logging."""

import logging

import pytest

from ara.mcp_servers.common import (
    MCPToolError,
    ToolInputError,
    ToolNotFoundError,
    ToolTimeoutError,
    error_payload,
    get_server_logger,
    log_tool_call,
    require_int,
    require_text,
    require_text_list,
    validate_arguments,
)


def test_validate_arguments_rejects_missing_unexpected_and_non_object_inputs() -> None:
    assert validate_arguments(
        {"query": "retrieval", "limit": 4},
        required={"query"},
        optional={"limit"},
    ) == {"query": "retrieval", "limit": 4}

    with pytest.raises(ToolInputError, match="Missing required"):
        validate_arguments({}, required={"query"})
    with pytest.raises(ToolInputError, match="Unexpected"):
        validate_arguments({"query": "retrieval", "extra": True}, required={"query"})
    with pytest.raises(ToolInputError, match="must be an object"):
        validate_arguments(["query"], required={"query"})


@pytest.mark.parametrize("value", [None, 10, "  ", "a\x00b"])
def test_require_text_rejects_invalid_values(value: object) -> None:
    with pytest.raises(ToolInputError):
        require_text(value, "query", max_length=20)


def test_require_text_trims_and_enforces_bounds() -> None:
    assert require_text("  search this  ", "query", max_length=20) == "search this"
    with pytest.raises(ToolInputError, match="no more than"):
        require_text("too long", "query", max_length=3)


@pytest.mark.parametrize("value", [True, "4", 0, 11])
def test_require_int_rejects_bool_wrong_type_and_out_of_range(value: object) -> None:
    with pytest.raises(ToolInputError):
        require_int(value, "limit", minimum=1, maximum=10)


def test_require_text_list_checks_limits_and_duplicates() -> None:
    assert require_text_list(["a", "b"], "chunk_ids", max_items=3, max_item_length=20) == [
        "a",
        "b",
    ]
    with pytest.raises(ToolInputError, match="duplicate"):
        require_text_list(["a", " a "], "chunk_ids", max_items=3, max_item_length=20)


def test_error_payload_does_not_leak_unexpected_exception_text() -> None:
    assert error_payload(ToolNotFoundError("No matching chunk was found.")) == {
        "code": "not_found",
        "message": "No matching chunk was found.",
        "retryable": False,
    }
    assert error_payload(ToolTimeoutError()) == {
        "code": "timeout",
        "message": "The tool request timed out.",
        "retryable": True,
    }
    assert error_payload(RuntimeError("private endpoint token")) == {
        "code": "internal_error",
        "message": "The tool failed unexpectedly.",
        "retryable": False,
    }
    with pytest.raises(ValueError, match="error code"):
        MCPToolError("bad code", "message")


def test_tool_logger_names_are_scoped_and_validated() -> None:
    assert get_server_logger("rag-server").name == "ara.mcp.rag-server"
    with pytest.raises(ValueError, match="server_name"):
        get_server_logger("../bad")


def test_log_tool_call_records_success_and_safe_failure(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("ara.mcp.test")
    with caplog.at_level(logging.DEBUG, logger=logger.name):
        with log_tool_call(logger, server_name="rag", tool_name="search"):
            pass
        with pytest.raises(ToolInputError):
            with log_tool_call(logger, server_name="rag", tool_name="search"):
                raise ToolInputError("invalid query")

    assert [record.message for record in caplog.records] == [
        "MCP tool started",
        "MCP tool completed",
        "MCP tool started",
        "MCP tool failed",
    ]
    assert caplog.records[-1].mcp_error_code == "invalid_argument"
    assert caplog.records[-1].mcp_duration_ms >= 0
