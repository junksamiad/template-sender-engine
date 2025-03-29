"""
Circuit Breaker Pattern - Usage Example

This example demonstrates how to use the circuit breaker pattern
to protect against failures in external service integrations.
"""
import time
import random
import structlog
from typing import Dict, Any

from src.shared.errors.circuit_breaker import CircuitBreaker, circuit_protected
from src.shared.errors.exceptions import ServiceUnavailableError

# Set up logging
log = structlog.get_logger()


class ExternalServiceClient:
    """Simulated external service client that occasionally fails."""
    
    def __init__(self, failure_rate: float = 0.3):
        """
        Initialize the client.
        
        Args:
            failure_rate: Probability of request failure (0.0-1.0)
        """
        self.failure_rate = failure_rate
        self.request_count = 0
        self.failure_count = 0
        
        # Create circuit breaker for this service
        self.circuit = CircuitBreaker(
            name="external-service",
            failure_threshold=3,
            reset_timeout_seconds=5,
            half_open_max_calls=2
        )
    
    @circuit_protected(circuit=None)  # Will be set in __init__
    def fetch_data(self, resource_id: str) -> Dict[str, Any]:
        """
        Fetch data from the external service.
        
        Args:
            resource_id: ID of the resource to fetch
            
        Returns:
            Dictionary containing the resource data
            
        Raises:
            ServiceUnavailableError: When the service is not responding
            ValueError: When the resource doesn't exist
        """
        # Simulate network latency
        time.sleep(0.1)
        
        # Track request
        self.request_count += 1
        
        # Simulate random failure
        if random.random() < self.failure_rate:
            self.failure_count += 1
            error_type = random.choice(["timeout", "server_error", "not_found"])
            
            if error_type == "timeout":
                raise ServiceUnavailableError(
                    "Request timed out",
                    code="REQUEST_TIMEOUT",
                    metadata={"resource_id": resource_id}
                )
            elif error_type == "server_error":
                raise ServiceUnavailableError(
                    "Server error",
                    code="SERVER_ERROR",
                    metadata={"resource_id": resource_id}
                )
            else:
                raise ValueError(f"Resource not found: {resource_id}")
        
        # Successful response
        return {
            "id": resource_id,
            "name": f"Resource {resource_id}",
            "status": "active",
            "created_at": "2023-03-29T12:00:00Z"
        }


def main():
    """Main function demonstrating circuit breaker usage."""
    # Create service client
    service = ExternalServiceClient(failure_rate=0.5)
    
    # Fix the circuit_protected decorator to use the created circuit
    service.fetch_data.__wrapped__.__closure__[0].cell_contents.circuit_breaker = service.circuit
    
    # Track successful and failed calls
    successes = 0
    failures = 0
    
    # Make a series of requests
    for i in range(20):
        resource_id = f"resource-{i}"
        
        try:
            # Try to fetch data
            data = service.fetch_data(resource_id)
            successes += 1
            
            # Log success
            log.info(
                "Successfully fetched resource",
                resource_id=resource_id,
                resource_name=data["name"]
            )
        except ServiceUnavailableError as e:
            failures += 1
            
            # Log error
            if e.code == "CIRCUIT_OPEN":
                log.warning(
                    "Circuit is open, request blocked",
                    seconds_until_retry=e.metadata.get("seconds_until_retry", "unknown"),
                    circuit_name=service.circuit.name
                )
            else:
                log.error(
                    "Service unavailable",
                    error_code=e.code,
                    error_message=e.message
                )
        except ValueError as e:
            failures += 1
            
            # Log not found error
            log.warning("Resource not found", resource_id=resource_id)
        except Exception as e:
            failures += 1
            
            # Log unexpected error
            log.exception("Unexpected error", error=str(e))
        
        # Print circuit status after each request
        circuit_status = service.circuit.state.value
        circuit_failures = service.circuit.failures
        
        print(f"Request {i+1}: Circuit status = {circuit_status} (Failures: {circuit_failures})")
        
        # Pause between requests to show circuit state changes
        time.sleep(0.5)
    
    # Print final statistics
    print("\n--- Final Statistics ---")
    print(f"Successes: {successes}")
    print(f"Failures: {failures}")
    print(f"Service Metrics:")
    for key, value in service.circuit.get_metrics().items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main() 