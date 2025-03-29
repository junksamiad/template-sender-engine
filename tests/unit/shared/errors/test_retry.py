"""Unit tests for the retry mechanism."""
import unittest
from unittest.mock import patch, MagicMock, call

from src.shared.errors.retry import RetryOptions, with_retry
from src.shared.errors.exceptions import (
    AIMultiCommsError,
    RateLimitError,
    ValidationError
)


class TestRetryMechanism(unittest.TestCase):
    """Test the retry mechanism functionality."""
    
    def test_retry_options_default(self):
        """Test default RetryOptions."""
        options = RetryOptions()
        
        self.assertEqual(options.max_retries, 3)
        self.assertEqual(options.initial_delay_ms, 1000)
        self.assertEqual(options.max_delay_ms, 10000)
        self.assertEqual(options.jitter_factor, 0.2)
        self.assertIn("RateLimitError", options.retryable_errors)
        self.assertIn("TimeoutError", options.retryable_errors)
        self.assertIn("ServiceUnavailableError", options.retryable_errors)
        self.assertIn("NetworkError", options.retryable_errors)
        self.assertIn("InternalError", options.retryable_errors)
    
    def test_retry_options_custom(self):
        """Test custom RetryOptions."""
        options = RetryOptions(
            max_retries=5,
            initial_delay_ms=500,
            max_delay_ms=5000,
            jitter_factor=0.1,
            retryable_errors=["RateLimitError"]
        )
        
        self.assertEqual(options.max_retries, 5)
        self.assertEqual(options.initial_delay_ms, 500)
        self.assertEqual(options.max_delay_ms, 5000)
        self.assertEqual(options.jitter_factor, 0.1)
        self.assertEqual(options.retryable_errors, ["RateLimitError"])
    
    @patch('time.sleep')
    def test_with_retry_success_first_attempt(self, mock_sleep):
        """Test successful function execution on first attempt."""
        # Mock function that succeeds
        test_func = MagicMock(return_value="success")
        
        # Apply retry decorator
        decorated_func = with_retry(test_func)
        
        # Call the decorated function
        result = decorated_func("arg1", kwarg1="value1")
        
        # Verify
        self.assertEqual(result, "success")
        test_func.assert_called_once_with("arg1", kwarg1="value1")
        mock_sleep.assert_not_called()
    
    @patch('time.sleep')
    def test_with_retry_success_after_retries(self, mock_sleep):
        """Test successful function execution after retries."""
        # Mock function that fails twice then succeeds
        test_func = MagicMock(side_effect=[
            RateLimitError("Rate limit exceeded", code="RATE_LIMIT"),
            RateLimitError("Rate limit exceeded", code="RATE_LIMIT"),
            "success"
        ])
        
        # Apply retry decorator with custom options
        decorated_func = with_retry(test_func, options=RetryOptions(max_retries=3))
        
        # Call the decorated function
        result = decorated_func()
        
        # Verify
        self.assertEqual(result, "success")
        self.assertEqual(test_func.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # Sleep called between retries
    
    @patch('time.sleep')
    def test_with_retry_max_retries_reached(self, mock_sleep):
        """Test function that fails even after max retries."""
        # Mock function that always fails with a retryable error
        error = RateLimitError("Rate limit exceeded", code="RATE_LIMIT")
        test_func = MagicMock(side_effect=error)
        
        # Apply retry decorator
        decorated_func = with_retry(test_func, options=RetryOptions(max_retries=2))
        
        # Call the decorated function (should raise after max retries)
        with self.assertRaises(RateLimitError):
            decorated_func()
        
        # Verify
        self.assertEqual(test_func.call_count, 3)  # Initial + 2 retries
        self.assertEqual(mock_sleep.call_count, 2)  # Sleep called between retries
    
    @patch('time.sleep')
    def test_non_retryable_error_raises_immediately(self, mock_sleep):
        """Test non-retryable error raises immediately without retry."""
        # Mock function that fails with a non-retryable error
        error = ValidationError("Invalid input", code="INVALID_INPUT")
        test_func = MagicMock(side_effect=error)
        
        # Apply retry decorator
        decorated_func = with_retry(test_func)
        
        # Call the decorated function (should raise immediately)
        with self.assertRaises(ValidationError):
            decorated_func()
        
        # Verify
        test_func.assert_called_once()  # Only called once
        mock_sleep.assert_not_called()  # No sleep, no retry


if __name__ == "__main__":
    unittest.main() 