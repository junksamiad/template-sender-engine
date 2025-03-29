"""
Custom exception classes for the AI Multi-Communications Engine.

This module defines a hierarchy of custom exceptions used across the application
to provide consistent error handling and categorization.
"""
from typing import Any, Dict, Optional, Type, Union
from enum import Enum, auto


class ErrorCategory(Enum):
    """Categories for error classification."""
    VALIDATION = auto()
    AUTHENTICATION = auto()
    AUTHORIZATION = auto()
    RESOURCE_NOT_FOUND = auto()
    RATE_LIMIT = auto()
    TIMEOUT = auto()
    SERVICE_UNAVAILABLE = auto()
    NETWORK = auto()
    INTERNAL = auto()
    DATA_INCONSISTENCY = auto()
    CONFIGURATION = auto()
    INFRASTRUCTURE = auto()
    TRANSIENT = auto()  # Errors that are likely to be resolved with retries
    PERMANENT = auto()  # Errors that will not be resolved with retries


class AIMultiCommsError(Exception):
    """Base exception class for all AI Multi-Communications Engine errors."""
    
    # Default values that subclasses can override
    default_code = "GENERAL_ERROR"
    default_message = "An error occurred."
    default_category = ErrorCategory.INTERNAL
    retryable = False
    
    def __init__(
        self, 
        message: Optional[str] = None, 
        code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        category: Optional[ErrorCategory] = None
    ):
        """
        Initialize the base error class.
        
        Args:
            message: Human-readable error message
            code: Error code for programmatic identification
            metadata: Additional context about the error
            original_error: Original exception if this is a wrapped error
            category: Error category from the ErrorCategory enum
        """
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.metadata = metadata or {}
        self.original_error = original_error
        self.category = category or self.default_category
        
        # Include original error info in the message if available
        if original_error:
            self.metadata["original_error_type"] = type(original_error).__name__
            self.metadata["original_error_message"] = str(original_error)
        
        super().__init__(self.message)


class ValidationError(AIMultiCommsError):
    """Error raised when input validation fails."""
    default_code = "VALIDATION_ERROR"
    default_message = "Validation failed."
    default_category = ErrorCategory.VALIDATION
    retryable = False


class AuthenticationError(AIMultiCommsError):
    """Error raised when authentication fails."""
    default_code = "AUTHENTICATION_ERROR"
    default_message = "Authentication failed."
    default_category = ErrorCategory.AUTHENTICATION
    retryable = False


class AuthorizationError(AIMultiCommsError):
    """Error raised when authorization fails."""
    default_code = "AUTHORIZATION_ERROR"
    default_message = "Authorization failed."
    default_category = ErrorCategory.AUTHORIZATION
    retryable = False


class ResourceNotFoundError(AIMultiCommsError):
    """Error raised when a requested resource is not found."""
    default_code = "RESOURCE_NOT_FOUND"
    default_message = "Resource not found."
    default_category = ErrorCategory.RESOURCE_NOT_FOUND
    retryable = False


class RateLimitError(AIMultiCommsError):
    """Error raised when rate limits are exceeded."""
    default_code = "RATE_LIMIT_EXCEEDED"
    default_message = "Rate limit exceeded."
    default_category = ErrorCategory.RATE_LIMIT
    retryable = True


class TimeoutError(AIMultiCommsError):
    """Error raised when an operation times out."""
    default_code = "TIMEOUT"
    default_message = "Operation timed out."
    default_category = ErrorCategory.TIMEOUT
    retryable = True


class ServiceUnavailableError(AIMultiCommsError):
    """Error raised when a service is temporarily unavailable."""
    default_code = "SERVICE_UNAVAILABLE"
    default_message = "Service temporarily unavailable."
    default_category = ErrorCategory.SERVICE_UNAVAILABLE
    retryable = True


class NetworkError(AIMultiCommsError):
    """Error raised when a network operation fails."""
    default_code = "NETWORK_ERROR"
    default_message = "Network operation failed."
    default_category = ErrorCategory.NETWORK
    retryable = True


class InternalError(AIMultiCommsError):
    """Error raised when an unexpected internal error occurs."""
    default_code = "INTERNAL_ERROR"
    default_message = "Internal error occurred."
    default_category = ErrorCategory.INTERNAL
    retryable = True


