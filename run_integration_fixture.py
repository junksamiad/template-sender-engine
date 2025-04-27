import sys
import os
import pytest
import time
import boto3

# Add the project root to the Python path
sys.path.append(os.path.abspath("."))

# Import the fixture directly (we need to recreate it since it's not in a conftest.py)
@pytest.fixture(scope="function")
def dynamodb_client():
    """Boto3 DynamoDB client."""
    return boto3.client("dynamodb", region_name="eu-north-1")

@pytest.fixture(scope="function")
def setup_test_company_config(dynamodb_client):
    """
    Fixture to ensure the specific test company config exists in DynamoDB and cleans it up afterwards.
    Uses hardcoded table name for dev testing.
    """
    DYNAMODB_COMPANY_TABLE_NAME = "ai-multi-comms-company-data-dev"
    SQS_QUEUE_URL = "https://sqs.eu-north-1.amazonaws.com/337909745089/ai-multi-comms-whatsapp-queue-dev"
    
    test_company_id = "ci-aaa-XXX"  # Updated from e2e script 
    test_project_id = "pi-aaa-XXX"  # Updated from e2e script
    config_item = {
        "company_id": {"S": test_company_id},
        "project_id": {"S": test_project_id},
        "project_status": {"S": "active"},  # Ensure it's active for the test
        "config_type": {"S": "project_settings"},  # Assuming this is the type
        "api_key_secret_name": {"S": "dev/api_keys/company/ci-aaa-001"},  # Example secret name structure
        "allowed_channels": {"L": [{"S": "whatsapp"}, {"S": "email"}]},  # Allow whatsapp
        "ai_config": {"M": {  # Added placeholder AI config structure
            "openai_config": {"M": {
                "whatsapp": {"M": {
                    "api_key_reference": {"S": "dev/openai/api_key"},
                    "assistant_id_template_sender": {"S": "asst_placeholderTemplateSender"},
                    # ... other AI settings ...
                }},
                # ... other channels ...
            }}
        }},
        "channel_config": {"M": {  # Added placeholder Channel config structure
             "whatsapp": {"M": {
                "company_whatsapp_number": {"S": "+14155238886"},  # Example Twilio sandbox number
                "whatsapp_credentials_id": {"S": "dev/twilio/whatsapp/creds"}  # Example secret ref
             }}
             # ... other channels ...
        }},
        "routing_config": {"M": {
            "whatsapp": {"M": {
                # Use the hardcoded dev queue URL here
                "sqs_queue_url": {"S": SQS_QUEUE_URL}
            }}
            # Add routing for other channels if needed for other tests
        }},
        "company_name": {"S": "Test Company A"},  # Add other fields potentially needed by router
        "project_name": {"S": "Test Project A1"},
        "company_rep": {"S": "Test Rep"}
    }

    print(f"\nEnsuring test config exists: {test_company_id}/{test_project_id} in table {DYNAMODB_COMPANY_TABLE_NAME}")
    # Use put_item which overwrites if exists
    dynamodb_client.put_item(
        TableName=DYNAMODB_COMPANY_TABLE_NAME,
        Item=config_item
    )
    print(f"DynamoDB put_item call successful for {test_company_id}/{test_project_id}")

    yield test_company_id, test_project_id  # Provide the IDs to the test

    # Teardown: Remove the item
    print(f"\nTearing down test config: {test_company_id}/{test_project_id}")
    try:
        dynamodb_client.delete_item(
            TableName=DYNAMODB_COMPANY_TABLE_NAME,
            Key={
                "company_id": {"S": test_company_id},
                "project_id": {"S": test_project_id}
            }
        )
        print("Company data record deleted.")
    except Exception as e:
        print(f"Error during DynamoDB cleanup: {e}")

# A simple test function that uses the fixture
def test_fixture_in_isolation(setup_test_company_config):
    print("\n--- Running setup_test_company_config fixture in isolation ---")
    
    # Print the returned values
    company_id, project_id = setup_test_company_config
    print(f"Fixture returned: company_id={company_id}, project_id={project_id}")
    
    # Add a delay so we can observe the record in DynamoDB before teardown
    print("Waiting 10 seconds before fixture teardown...")
    time.sleep(10)
    
    # When this function exits, the fixture's teardown will run

if __name__ == "__main__":
    # Run just this test function
    pytest.main(["-xvs", __file__]) 