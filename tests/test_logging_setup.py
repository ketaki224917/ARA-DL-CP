"""Tests for application logging setup."""

import logging

import pytest

from ara.logging_setup import configure_logging


def test_configure_logging_sets_level(caplog: pytest.LogCaptureFixture) -> None:
    configure_logging("DEBUG")
    logger = logging.getLogger("ara.test")

    with caplog.at_level(logging.DEBUG, logger="ara.test"):
        logger.debug("visible")

    assert "visible" in caplog.text


def test_unknown_log_level_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown logging level"):
        configure_logging("verboseish")