class DataInconsistencyError(AIMultiCommsError):
    """Error raised when data inconsistency is detected."""
    default_code = "DATA_INCONSISTENCY"
    default_message = "Data inconsistency detected."
    default_category = ErrorCategory.DATA_INCONSISTENCY
    retryable = False


class ConfigurationError(AIMultiCommsError):
    """Error raised when a configuration issue is detected."""
    default_code = "CONFIGURATION_ERROR"
    default_message = "Configuration error detected."
    default_category = ErrorCategory.CONFIGURATION
    retryable = False


class AssistantConfigurationError(ConfigurationError):
    """Error raised when an OpenAI assistant configuration issue is detected."""
    default_code = "ASSISTANT_CONFIGURATION_ERROR"
    default_message = "OpenAI assistant configuration error."
    default_category = ErrorCategory.CONFIGURATION
    retryable = False


class CircuitBreakerOpenError(ServiceUnavailableError):
    """Raised when a circuit breaker is open and a request is attempted."""
    default_code = "CIRCUIT_BREAKER_OPEN"
    default_message = "Service circuit breaker is open."
    default_category = ErrorCategory.TRANSIENT


class SQSHeartbeatError(AIMultiCommsError):
    """Raised when there is an issue with the SQS heartbeat mechanism."""
    default_code = "SQS_HEARTBEAT_ERROR"
    default_message = "Error in SQS heartbeat mechanism."
    default_category = ErrorCategory.INFRASTRUCTURE
    retryable = True


# Error categorization utility
def categorize_error(error: Exception) -> Dict[str, Any]:
    """
    Categorize an error by examining its properties.
    
    Args:
        error: The error to categorize
        
    Returns:
        Dictionary containing error category, code, and retryable status
    """
    if isinstance(error, AIMultiCommsError):
        return {
            "category": error.__class__.__name__,
            "code": error.code,
            "retryable": getattr(error, "retryable", False),
            "message": error.message,
            "metadata": error.metadata
        }
    
    # Handle AWS service errors
    if hasattr(error, "response") and hasattr(error.response, "get"):
        error_code = error.response.get("Error", {}).get("Code", "")
        
        # AWS service-specific errors
        if error_code == "ThrottlingException" or error_code == "TooManyRequestsException":
            return {
                "category": "RateLimitError",
                "code": error_code,
                "retryable": True,
                "message": str(error),
                "metadata": {"service": "AWS"}
            }
        elif error_code == "ResourceNotFoundException":
            return {
                "category": "ResourceNotFoundError",
                "code": error_code,
                "retryable": False,
                "message": str(error),
                "metadata": {"service": "AWS"}
            }
        elif error_code == "ValidationException":
            return {
                "category": "ValidationError",
                "code": error_code,
                "retryable": False,
                "message": str(error),
                "metadata": {"service": "AWS"}
            }
        elif error_code == "AccessDeniedException":
            return {
                "category": "AuthorizationError",
                "code": error_code,
                "retryable": False,
                "message": str(error),
                "metadata": {"service": "AWS"}
            }
        elif error_code == "ServiceUnavailable":
            return {
                "category": "ServiceUnavailableError",
                "code": error_code,
                "retryable": True,
                "message": str(error),
                "metadata": {"service": "AWS"}
            }
    
    # Handle HTTP-like errors
    if hasattr(error, "status_code"):
        status_code = error.status_code
        if status_code == 401:
            return {
                "category": "AuthenticationError",
                "code": "UNAUTHORIZED",
                "retryable": False,
                "message": str(error),
                "metadata": {}
            }
        elif status_code == 403:
            return {
                "category": "AuthorizationError",
                "code": "FORBIDDEN",
                "retryable": False,
                "message": str(error),
                "metadata": {}
            }
        elif status_code == 404:
            return {
                "category": "ResourceNotFoundError",
                "code": "NOT_FOUND",
                "retryable": False,
                "message": str(error),
                "metadata": {}
            }
        elif status_code == 429:
            return {
                "category": "RateLimitError",
                "code": "RATE_LIMIT_EXCEEDED",
                "retryable": True,
                "message": str(error),
                "metadata": {}
            }
        elif status_code >= 500:
            return {
                "category": "ServiceUnavailableError",
                "code": "SERVER_ERROR",
                "retryable": True,
                "message": str(error),
                "metadata": {}
            }
    
    # Default categorization for unknown errors
    return {
        "category": "InternalError",
        "code": "UNKNOWN_ERROR",
        "retryable": True,
        "message": str(error),
        "metadata": {}
    } 