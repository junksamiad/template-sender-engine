import sys
import os
import pytest

if __name__ == "__main__":
    """
    Simple script to run a specific test file with explicit options.
    Usage: python run_single_test.py [test_file_path]
    Example: python run_single_test.py tests/e2e/test_error_paths.py::test_processor_failure_missing_secret
    """
    
    if len(sys.argv) < 2:
        print("Please specify the test file or test to run.")
        print("Example: python run_single_test.py tests/e2e/test_error_paths.py::test_processor_failure_missing_secret")
        sys.exit(1)
    
    test_path = sys.argv[1]
    
    # Add verbose option, show output, and don't exit on first failure
    pytest_args = ["-xvs", test_path]
    
    # Run the specified test
    print(f"Running test: {test_path}")
    result = pytest.main(pytest_args)
    
    print(f"\nTest run complete with exit code: {result}") 