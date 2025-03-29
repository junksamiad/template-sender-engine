"""
Tests for the logging utility.
"""
import json
import logging
import os
from unittest.mock import patch

import pytest
import structlog

from src.shared.logging import configure_logging, get_logger, redact_sensitive_info


@pytest.mark.unit
@pytest.mark.phase0
def test_configure_logging() -> None:
    """Test that configure_logging sets up logging correctly."""
    with patch.object(structlog, "configure") as mock_configure:
        configure_logging("DEBUG")
        mock_configure.assert_called_once()
        assert logging.getLogger().level == logging.DEBUG


@pytest.mark.unit
@pytest.mark.phase0
def test_get_logger() -> None:
    """Test that get_logger returns a logger with the correct name."""
    configure_logging()
    logger = get_logger("test_logger")
    # Simply check that we get a logger instance back
    assert logger is not None
    # Check that the logger representation contains the expected name
    assert "test_logger" in str(logger)


@pytest.mark.unit
@pytest.mark.phase0
def test_redact_sensitive_info() -> None:
    """Test that redact_sensitive_info correctly redacts sensitive information."""
    data = {
        "name": "test",
        "api_key": "secret-api-key",
        "configs": {
            "token": "secret-token",
            "visible": "visible-config",
        },
        "items": [
            {"id": 1, "password": "secret-password"},
            {"id": 2, "description": "visible-description"},
        ],
    }

    redacted = redact_sensitive_info(data)

    assert redacted["name"] == "test"
    assert redacted["api_key"] == "***REDACTED***"
    assert redacted["configs"]["token"] == "***REDACTED***"
    assert redacted["configs"]["visible"] == "visible-config"
    assert redacted["items"][0]["id"] == 1
    assert redacted["items"][0]["password"] == "***REDACTED***"
    assert redacted["items"][1]["id"] == 2
    assert redacted["items"][1]["description"] == "visible-description" 