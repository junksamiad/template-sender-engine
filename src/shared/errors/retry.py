"""
Retry mechanism with exponential backoff for handling transient errors.

This module provides utilities for retrying operations that may fail due to
transient errors, using exponential backoff with jitter.
"""
import random
import time
import functools
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

import structlog

from src.shared.errors.exceptions import categorize_error

# Type variables for the retry function
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

# Get logger
logger = structlog.get_logger(__name__)


class RetryOptions:
    """Configuration options for the retry mechanism."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay_ms: int = 1000,
        max_delay_ms: int = 10000,
        jitter_factor: float = 0.2,
        retryable_errors: Optional[List[str]] = None
    ):
        """
        Initialize retry options.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay_ms: Initial delay in milliseconds
            max_delay_ms: Maximum delay in milliseconds
            jitter_factor: Factor for random jitter (0.0-1.0)
            retryable_errors: List of error categories that should be retried
        """
        self.max_retries = max_retries
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.jitter_factor = jitter_factor
        self.retryable_errors = retryable_errors or [
            "RateLimitError",
            "TimeoutError",
            "ServiceUnavailableError",
            "NetworkError",
            "InternalError"
        ]


def with_retry(func: Callable[..., T], options: Optional[RetryOptions] = None) -> Callable[..., T]:
    """
    Decorator that adds retry logic to a function.
    
    Args:
        func: The function to decorate
        options: Optional retry configuration
        
    Returns:
        Decorated function with retry logic
    """
    retry_options = options or RetryOptions()
    
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        attempt = 0
        last_exception = None
        
        # Get function name safely (handles mocks in tests)
        func_name = getattr(func, "__name__", str(func))
        
        while attempt <= retry_options.max_retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                attempt += 1
                
                # Check if we've exhausted our retries
                if attempt > retry_options.max_retries:
                    logger.error(
                        "Operation failed after maximum retries",
                        exc_info=e,
                        attempt=attempt,
                        max_retries=retry_options.max_retries,
                        function=func_name
                    )
                    raise
                
                # Categorize the error
                error_info = categorize_error(e)
                
                # Check if the error is retryable
                if not error_info["retryable"] or error_info["category"] not in retry_options.retryable_errors:
                    logger.error(
                        "Non-retryable error occurred",
                        exc_info=e,
                        error_category=error_info["category"],
                        error_code=error_info["code"],
                        function=func_name
                    )
                    raise
                
                # Calculate backoff with jitter
                backoff = min(
                    retry_options.initial_delay_ms * (2 ** (attempt - 1)),
                    retry_options.max_delay_ms
                )
                jitter = backoff * retry_options.jitter_factor * (random.random() * 2 - 1)
                delay = max(1, (backoff + jitter) / 1000)  # Convert to seconds
                
                logger.warning(
                    "Retryable error occurred, retrying operation",
                    error=str(e),
                    error_category=error_info["category"],
                    error_code=error_info["code"],
                    attempt=attempt,
                    backoff_seconds=delay,
                    function=func_name
                )
                
                # Wait before retry
                time.sleep(delay)
        
        # We should never reach here due to the raise in the loop
        assert last_exception is not None
        raise last_exception
    
    return wrapper


async def with_retry_async(func, options: Optional[RetryOptions] = None):
    """
    Async version of with_retry for asynchronous functions.
    This is a placeholder for future implementation.
    """
    # This would be implemented for async functions
    # For now, we'll raise NotImplementedError
    raise NotImplementedError("Async retry not implemented yet") 