"""Unit tests for the exceptions module."""
import unittest
from src.shared.errors.exceptions import (
    AIMultiCommsError,
    ValidationError,
    AuthenticationError,
    ResourceNotFoundError,
    categorize_error
)


class TestCustomExceptions(unittest.TestCase):
    """Test custom exceptions and error categorization."""
    
    def test_base_error(self):
        """Test the base AIMultiCommsError class."""
        error = AIMultiCommsError("Test error message")
        self.assertEqual(str(error), "Test error message")
        self.assertEqual(error.message, "Test error message")
        self.assertEqual(error.code, None)
        self.assertEqual(error.metadata, {})
        self.assertEqual(error.original_error, None)
        self.assertEqual(error.category, "AIMultiCommsError")
    
    def test_error_with_code_and_metadata(self):
        """Test creating an error with code and metadata."""
        metadata = {"test_key": "test_value"}
        error = AIMultiCommsError("Test error message", code="TEST_ERROR", metadata=metadata)
        self.assertEqual(error.message, "Test error message")
        self.assertEqual(error.code, "TEST_ERROR")
        self.assertEqual(error.metadata, metadata)
    
    def test_wrapping_original_error(self):
        """Test wrapping an original error."""
        original_error = ValueError("Original error")
        error = AIMultiCommsError(
            "Wrapped error message",
            code="WRAPPED_ERROR",
            original_error=original_error
        )
        
        self.assertEqual(error.message, "Wrapped error message")
        self.assertEqual(error.original_error, original_error)
        self.assertEqual(error.metadata["original_error_type"], "ValueError")
        self.assertEqual(error.metadata["original_error_message"], "Original error")
    
    def test_validation_error(self):
        """Test the ValidationError class."""
        error = ValidationError("Invalid input")
        self.assertEqual(error.message, "Invalid input")
        self.assertEqual(error.category, "ValidationError")
        self.assertFalse(error.retryable)
    
    def test_authentication_error(self):
        """Test the AuthenticationError class."""
        error = AuthenticationError("Invalid credentials")
        self.assertEqual(error.message, "Invalid credentials")
        self.assertEqual(error.category, "AuthenticationError")
        self.assertFalse(error.retryable)
    
    def test_resource_not_found_error(self):
        """Test the ResourceNotFoundError class."""
        error = ResourceNotFoundError("Resource not found")
        self.assertEqual(error.message, "Resource not found")
        self.assertEqual(error.category, "ResourceNotFoundError")
        self.assertFalse(error.retryable)


class TestErrorCategorization(unittest.TestCase):
    """Test error categorization functionality."""
    
    def test_categorize_custom_error(self):
        """Test categorizing a custom error."""
        error = ValidationError("Invalid input", code="INVALID_FORMAT")
        
        error_info = categorize_error(error)
        
        self.assertEqual(error_info["category"], "ValidationError")
        self.assertEqual(error_info["code"], "INVALID_FORMAT")
        self.assertEqual(error_info["retryable"], False)
        self.assertEqual(error_info["message"], "Invalid input")
    
    def test_categorize_aws_error(self):
        """Test categorizing an AWS error."""
        # Mock AWS error
        class MockAwsError(Exception):
            def __init__(self):
                self.response = {
                    "Error": {
                        "Code": "ThrottlingException",
                        "Message": "Rate exceeded"
                    }
                }
        
        error = MockAwsError()
        error_info = categorize_error(error)
        
        self.assertEqual(error_info["category"], "RateLimitError")
        self.assertEqual(error_info["code"], "ThrottlingException")
        self.assertEqual(error_info["retryable"], True)
        self.assertEqual(error_info["metadata"]["service"], "AWS")
    
    def test_categorize_http_error(self):
        """Test categorizing an HTTP-like error."""
        # Mock HTTP error
        class MockHttpError(Exception):
            def __init__(self):
                self.status_code = 429
            def __str__(self):
                return "Too many requests"
        
        error = MockHttpError()
        error_info = categorize_error(error)
        
        self.assertEqual(error_info["category"], "RateLimitError")
        self.assertEqual(error_info["code"], "RATE_LIMIT_EXCEEDED")
        self.assertEqual(error_info["retryable"], True)
        self.assertEqual(error_info["message"], "Too many requests")
    
    def test_categorize_generic_error(self):
        """Test categorizing a generic error."""
        error = ValueError("Invalid value")
        error_info = categorize_error(error)
        
        self.assertEqual(error_info["category"], "InternalError")
        self.assertEqual(error_info["code"], "UNKNOWN_ERROR")
        self.assertEqual(error_info["retryable"], True)
        self.assertEqual(error_info["message"], "Invalid value")


if __name__ == "__main__":
    unittest.main() 