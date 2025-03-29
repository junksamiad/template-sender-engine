"""
Circuit breaker pattern implementation for protecting against cascading failures.

This module provides a circuit breaker implementation that can be used to protect
against cascading failures when interacting with external services.
"""
import time
import functools
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Set

import structlog

# Get logger
logger = structlog.get_logger(__name__)

# Type variables
T = TypeVar("T")


class CircuitState(Enum):
    """Possible states for the circuit breaker."""
    CLOSED = "CLOSED"  # Normal operation, requests flow through
    OPEN = "OPEN"  # Failing, requests are blocked
    HALF_OPEN = "HALF_OPEN"  # Testing recovery


class CircuitBreaker:
    """
    Implementation of the circuit breaker pattern.
    
    The circuit breaker prevents cascading failures by stopping requests to a failing
    service and periodically testing if the service has recovered.
    """
    
    # Registry of all circuit breakers to support global operations
    _registry: Dict[str, 'CircuitBreaker'] = {}
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout_seconds: int = 30,
        half_open_max_calls: int = 1,
        excluded_exceptions: Optional[Set[type]] = None
    ):
        """
        Initialize the circuit breaker.
        
        Args:
            name: Name of the circuit (for logging/metrics)
            failure_threshold: Number of failures before opening circuit
            reset_timeout_seconds: Time to wait before testing recovery
            half_open_max_calls: Maximum calls allowed in half-open state
            excluded_exceptions: Exception types that should not count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        self.excluded_exceptions = excluded_exceptions or set()
        
        # State management
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = 0
        self.last_success_time = 0
        self.half_open_calls = 0
        self.total_successes = 0
        self.total_failures = 0
        self.consecutive_successes = 0
        
        # Register this circuit breaker
        CircuitBreaker._registry[name] = self
        
        logger.info(
            "Circuit breaker initialized",
            circuit_name=self.name,
            failure_threshold=self.failure_threshold,
            reset_timeout_seconds=self.reset_timeout_seconds
        )
    
    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Result of the function call
            
        Raises:
            ServiceUnavailableError: When circuit is open
            Exception: Any exception raised by the function
        """
        # Check if circuit is open
        self._check_state()
        
        try:
            # Execute the function
            result = func(*args, **kwargs)
            
            # Record success
            self._record_success()
            
            return result
        except Exception as e:
            # If exception type is excluded, don't count as failure
            if type(e) in self.excluded_exceptions:
                logger.info(
                    "Exception excluded from circuit breaker failure count",
                    circuit_name=self.name,
                    exception_type=type(e).__name__
                )
                raise
            
            # Record failure
            self._record_failure()
            
            # Re-raise the original exception
            raise
    
    def execute_async(self, func, *args, **kwargs):
        """
        Placeholder for executing an async function with circuit breaker protection.
        
        This would be implemented for async functions.
        """
        raise NotImplementedError("Async circuit breaker not implemented yet")
    
    def reset(self) -> None:
        """
        Manually reset the circuit breaker to closed state.
        
        This can be used for administrative purposes to force reset a circuit.
        """
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.half_open_calls = 0
        
        logger.info(
            "Circuit manually reset to CLOSED state",
            circuit_name=self.name,
            previous_state=old_state.value
        )
    
    def force_open(self) -> None:
        """
        Manually force the circuit into the open state.
        
        This can be used for administrative purposes or for testing.
        """
        old_state = self.state
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()
        
        logger.info(
            "Circuit manually forced to OPEN state",
            circuit_name=self.name,
            previous_state=old_state.value
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about the circuit breaker's current state and history.
        
        Returns:
            Dictionary with circuit metrics
        """
        current_time = time.time()
        
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "consecutive_successes": self.consecutive_successes,
            "time_since_last_failure_seconds": (
                current_time - self.last_failure_time if self.last_failure_time > 0 else None
            ),
            "time_since_last_success_seconds": (
                current_time - self.last_success_time if self.last_success_time > 0 else None
            ),
            "half_open_calls": self.half_open_calls,
            "failure_threshold": self.failure_threshold,
            "reset_timeout_seconds": self.reset_timeout_seconds,
            "half_open_max_calls": self.half_open_max_calls,
        }
    
    def _check_state(self) -> None:
        """
        Check and potentially update the circuit state based on current conditions.
        
        Raises:
            ServiceUnavailableError: When circuit is open
        """
        current_time = time.time()
        
        if self.state == CircuitState.OPEN:
            # Check if reset timeout has elapsed
            if current_time - self.last_failure_time >= self.reset_timeout_seconds:
                # Transition to half-open state
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                
                logger.info(
                    "Circuit transitioned to HALF_OPEN state",
                    circuit_name=self.name,
                    open_duration_seconds=current_time - self.last_failure_time
                )
            else:
                # Circuit is still open
                from src.shared.errors.exceptions import ServiceUnavailableError
                
                elapsed = current_time - self.last_failure_time
                remaining = self.reset_timeout_seconds - elapsed
                
                logger.warning(
                    "Circuit is OPEN, rejecting request",
                    circuit_name=self.name,
                    seconds_until_retry=max(0, remaining)
                )
                
                raise ServiceUnavailableError(
                    f"Circuit {self.name} is OPEN, service unavailable",
                    code="CIRCUIT_OPEN",
                    metadata={
                        "circuit_name": self.name,
                        "seconds_until_retry": max(0, remaining)
                    }
                )
        
        elif self.state == CircuitState.HALF_OPEN:
            # Limit calls in half-open state
            if self.half_open_calls >= self.half_open_max_calls:
                from src.shared.errors.exceptions import ServiceUnavailableError
                
                logger.warning(
                    "Circuit is HALF_OPEN but max test calls reached, rejecting request",
                    circuit_name=self.name,
                    half_open_calls=self.half_open_calls,
                    half_open_max_calls=self.half_open_max_calls
                )
                
                raise ServiceUnavailableError(
                    f"Circuit {self.name} is HALF_OPEN and at test call limit",
                    code="CIRCUIT_HALF_OPEN",
                    metadata={
                        "circuit_name": self.name,
                        "half_open_calls": self.half_open_calls,
                        "half_open_max_calls": self.half_open_max_calls
                    }
                )
            
            # Increment the half-open call counter
            self.half_open_calls += 1
    
    def _record_success(self) -> None:
        """Record a successful operation and potentially reset the circuit."""
        self.last_success_time = time.time()
        self.total_successes += 1
        self.consecutive_successes += 1
        
        if self.state == CircuitState.HALF_OPEN:
            # Reset the circuit on success in half-open state
            self.state = CircuitState.CLOSED
            self.failures = 0
            
            logger.info(
                "Circuit RESET to CLOSED state after successful operation",
                circuit_name=self.name
            )
    
    def _record_failure(self) -> None:
        """Record a failed operation and potentially open the circuit."""
        self.failures += 1
        self.total_failures += 1
        self.consecutive_successes = 0
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED and self.failures >= self.failure_threshold:
            # Open the circuit after threshold failures
            self.state = CircuitState.OPEN
            
            logger.warning(
                "Circuit OPENED due to too many failures",
                circuit_name=self.name,
                failures=self.failures,
                failure_threshold=self.failure_threshold
            )
        
        elif self.state == CircuitState.HALF_OPEN:
            # Failures in half-open state immediately open the circuit
            self.state = CircuitState.OPEN
            
            logger.warning(
                "Circuit OPENED from HALF_OPEN state due to failure",
                circuit_name=self.name
            )
    
    @classmethod
    def get_circuit(cls, name: str) -> Optional['CircuitBreaker']:
        """
        Get a registered circuit breaker by name.
        
        Args:
            name: Name of the circuit breaker
            
        Returns:
            Circuit breaker instance or None if not found
        """
        return cls._registry.get(name)
    
    @classmethod
    def get_all_circuits(cls) -> Dict[str, 'CircuitBreaker']:
        """
        Get all registered circuit breakers.
        
        Returns:
            Dictionary mapping circuit breaker names to instances
        """
        return cls._registry.copy()
    
    @classmethod
    def reset_all_circuits(cls) -> None:
        """Reset all registered circuit breakers to CLOSED state."""
        for circuit in cls._registry.values():
            circuit.reset()


def circuit_protected(circuit_breaker: CircuitBreaker):
    """
    Decorator to protect a function with a circuit breaker.
    
    Args:
        circuit_breaker: The circuit breaker instance to use
        
    Returns:
        Decorated function with circuit breaker protection
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return circuit_breaker.execute(func, *args, **kwargs)
        return wrapper
    return decorator 