"""
Error handling framework for the AI Multi-Communications Engine.

This module provides a comprehensive error handling framework including:
- Custom error classes for different error categories
- Error categorization utilities
- Retry mechanisms with exponential backoff
- Circuit breaker implementation
- Error response formatting utilities
"""

from src.shared.errors.exceptions import (
    AIMultiCommsError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    RateLimitError,
    TimeoutError,
    ServiceUnavailableError,
    NetworkError,
    InternalError,
    DataInconsistencyError,
    ConfigurationError,
    AssistantConfigurationError,
    categorize_error
)

from src.shared.errors.retry import (
    RetryOptions,
    with_retry
)

from src.shared.errors.circuit_breaker import CircuitBreaker

from src.shared.errors.response import (
    ErrorResponse,
    get_http_status_for_error,
    format_error_response
) 