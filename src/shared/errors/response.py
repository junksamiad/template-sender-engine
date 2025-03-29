"""
Error response formatting utilities for API responses.

This module provides utilities for formatting error responses in a consistent way.
"""
from typing import Any, Dict, Optional, Type, Union
import structlog

from src.shared.errors.exceptions import AIMultiCommsError, categorize_error

# Get logger
logger = structlog.get_logger(__name__)


class ErrorResponse:
    """
    Standard error response format for API endpoints.
    
    This class helps create consistent error responses across the application.
    """
    
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the error response.
        
        Args:
            message: Human-readable error message
            code: Error code for programmatic identification
            status_code: HTTP status code
            request_id: Request ID for correlation
            details: Additional error details
        """
        self.message = message
        self.code = code
        self.status_code = status_code
        self.request_id = request_id
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the error response to a dictionary.
        
        Returns:
            Dictionary representation of the error response
        """
        response = {
            "status": "error",
            "error_code": self.code,
            "message": self.message
        }
        
        if self.request_id:
            response["request_id"] = self.request_id
            
        if self.details:
            response["details"] = self.details
            
        return response


def get_http_status_for_error(error: Exception) -> int:
    """
    Get appropriate HTTP status code for an error.
    
    Args:
        error: The error to get status code for
        
    Returns:
        HTTP status code
    """
    if isinstance(error, AIMultiCommsError):
        error_category = error.__class__.__name__
    else:
        error_info = categorize_error(error)
        error_category = error_info["category"]
    
    status_code_map = {
        "ValidationError": 400,
        "AuthenticationError": 401,
        "AuthorizationError": 403,
        "ResourceNotFoundError": 404,
        "RateLimitError": 429,
        "TimeoutError": 504,
        "ServiceUnavailableError": 503,
        "NetworkError": 502,
        "InternalError": 500,
        "DataInconsistencyError": 500,
        "ConfigurationError": 500,
        "AssistantConfigurationError": 500,
    }
    
    return status_code_map.get(error_category, 500)


def get_sanitized_error_message(error: Exception) -> str:
    """
    Get sanitized error message safe for client responses.
    
    Avoids exposing sensitive information in server errors.
    
    Args:
        error: The error to get message for
        
    Returns:
        Sanitized error message
    """
    if isinstance(error, AIMultiCommsError):
        return error.message
    
    error_info = categorize_error(error)
    
    # For 5xx errors, use generic message to avoid exposing internals
    if error_info["category"] in ["InternalError", "DataInconsistencyError", "ConfigurationError"]:
        return "An internal server error occurred"
        
    if error_info["category"] in ["ServiceUnavailableError", "NetworkError"]:
        return "The service is temporarily unavailable"
    
    if error_info["category"] == "TimeoutError":
        return "The request timed out"
    
    # For 4xx errors, the actual message is usually safe to return
    return error_info["message"]


def format_error_response(
    error: Exception,
    request_id: Optional[str] = None,
    include_details: bool = False
) -> ErrorResponse:
    """
    Format an error into a standard error response.
    
    Args:
        error: The error to format
        request_id: Request ID for correlation
        include_details: Whether to include detailed error information
        
    Returns:
        ErrorResponse object
    """
    status_code = get_http_status_for_error(error)
    message = get_sanitized_error_message(error)
    
    if isinstance(error, AIMultiCommsError):
        code = error.code or error.__class__.__name__
        details = error.metadata if include_details else None
    else:
        error_info = categorize_error(error)
        code = error_info["code"] or error_info["category"]
        
        details = None
        if include_details and status_code < 500:  # Only include details for non-server errors
            details = {k: v for k, v in error_info["metadata"].items() if k != "service"}
    
    return ErrorResponse(
        message=message,
        code=code,
        status_code=status_code,
        request_id=request_id,
        details=details
    ) 