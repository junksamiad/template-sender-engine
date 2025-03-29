"""
Custom exception classes for the AI Multi-Communications Engine.

This module defines a hierarchy of custom exceptions used across the application
to provide consistent error handling and categorization.
"""
from typing import Any, Dict, Optional, Type, Union


class AIMultiCommsError(Exception):
    """Base exception class for all AI Multi-Communications Engine errors."""
    
    def __init__(
        self, 
        message: str, 
        code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        """
        Initialize the base error class.
        
        Args:
            message: Human-readable error message
            code: Error code for programmatic identification
            metadata: Additional context about the error
            original_error: Original exception if this is a wrapped error
        """
        self.message = message
        self.code = code
        self.metadata = metadata or {}
        self.original_error = original_error
        self.category = self.__class__.__name__
        
        # Include original error info in the message if available
        if original_error:
            self.metadata["original_error_type"] = type(original_error).__name__
            self.metadata["original_error_message"] = str(original_error)
        
        super().__init__(message)


class ValidationError(AIMultiCommsError):
    """Error raised when input validation fails."""
    retryable = False


class AuthenticationError(AIMultiCommsError):
    """Error raised when authentication fails."""
    retryable = False


class AuthorizationError(AIMultiCommsError):
    """Error raised when authorization fails."""
    retryable = False


class ResourceNotFoundError(AIMultiCommsError):
    """Error raised when a requested resource is not found."""
    retryable = False


class RateLimitError(AIMultiCommsError):
    """Error raised when rate limits are exceeded."""
    retryable = True


class TimeoutError(AIMultiCommsError):
    """Error raised when an operation times out."""
    retryable = True


class ServiceUnavailableError(AIMultiCommsError):
    """Error raised when a service is unavailable."""
    retryable = True


class NetworkError(AIMultiCommsError):
    """Error raised when a network operation fails."""
    retryable = True


class InternalError(AIMultiCommsError):
    """Error raised when an unexpected internal error occurs."""
    retryable = True


class DataInconsistencyError(AIMultiCommsError):
    """Error raised when data inconsistency is detected."""
    retryable = False


class ConfigurationError(AIMultiCommsError):
    """Error raised when a configuration issue is detected."""
    retryable = False


class AssistantConfigurationError(ConfigurationError):
    """Error raised when an OpenAI assistant configuration issue is detected."""
    retryable = False


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