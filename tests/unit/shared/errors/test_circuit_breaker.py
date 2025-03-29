"""Unit tests for the circuit breaker implementation."""
import unittest
from unittest.mock import patch, MagicMock
import time

from src.shared.errors.circuit_breaker import CircuitBreaker, CircuitState, circuit_protected
from src.shared.errors.exceptions import ServiceUnavailableError


class TestCircuitBreaker(unittest.TestCase):
    """Test the circuit breaker functionality."""
    
    def setUp(self):
        """Set up the circuit breaker for each test."""
        self.circuit_breaker = CircuitBreaker(
            name="test-circuit",
            failure_threshold=3,
            reset_timeout_seconds=2,
            half_open_max_calls=2
        )
    
    def test_initial_state(self):
        """Test the initial state of the circuit breaker."""
        self.assertEqual(self.circuit_breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.circuit_breaker.failures, 0)
        self.assertEqual(self.circuit_breaker.name, "test-circuit")
        self.assertEqual(self.circuit_breaker.failure_threshold, 3)
        self.assertEqual(self.circuit_breaker.reset_timeout_seconds, 2)
        self.assertEqual(self.circuit_breaker.half_open_max_calls, 2)
        self.assertEqual(self.circuit_breaker.half_open_calls, 0)
    
    def test_successful_execution(self):
        """Test successful function execution."""
        # Mock function that succeeds
        test_func = MagicMock(return_value="success")
        
        # Execute with circuit breaker
        result = self.circuit_breaker.execute(test_func, "arg1", kwarg1="value1")
        
        # Verify
        self.assertEqual(result, "success")
        test_func.assert_called_once_with("arg1", kwarg1="value1")
        self.assertEqual(self.circuit_breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.circuit_breaker.failures, 0)
    
    def test_circuit_opens_after_failures(self):
        """Test that circuit opens after threshold failures."""
        # Mock function that always fails
        test_func = MagicMock(side_effect=ValueError("Test error"))
        
        # Execute function until circuit opens
        for i in range(self.circuit_breaker.failure_threshold):
            with self.assertRaises(ValueError):
                self.circuit_breaker.execute(test_func)
            
            # Check state after each failure
            if i < self.circuit_breaker.failure_threshold - 1:
                self.assertEqual(self.circuit_breaker.state, CircuitState.CLOSED)
                self.assertEqual(self.circuit_breaker.failures, i + 1)
            else:
                # Last execution should open the circuit
                self.assertEqual(self.circuit_breaker.state, CircuitState.OPEN)
                self.assertEqual(self.circuit_breaker.failures, self.circuit_breaker.failure_threshold)
    
    def test_open_circuit_blocks_calls(self):
        """Test that open circuit blocks calls with ServiceUnavailableError."""
        # First, open the circuit
        self.circuit_breaker.state = CircuitState.OPEN
        self.circuit_breaker.last_failure_time = time.time()
        
        # Mock function that should not be called
        test_func = MagicMock()
        
        # Execute function (should be blocked)
        with self.assertRaises(ServiceUnavailableError) as context:
            self.circuit_breaker.execute(test_func)
        
        # Verify error details
        self.assertEqual(context.exception.code, "CIRCUIT_OPEN")
        self.assertEqual(
            context.exception.message, 
            f"Circuit {self.circuit_breaker.name} is OPEN, service unavailable"
        )
        
        # Function should not have been called
        test_func.assert_not_called()
    
    def test_circuit_transitions_to_half_open_after_timeout(self):
        """Test circuit transition to half-open state after timeout."""
        # Set up circuit in OPEN state
        self.circuit_breaker.state = CircuitState.OPEN
        self.circuit_breaker.last_failure_time = time.time() - (self.circuit_breaker.reset_timeout_seconds + 0.1)
        
        # Mock function
        test_func = MagicMock(return_value="success")
        
        # Execute function
        result = self.circuit_breaker.execute(test_func)
        
        # Verify state transition and execution
        self.assertEqual(self.circuit_breaker.state, CircuitState.CLOSED)  # Success in HALF_OPEN resets to CLOSED
        self.assertEqual(result, "success")
        test_func.assert_called_once()
    
    def test_half_open_state_calls_limited(self):
        """Test that half-open state limits the number of test calls."""
        # Set up circuit in HALF_OPEN state with max calls reached
        self.circuit_breaker.state = CircuitState.HALF_OPEN
        self.circuit_breaker.half_open_calls = self.circuit_breaker.half_open_max_calls
        
        # Mock function that should not be called
        test_func = MagicMock()
        
        # Execute function (should be blocked)
        with self.assertRaises(ServiceUnavailableError) as context:
            self.circuit_breaker.execute(test_func)
        
        # Verify error details
        self.assertEqual(context.exception.code, "CIRCUIT_HALF_OPEN")
        self.assertTrue("at test call limit" in context.exception.message)
        
        # Function should not have been called
        test_func.assert_not_called()
    
    def test_half_open_success_resets_circuit(self):
        """Test that successful execution in half-open state resets the circuit."""
        # Set up circuit in HALF_OPEN state
        self.circuit_breaker.state = CircuitState.HALF_OPEN
        self.circuit_breaker.failures = 3
        
        # Mock function that succeeds
        test_func = MagicMock(return_value="success")
        
        # Execute function
        result = self.circuit_breaker.execute(test_func)
        
        # Verify reset to CLOSED state
        self.assertEqual(self.circuit_breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.circuit_breaker.failures, 0)
        self.assertEqual(result, "success")
    
    def test_half_open_failure_reopens_circuit(self):
        """Test that failure in half-open state reopens the circuit."""
        # Set up circuit in HALF_OPEN state
        self.circuit_breaker.state = CircuitState.HALF_OPEN
        
        # Mock function that fails
        test_func = MagicMock(side_effect=ValueError("Test error"))
        
        # Execute function
        with self.assertRaises(ValueError):
            self.circuit_breaker.execute(test_func)
        
        # Verify return to OPEN state
        self.assertEqual(self.circuit_breaker.state, CircuitState.OPEN)
    
    def test_circuit_protected_decorator(self):
        """Test the circuit_protected decorator."""
        # Create circuit breaker
        circuit = CircuitBreaker(name="decorator-test")
        
        # Define decorated function
        @circuit_protected(circuit)
        def test_function(arg1, arg2=None):
            return f"{arg1}-{arg2}"
        
        # Call decorated function
        result = test_function("hello", arg2="world")
        
        # Verify result
        self.assertEqual(result, "hello-world")
        self.assertEqual(circuit.state, CircuitState.CLOSED)
    
    def test_circuit_protected_decorator_with_failure(self):
        """Test the circuit_protected decorator with failing function."""
        # Create circuit breaker with low threshold
        circuit = CircuitBreaker(name="decorator-fail-test", failure_threshold=1)
        
        # Define decorated function that fails
        @circuit_protected(circuit)
        def failing_function():
            raise ValueError("Decorator test error")
        
        # Call decorated function
        with self.assertRaises(ValueError):
            failing_function()
        
        # Verify circuit is now open
        self.assertEqual(circuit.state, CircuitState.OPEN)
    
    def test_excluded_exceptions(self):
        """Test that excluded exceptions don't count as failures."""
        # Create circuit breaker with excluded exception types
        circuit = CircuitBreaker(
            name="excluded-exceptions-test",
            failure_threshold=1,
            excluded_exceptions={KeyError}
        )
        
        # Cause excluded exception
        with self.assertRaises(KeyError):
            circuit.execute(lambda: {}["nonexistent_key"])
        
        # Verify state is still CLOSED and failure count is 0
        self.assertEqual(circuit.state, CircuitState.CLOSED)
        self.assertEqual(circuit.failures, 0)
        
        # Cause non-excluded exception
        with self.assertRaises(ValueError):
            circuit.execute(lambda: int("not_a_number"))
        
        # Verify state is now OPEN
        self.assertEqual(circuit.state, CircuitState.OPEN)
    
    def test_manual_reset(self):
        """Test manually resetting the circuit breaker."""
        # First, open the circuit
        self.circuit_breaker.state = CircuitState.OPEN
        self.circuit_breaker.failures = 5
        
        # Reset the circuit manually
        self.circuit_breaker.reset()
        
        # Verify circuit is reset
        self.assertEqual(self.circuit_breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.circuit_breaker.failures, 0)
    
    def test_force_open(self):
        """Test manually forcing the circuit open."""
        # Circuit starts closed
        self.assertEqual(self.circuit_breaker.state, CircuitState.CLOSED)
        
        # Force open
        self.circuit_breaker.force_open()
        
        # Verify state
        self.assertEqual(self.circuit_breaker.state, CircuitState.OPEN)
        self.assertGreater(self.circuit_breaker.last_failure_time, 0)
        
        # Verify function calls are blocked
        with self.assertRaises(ServiceUnavailableError):
            self.circuit_breaker.execute(lambda: "test")
    
    def test_get_metrics(self):
        """Test getting circuit breaker metrics."""
        # Create some activity
        self.circuit_breaker.execute(lambda: "success1")
        self.circuit_breaker.execute(lambda: "success2")
        
        try:
            self.circuit_breaker.execute(lambda: 1/0)
        except ZeroDivisionError:
            pass
        
        # Get metrics
        metrics = self.circuit_breaker.get_metrics()
        
        # Verify metrics
        self.assertEqual(metrics["name"], "test-circuit")
        self.assertEqual(metrics["state"], "CLOSED")
        self.assertEqual(metrics["failures"], 1)
        self.assertEqual(metrics["total_successes"], 2)
        self.assertEqual(metrics["total_failures"], 1)
        self.assertEqual(metrics["consecutive_successes"], 0)
        self.assertIsNotNone(metrics["time_since_last_failure_seconds"])
        self.assertIsNotNone(metrics["time_since_last_success_seconds"])
    
    def test_registry_and_get_circuit(self):
        """Test the circuit breaker registry functions."""
        # Create a new circuit breaker
        test_circuit = CircuitBreaker(name="registry-test")
        
        # Retrieve it by name
        retrieved_circuit = CircuitBreaker.get_circuit("registry-test")
        
        # Verify retrieval
        self.assertIs(retrieved_circuit, test_circuit)
        
        # Get all circuits and verify inclusion
        all_circuits = CircuitBreaker.get_all_circuits()
        self.assertIn("registry-test", all_circuits)
        self.assertIn("test-circuit", all_circuits)  # from setUp
    
    def test_reset_all_circuits(self):
        """Test resetting all circuit breakers."""
        # Create several circuit breakers
        circuit1 = CircuitBreaker(name="test-reset-all-1")
        circuit2 = CircuitBreaker(name="test-reset-all-2")
        
        # Force them into various states
        circuit1.force_open()
        circuit2.failures = 2
        
        # Reset all circuits
        CircuitBreaker.reset_all_circuits()
        
        # Verify all are reset
        self.assertEqual(circuit1.state, CircuitState.CLOSED)
        self.assertEqual(circuit1.failures, 0)
        self.assertEqual(circuit2.state, CircuitState.CLOSED)
        self.assertEqual(circuit2.failures, 0)


if __name__ == "__main__":
    unittest.main() 