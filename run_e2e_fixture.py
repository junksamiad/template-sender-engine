import sys
import os
import pytest
import time

# Add the project root to the Python path to import the fixture
sys.path.append(os.path.abspath("."))

# Import the fixture directly from the conftest module
from tests.e2e.conftest import setup_e2e_company_data, dynamodb_client

# A simple test function that uses the fixture
def test_fixture_in_isolation():
    print("\n--- Running setup_e2e_company_data fixture in isolation ---")
    
    # Call the fixture directly
    company_id, project_id = setup_e2e_company_data(dynamodb_client(), None)
    
    # Print the returned values
    print(f"Fixture returned: company_id={company_id}, project_id={project_id}")
    
    # Add a delay so we can observe the record in DynamoDB before teardown
    print("Waiting 10 seconds before fixture teardown...")
    time.sleep(10)
    
    # When this function exits, the fixture's teardown will run

if __name__ == "__main__":
    # Run just this test function
    pytest.main(["-xvs", __file__]) 