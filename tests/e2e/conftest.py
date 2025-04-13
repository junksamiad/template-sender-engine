import pytest
import boto3
import json
import os

# --- Configuration (Shared) ---
REGION = "eu-north-1"
DYNAMODB_COMPANY_TABLE_NAME = "ai-multi-comms-company-data-dev"
COMPANY_DATA_SAMPLE_PATH = "samples/recruitment_company_data_record_example_dev.json"

# --- Shared Fixtures ---

@pytest.fixture(scope="session") # Change scope to session for potential reuse
def dynamodb_client():
    """Boto3 DynamoDB client configured for the correct region."""
    print(f"\nCreating DynamoDB client fixture for region: {REGION} (session scope)")
    return boto3.client("dynamodb", region_name=REGION)

# Helper function to format JSON for DynamoDB put_item
# This is a simplified version; a more robust one would handle all types
def format_json_for_dynamodb(data):
    formatted = {}
    for key, value in data.items():
        # Check for bool FIRST, as bool is a subclass of int
        if isinstance(value, bool):
            formatted[key] = {"BOOL": value}
        elif isinstance(value, str):
            formatted[key] = {"S": value}
        elif isinstance(value, (int, float)):
            formatted[key] = {"N": str(value)}
        elif isinstance(value, list):
            # Simple list handling; extend if other types needed
            # Important: Need to handle lists of maps, numbers, bools etc.
            # This simplified version assumes list of strings or simple types for now.
            list_values = []
            for item in value:
                if isinstance(item, str):
                    list_values.append({"S": item})
                elif isinstance(item, bool):
                     list_values.append({"BOOL": item})
                elif isinstance(item, (int, float)):
                     list_values.append({"N": str(item)})
                # Add more types as needed inside lists
                else:
                    # Fallback for unknown list item types (might error or be null)
                    print(f"Warning: Unsupported type in list for key '{key}': {type(item)}")
            formatted[key] = {"L": list_values}
        elif isinstance(value, dict):
            formatted[key] = {"M": format_json_for_dynamodb(value)} # Recursive call for maps
        elif value is None:
             formatted[key] = {"NULL": True} # Handle None as NULL
        # Add handling for other types (bytes, sets) if needed
    return formatted

@pytest.fixture(scope="function")
def setup_e2e_company_data(dynamodb_client, request):
    """Ensures the specific company data record exists for the E2E test and cleans up."""
    print(f"\n--- Fixture Setup: Loading Company Data from {COMPANY_DATA_SAMPLE_PATH} ---")
    try:
        with open(COMPANY_DATA_SAMPLE_PATH, 'r') as f:
            company_data_item = json.load(f)
    except Exception as e:
        pytest.fail(f"Failed to load company data sample: {e}")

    company_id = company_data_item.get("company_id")
    project_id = company_data_item.get("project_id")
    if not company_id or not project_id:
        pytest.fail("Company/Project ID missing in sample data file.")

    print(f"Ensuring company data exists: {company_id}/{project_id} in {DYNAMODB_COMPANY_TABLE_NAME}")
    # Use put_item for simplicity (create or overwrite)
    try:
        formatted_item = format_json_for_dynamodb(company_data_item)
        dynamodb_client.put_item(
            TableName=DYNAMODB_COMPANY_TABLE_NAME,
            Item=formatted_item
        )
        print("Company data put/overwrite successful.")
    except Exception as e:
        pytest.fail(f"Failed to put company data item into DynamoDB: {e}")

    # Teardown function using request.addfinalizer for robustness
    def teardown():
        print(f"\n--- Fixture Teardown: Deleting Company Data {company_id}/{project_id} ---")
        try:
            dynamodb_client.delete_item(
                TableName=DYNAMODB_COMPANY_TABLE_NAME,
                Key={"company_id": {"S": company_id}, "project_id": {"S": project_id}}
            )
            print("Company data deleted successfully.")
        except Exception as e:
            # Log error but don't fail the test run itself on teardown failure
            print(f"Warning: Error during company data cleanup: {e}")

    request.addfinalizer(teardown)

    # Yield the IDs in case a test needs them
    yield company_id, project_id

# Add other shared fixtures or helpers below if needed 