"""
Logging utilities for the AI Multi-Communications Engine.
"""
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

import structlog


def configure_logging(log_level: str = None) -> None:
    """
    Configure logging for the application.

    Args:
        log_level: The log level to use. Defaults to the LOG_LEVEL environment variable or INFO.
    """
    log_level = log_level or os.environ.get("LOG_LEVEL", "INFO")
    numeric_level = getattr(logging, log_level)
    
    # Explicitly set root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Configure basic logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
        force=True,  # Force reconfiguration
    )

    # Configure structlog to output JSON logs for easy CloudWatch parsing
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger with the given name.

    Args:
        name: The name of the logger.

    Returns:
        A structured logger.
    """
    # Ensure logging is configured
    if not structlog.is_configured():
        configure_logging()
        
    # Get a properly configured logger
    return structlog.stdlib.get_logger(name)


def redact_sensitive_info(data: Dict[str, Any], sensitive_keys: list = None) -> Dict[str, Any]:
    """
    Redact sensitive information from a dictionary.

    Args:
        data: The dictionary to redact.
        sensitive_keys: A list of sensitive keys to redact. Defaults to a standard list.

    Returns:
        The redacted dictionary.
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "api_key",
            "password",
            "secret",
            "token",
            "auth",
            "credential",
            "access_key",
            "secret_key",
        ]

    result = {}

    for key, value in data.items():
        if any(sensitive_term in key.lower() for sensitive_term in sensitive_keys):
            result[key] = "***REDACTED***"
        elif isinstance(value, dict):
            result[key] = redact_sensitive_info(value, sensitive_keys)
        elif isinstance(value, list):
            result[key] = [
                redact_sensitive_info(item, sensitive_keys) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value

    return result 