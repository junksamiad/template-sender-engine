import pytest
import boto3
import json
import os
import logging
from botocore.exceptions import ClientError

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

@pytest.fixture(scope="function")
def modify_company_data_inactive_project(setup_e2e_company_data, dynamodb_client, request):
    """
    Pytest fixture to temporarily modify the project_status to 'inactive'
    in the company-data-dev table for the standard test item.
    Depends on setup_e2e_company_data to ensure the item exists.
    Restores the original value during teardown.
    """
    # setup_e2e_company_data yielded the IDs, but we can also use the constants
    company_id, project_id = setup_e2e_company_data # Get IDs yielded by dependent fixture
    logger = logging.getLogger(__name__) # Get logger instance
    logger.info(f"FIXTURE SETUP: Modifying project_status to inactive for {company_id}/{project_id}")
    
    # Use the client yielded by dynamodb_client fixture
    # Note: boto3 client API uses different methods than resource API
    table_name = DYNAMODB_COMPANY_TABLE_NAME # From constants defined in conftest
    original_status = None
    key = {
        "company_id": {"S": company_id},
        "project_id": {"S": project_id}
    }

    try:
        # 1. Get current item to store original status
        response = dynamodb_client.get_item(TableName=table_name, Key=key)
        item = response.get('Item')
        if not item:
            pytest.fail(f"Test item {key} not found in {table_name} during inactive_project fixture setup.")

        original_status = item.get('project_status', {}).get('S')
        if not original_status:
             pytest.fail(f"Could not find 'project_status'(S) in item: {key}")

        logger.info(f"Original project_status: '{original_status}'")

        # Avoid modification if already inactive (e.g., leftover from failed teardown)
        if original_status == "inactive":
            logger.warning("Item project_status is already inactive. Skipping update.")
        else:
            # 2. Update item status to inactive
            logger.info(f"Updating item {key} setting project_status to 'inactive'")
            dynamodb_client.update_item(
                TableName=table_name,
                Key=key,
                UpdateExpression="SET project_status = :inactive_status",
                ExpressionAttributeValues={":inactive_status": {"S": "inactive"}},
                ReturnValues="UPDATED_NEW"
            )
            logger.info("Item project_status updated successfully to inactive.")

    except ClientError as e:
        pytest.fail(f"DynamoDB error during inactive_project fixture setup: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error during inactive_project fixture setup: {e}")

    # Teardown function
    def teardown():
        logger.info(f"FIXTURE TEARDOWN: Restoring project_status for {company_id}/{project_id}")
        if original_status is not None and original_status != "inactive":
            try:
                logger.info(f"Restoring original project_status: '{original_status}'")
                dynamodb_client.update_item(
                    TableName=table_name,
                    Key=key,
                    UpdateExpression="SET project_status = :original_status",
                    ExpressionAttributeValues={":original_status": {"S": original_status}}
                )
                logger.info("Item project_status restored successfully.")
            except ClientError as e:
                 logger.error(f"DynamoDB error during inactive_project fixture teardown: {e}")
            except Exception as e:
                 logger.error(f"Unexpected error during inactive_project fixture teardown: {e}")
        elif original_status == "inactive":
             logger.warning("Original status was inactive; no restore needed.")
        else:
             logger.error("Original project_status was not stored correctly; cannot restore.")

    request.addfinalizer(teardown)
    # Yield control to the test function
    yield # No specific value needed, just setup/teardown 

@pytest.fixture(scope="function")
def modify_company_data_disallowed_channel(setup_e2e_company_data, dynamodb_client, request):
    """
    Pytest fixture to temporarily modify the allowed_channels list to exclude 'whatsapp'
    in the company-data-dev table for the standard test item.
    Depends on setup_e2e_company_data to ensure the item exists.
    Restores the original value during teardown.
    """
    company_id, project_id = setup_e2e_company_data
    logger = logging.getLogger(__name__)
    logger.info(f"FIXTURE SETUP: Modifying allowed_channels to exclude 'whatsapp' for {company_id}/{project_id}")

    table_name = DYNAMODB_COMPANY_TABLE_NAME
    original_channels = None
    # Assuming the expected channels without whatsapp
    modified_channels = [{"S": "sms"}, {"S": "email"}] # DynamoDB List of Strings format
    key = {
        "company_id": {"S": company_id},
        "project_id": {"S": project_id}
    }

    try:
        # 1. Get current item to store original channels
        response = dynamodb_client.get_item(TableName=table_name, Key=key)
        item = response.get('Item')
        if not item:
            pytest.fail(f"Test item {key} not found in {table_name} during disallowed_channel fixture setup.")

        original_channels = item.get('allowed_channels', {}).get('L') # Get List attribute
        if original_channels is None: # Check for None explicitly
             pytest.fail(f"Could not find 'allowed_channels'(L) in item: {key}")

        logger.info(f"Original allowed_channels: {original_channels}")

        # Avoid modification if already modified (e.g., leftover from failed teardown)
        # Simple check: see if whatsapp is already missing
        if not any(d.get('S') == 'whatsapp' for d in original_channels):
            logger.warning("Item allowed_channels already excludes 'whatsapp'. Skipping update.")
        else:
            # 2. Update item with modified channels list
            logger.info(f"Updating item {key} setting allowed_channels to {modified_channels}")
            dynamodb_client.update_item(
                TableName=table_name,
                Key=key,
                UpdateExpression="SET allowed_channels = :modified_list",
                ExpressionAttributeValues={":modified_list": {"L": modified_channels}},
                ReturnValues="UPDATED_NEW"
            )
            logger.info("Item allowed_channels updated successfully.")

    except ClientError as e:
        pytest.fail(f"DynamoDB error during disallowed_channel fixture setup: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error during disallowed_channel fixture setup: {e}")

    # Teardown function
    def teardown():
        logger.info(f"FIXTURE TEARDOWN: Restoring allowed_channels for {company_id}/{project_id}")
        # Check if original_channels was captured and if it actually contained whatsapp
        if original_channels is not None and any(d.get('S') == 'whatsapp' for d in original_channels):
            try:
                logger.info(f"Restoring original allowed_channels: {original_channels}")
                dynamodb_client.update_item(
                    TableName=table_name,
                    Key=key,
                    UpdateExpression="SET allowed_channels = :original_list",
                    ExpressionAttributeValues={":original_list": {"L": original_channels}}
                )
                logger.info("Item allowed_channels restored successfully.")
            except ClientError as e:
                 logger.error(f"DynamoDB error during disallowed_channel fixture teardown: {e}")
            except Exception as e:
                 logger.error(f"Unexpected error during disallowed_channel fixture teardown: {e}")
        elif original_channels is not None:
             logger.warning("Original allowed_channels list did not contain whatsapp; no restore needed.")
        else:
             logger.error("Original allowed_channels was not stored correctly; cannot restore.")

    request.addfinalizer(teardown)
    yield # No specific value needed, just setup/teardown 