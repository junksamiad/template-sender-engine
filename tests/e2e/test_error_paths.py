import pytest
import requests
import boto3
import uuid
import time
import os
import logging
import json
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# --- Configuration ---
# Fetch API details and table names from environment variables or use defaults
# Ensure these are set in your test environment (e.g., .env file, export)
# API_URL = os.environ.get("E2E_TEST_API_URL", "YOUR_API_URL_HERE") # Replace default if not set via ENV
# API_KEY = os.environ.get("E2E_TEST_API_KEY", "YOUR_API_KEY_HERE") # Replace default if not set via ENV
API_URL = "https://xlijn1k4xh.execute-api.eu-north-1.amazonaws.com/dev/initiate-conversation" # Hardcoded from happy path (added endpoint)
API_KEY = "YbgTABlGlg6s2YZ9gcyuB4AUhi5jJcC05yeKcCWR" # Hardcoded from happy path

# if API_URL == "YOUR_API_URL_HERE" or API_KEY == "YOUR_API_KEY_HERE":
#      # Consider using pytest.skip or fail if config is missing and not defaulted reasonably
#      print("Warning: E2E_TEST_API_URL or E2E_TEST_API_KEY not set. Using placeholders.")

COMPANY_DATA_TABLE = "ai-multi-comms-company-data-dev" # Updated table name
CONVERSATIONS_TABLE = "ai-multi-comms-conversations-dev" # Updated table name
# Using identifiers from samples/recruitment_company_data_record_example_dev.json
TEST_COMPANY_ID = "ci-aaa-001"
TEST_PROJECT_ID = "pi-aaa-001"
# Define the invalid reference to use during the test
INVALID_SECRET_REF = "invalid/secret/ref/for/e2e/testing"
# Assumed GSI name for polling conversations by request_id
CONVERSATIONS_REQUEST_ID_GSI = "request_id-index" # Adjust if GSI name is different

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Configure basic logging for visibility

# --- Helper Functions ---

# Consider moving helpers to tests/e2e/conftest.py if reused across test files
_dynamodb_resource = None

def get_dynamodb_resource():
    """Gets a cached DynamoDB resource."""
    global _dynamodb_resource
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource('dynamodb')
    return _dynamodb_resource

def get_dynamodb_table(table_name):
    """Gets a DynamoDB table object."""
    dynamodb = get_dynamodb_resource()
    return dynamodb.Table(table_name)

# --- Fixtures ---

@pytest.fixture(scope="function")
def modify_company_data_invalid_openai_secret(request):
    """
    Pytest fixture to temporarily modify the OpenAI secret reference
    in the company-data-dev table for a specific test item.
    Restores the original value during teardown.
    """
    logger.info(f"FIXTURE SETUP: Modifying OpenAI secret ref for {TEST_COMPANY_ID}/{TEST_PROJECT_ID}")
    table = get_dynamodb_table(COMPANY_DATA_TABLE)
    original_secret_ref = None
    key = {"company_id": TEST_COMPANY_ID, "project_id": TEST_PROJECT_ID}
    update_path = "ai_config.openai_config.whatsapp.api_key_reference" # Path to the attribute

    try:
        # 1. Get current item to store original value
        response = table.get_item(Key=key)
        item = response.get('Item')
        if not item:
            pytest.fail(f"Test item not found in {COMPANY_DATA_TABLE}: {key}")

        # Safely navigate the nested structure to get the original value
        try:
            original_secret_ref = item['ai_config']['openai_config']['whatsapp']['api_key_reference']
        except KeyError:
             pytest.fail(f"Could not find nested key '{update_path}' in item: {key}")

        if not isinstance(original_secret_ref, str):
             pytest.fail(f"Original value at '{update_path}' is not a string: {original_secret_ref}")

        logger.info(f"Original OpenAI secret reference: '{original_secret_ref}'")
        # Avoid modification if it's already the invalid ref (e.g., leftover from failed teardown)
        if original_secret_ref == INVALID_SECRET_REF:
            logger.warning("Item already has the invalid secret ref. Skipping update.")
        else:
            # 2. Update item with invalid ref
            logger.info(f"Updating item {key} with invalid secret ref: '{INVALID_SECRET_REF}' at path '{update_path}'")
            table.update_item(
                Key=key,
                UpdateExpression=f"SET {update_path} = :invalid_ref",
                ExpressionAttributeValues={":invalid_ref": INVALID_SECRET_REF},
                ReturnValues="UPDATED_NEW" # Optional: confirm change
            )
            logger.info("Item updated successfully.")

    except ClientError as e:
        pytest.fail(f"DynamoDB error during fixture setup: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error during fixture setup: {e}")

    # Teardown function using request.addfinalizer
    def teardown():
        logger.info(f"FIXTURE TEARDOWN: Restoring OpenAI secret ref for {TEST_COMPANY_ID}/{TEST_PROJECT_ID}")
        if original_secret_ref is not None and original_secret_ref != INVALID_SECRET_REF:
            try:
                logger.info(f"Restoring original OpenAI secret reference: '{original_secret_ref}'")
                table.update_item(
                    Key=key,
                    UpdateExpression=f"SET {update_path} = :original_ref",
                    ExpressionAttributeValues={":original_ref": original_secret_ref}
                )
                logger.info("Item restored successfully.")
            except ClientError as e:
                 # Log error but don't fail the test run itself on teardown failure
                 logger.error(f"DynamoDB error during fixture teardown: {e}")
            except Exception as e:
                 logger.error(f"Unexpected error during fixture teardown: {e}")
        elif original_secret_ref == INVALID_SECRET_REF:
             logger.warning("Original ref was the invalid ref; no restore needed.")
        else:
             # This case should ideally not be reached if setup succeeded
             logger.error("Original secret reference was not stored correctly; cannot restore.")

    request.addfinalizer(teardown)
    # Yield control to the test function
    # We don't need to yield a value, just manage setup/teardown
    yield

# --- Polling Function ---

# Define the LSI name as a constant
CONVERSATIONS_CREATED_AT_LSI = "created-at-index" # LSI defined in template.yaml

def poll_conversation_status(primary_channel_key, request_id, expected_status, test_start_time_iso, timeout=90, interval=10):
    """
    Polls the conversations table using the created-at-index LSI and waits
    for the specific request_id to reach the expected_status.

    Args:
        primary_channel_key (str): The HASH key for the table/LSI (e.g., recipient_tel).
        request_id (str): The request_id to filter for within the query results.
        expected_status (str): The target conversation_status.
        test_start_time_iso (str): ISO 8601 timestamp string from just before the test started.
        timeout (int): Maximum time to poll in seconds.
        interval (int): Time to wait between polls in seconds.

    Returns:
        dict or None: The DynamoDB item if found with the expected status,
                      or the item if a terminal status is found unexpectedly,
                      or None if timeout occurs.

    Raises:
        AssertionError: If the assumed LSI does not exist or query fails unexpectedly.
    """
    logger.info(
        f"Polling '{CONVERSATIONS_TABLE}' table (using LSI '{CONVERSATIONS_CREATED_AT_LSI}') for "
        f"primary_channel: '{primary_channel_key}', request_id: '{request_id}', "
        f"expecting status: '{expected_status}', querying after: '{test_start_time_iso}'"
    )
    table = get_dynamodb_table(CONVERSATIONS_TABLE)
    start_time = time.time()
    # Define terminal states to stop polling early if an unexpected final state is reached
    terminal_statuses = {
        "failed_secrets_fetch", "failed_to_process_ai", "failed_to_send_message",
        "failed_unknown", "initial_message_sent"
    }

    while time.time() - start_time < timeout:
        try:
             # Query the LSI using primary_channel and created_at range
             response = table.query(
                 IndexName=CONVERSATIONS_CREATED_AT_LSI,
                 KeyConditionExpression=
                     boto3.dynamodb.conditions.Key('primary_channel').eq(primary_channel_key) & 
                     boto3.dynamodb.conditions.Key('created_at').gt(test_start_time_iso),
                 ScanIndexForward=False, # Get newest items first to find our request sooner
                 Limit=10 # Limit results per query page
             )
             items = response.get('Items', [])
             logger.debug(f"Query returned {len(items)} items for primary_channel '{primary_channel_key}' after {test_start_time_iso}.")

             # Filter results client-side for the specific request_id
             matched_item = None
             for item in items:
                 if item.get('request_id') == request_id:
                     matched_item = item
                     break # Found our item

             if matched_item:
                 current_status = matched_item.get('conversation_status')
                 logger.info(f"Found item for request_id '{request_id}'. Current status: '{current_status}'")

                 if current_status == expected_status:
                     logger.info(f"Expected status '{expected_status}' found.")
                     return matched_item
                 elif current_status in terminal_statuses:
                     logger.warning(f"Found terminal status '{current_status}' which was not the expected '{expected_status}'. Returning item.")
                     return matched_item # Return item for inspection by the test
                 # else: status is not terminal and not expected yet, continue polling
             # else: No item matching request_id found in this query page, continue polling

        except ClientError as e:
             # Specifically check if the LSI doesn't exist
             if e.response['Error']['Code'] == 'ResourceNotFoundException':
                  pytest.fail(f"DynamoDB LSI '{CONVERSATIONS_CREATED_AT_LSI}' not found on table '{CONVERSATIONS_TABLE}'. Polling cannot proceed.")
             # Handle other potential errors (e.g., ValidationException if query params wrong)
             else:
                  logger.error(f"Error querying DynamoDB LSI '{CONVERSATIONS_CREATED_AT_LSI}': {e}. Retrying...")
             # Continue loop on other potentially transient errors

        except Exception as e:
            logger.error(f"Unexpected error during polling: {e}. Retrying...")

        logger.debug(f"Status not yet '{expected_status}'. Waiting {interval}s...")
        time.sleep(interval)

    logger.error(f"Timeout ({timeout}s) reached waiting for status '{expected_status}' for request_id '{request_id}' on primary_channel '{primary_channel_key}'")
    return None

# --- Test Cases ---

def test_processor_failure_missing_secret(setup_e2e_company_data, modify_company_data_invalid_openai_secret):
    """
    E2E Test: Verify processor handles missing OpenAI secret correctly.
    - Ensures company data exists via setup_e2e_company_data fixture.
    - Modifies company data to point OpenAI key ref to an invalid secret.
    - Sends a valid request via API Gateway.
    - Asserts API response is 200 OK.
    - Polls conversations table until status is 'failed_secrets_fetch'.
    - Requires manual check: No WhatsApp message should be received.
    """
    # Fixtures are requested by adding their names as arguments.
    # setup_e2e_company_data runs first (if not already run for the function),
    # then modify_company_data_invalid_openai_secret runs.
    request_id = str(uuid.uuid4()) # Valid UUID
    logger.info(f"--- Starting Test: test_processor_failure_missing_secret (Request ID: {request_id}) ---")

    # Prepare Request Payload
    # Define recipient_tel here as it's needed for polling
    recipient_tel = "+447111222333"
    payload = {
      "company_data": {
        "company_id": TEST_COMPANY_ID,
        "project_id": TEST_PROJECT_ID
      },
      "recipient_data": {
        "recipient_first_name": "Test",
        "recipient_last_name": "SecretFail",
        "recipient_tel": recipient_tel, # Use the variable
        "recipient_email": "test.secretfail@example.com",
        "comms_consent": True
      },
      "project_data": {
         "jobID": "e2e-test-job-001",
         "jobRole": "Secret Tester"
      },
      "request_data": {
        "request_id": request_id,
        "channel_method": "whatsapp",
        "initial_request_timestamp": datetime.now(timezone.utc).isoformat()
      }
    }
    logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")

    # Record start time just before sending the request
    test_start_time_iso = datetime.now(timezone.utc).isoformat()
    time.sleep(0.1) # Ensure slight delay so query finds items created after this

    # Send Request to API Gateway
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }
    api_response = None
    try:
        logger.info(f"Sending POST request to {API_URL}")
        api_response = requests.post(API_URL, headers=headers, json=payload, timeout=20) # Add timeout
        logger.info(f"API Response Status Code: {api_response.status_code}")
        api_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # Assert API accepted the request (synchronous part)
        assert api_response.status_code == 200, f"API Gateway returned {api_response.status_code}, expected 200."
        # Optional: Check response body contains request_id
        try:
            response_data = api_response.json()
            assert response_data.get("request_id") == request_id, "Response body did not contain matching request_id"
        except json.JSONDecodeError:
            pytest.fail("API response was not valid JSON.")

    except requests.exceptions.Timeout:
         pytest.fail(f"API request timed out after 20 seconds.")
    except requests.exceptions.RequestException as e:
        # Log response body if available for debugging
        response_text = e.response.text if e.response is not None else "No response body"
        logger.error(f"API Request failed: {e}. Response: {response_text}")
        pytest.fail(f"API request failed: {e}")

    # Poll DynamoDB for the expected final status ('failed_secrets_fetch')
    logger.info("Polling DynamoDB conversations table for final status...")
    final_item = poll_conversation_status(
        primary_channel_key=recipient_tel, # Pass the phone number
        request_id=request_id,
        expected_status="failed_secrets_fetch",
        test_start_time_iso=test_start_time_iso, # Pass the start time
        timeout=120,
        interval=15
    )

    # Assert the polling was successful and the status is correct
    assert final_item is not None, \
        f"Polling timed out or failed to find record for request_id '{request_id}'"

    final_status = final_item.get("conversation_status")
    assert final_status == "failed_secrets_fetch", \
        f"Final conversation_status was '{final_status}', expected 'failed_secrets_fetch'. Item: {final_item}"

    # --- Optional: Add DLQ check here if desired ---
    # logger.info("Skipping DLQ check for now.")

    logger.info(f"--- Test Passed: test_processor_failure_missing_secret (Request ID: {request_id}) ---")
    print(f"\nMANUAL CHECK REQUIRED: Verify NO WhatsApp message was received for test {request_id}")

def test_processor_failure_invalid_twilio_number(setup_e2e_company_data):
    """
    E2E Test: Verify processor handles invalid recipient phone number correctly.
    - Ensures company data exists with *valid* credentials.
    - Sends a request with an invalid recipient phone number format.
    - Asserts API response is 200 OK.
    - Polls conversations table until status is 'failed_to_send_message'.
    - Requires manual check: No WhatsApp message should be received.
    """
    # Use the fixture to ensure valid company data exists
    request_id = str(uuid.uuid4()) # Valid UUID
    invalid_recipient_tel = "+123" # Invalid E.164 format for Twilio
    logger.info(f"--- Starting Test: test_processor_failure_invalid_twilio_number (Request ID: {request_id}) ---")

    # Prepare Request Payload with invalid recipient_tel
    payload = {
      "company_data": {
        "company_id": TEST_COMPANY_ID,
        "project_id": TEST_PROJECT_ID
      },
      "recipient_data": {
        "recipient_first_name": "Test",
        "recipient_last_name": "InvalidNum",
        "recipient_tel": invalid_recipient_tel, # The invalid number
        "recipient_email": "test.invalidnum@example.com",
        "comms_consent": True
      },
      "project_data": {
         "jobID": "e2e-test-job-002",
         "jobRole": "Invalid Number Tester"
      },
      "request_data": {
        "request_id": request_id,
        "channel_method": "whatsapp",
        "initial_request_timestamp": datetime.now(timezone.utc).isoformat()
      }
    }
    logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")

    # Record start time just before sending the request
    test_start_time_iso = datetime.now(timezone.utc).isoformat()
    time.sleep(0.1) # Ensure slight delay so query finds items created after this

    # Send Request to API Gateway
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }
    api_response = None
    try:
        logger.info(f"Sending POST request to {API_URL}")
        api_response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        logger.info(f"API Response Status Code: {api_response.status_code}")
        # DO NOT raise_for_status here immediately, need to check code first
        # The initial API call should succeed (200 OK)
        assert api_response.status_code == 200, f"API Gateway returned {api_response.status_code}, expected 200."
        try:
            response_data = api_response.json()
            assert response_data.get("request_id") == request_id, "Response body did not contain matching request_id"
        except json.JSONDecodeError:
            pytest.fail("API response was not valid JSON.")

    except requests.exceptions.Timeout:
         pytest.fail(f"API request timed out after 20 seconds.")
    except requests.exceptions.RequestException as e:
        response_text = e.response.text if e.response is not None else "No response body"
        logger.error(f"API Request failed unexpectedly: {e}. Response: {response_text}")
        pytest.fail(f"API request failed unexpectedly: {e}")

    # Poll DynamoDB for the expected final status ('failed_to_send_message')
    logger.info("Polling DynamoDB conversations table for final status...")
    final_item = poll_conversation_status(
        primary_channel_key=invalid_recipient_tel, # Use the invalid number as the key
        request_id=request_id,
        expected_status="failed_to_send_message", # Status expected from Twilio failure
        test_start_time_iso=test_start_time_iso,
        timeout=120, # Allow generous time for processing and potential retries
        interval=15
    )

    # Assert the polling was successful and the status is correct
    assert final_item is not None, \
        f"Polling timed out or failed to find record for request_id '{request_id}' with primary_channel '{invalid_recipient_tel}'"

    final_status = final_item.get("conversation_status")
    assert final_status == "failed_to_send_message", \
        f"Final conversation_status was '{final_status}', expected 'failed_to_send_message'. Item: {final_item}"

    # --- Optional: Add DLQ check here if desired ---
    # logger.info("Skipping DLQ check for now.")

    logger.info(f"--- Test Passed: test_processor_failure_invalid_twilio_number (Request ID: {request_id}) ---")
    print(f"\nMANUAL CHECK REQUIRED: Verify NO WhatsApp message was received for test {request_id}")

def test_idempotency_e2e(setup_e2e_company_data):
    """
    E2E Test: Verify sending the same request twice results in only one processed conversation.
    - Ensures company data exists with valid credentials.
    - Generates a single request_id.
    - Sends the *same* valid request payload twice via API Gateway.
    - Asserts both API responses are 200 OK.
    - Polls conversations table until status is 'initial_message_sent'.
    - Queries the table again to ensure only ONE record exists for the request_id.
    - Requires manual check: Only ONE WhatsApp message should be received.
    """
    # Use the fixture to ensure valid company data exists
    request_id = str(uuid.uuid4()) # Single UUID for both requests
    # Use a valid phone number for this test
    # IMPORTANT: Use a number you can actually check for the manual verification!
    recipient_tel = "+447835065013" # Replace with a real test number if necessary
    logger.info(f"--- Starting Test: test_idempotency_e2e (Request ID: {request_id}) ---")

    # Prepare a valid Request Payload
    payload = {
      "company_data": {
        "company_id": TEST_COMPANY_ID,
        "project_id": TEST_PROJECT_ID
      },
      "recipient_data": {
        "recipient_first_name": "Test",
        "recipient_last_name": "Idempotent",
        "recipient_tel": recipient_tel, # Valid number
        "recipient_email": "test.idempotent@example.com",
        "comms_consent": True
      },
      "project_data": {
         "jobID": "e2e-test-job-003",
         "jobRole": "Idempotency Tester"
      },
      "request_data": {
        "request_id": request_id, # Use the single ID
        "channel_method": "whatsapp",
        "initial_request_timestamp": datetime.now(timezone.utc).isoformat()
      }
    }
    logger.debug(f"Request payload (used twice): {json.dumps(payload, indent=2)}")

    # Record start time just before sending the first request
    test_start_time_iso = datetime.now(timezone.utc).isoformat()
    time.sleep(0.1) # Ensure slight delay

    # Send Request to API Gateway - First time
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }
    api_response1 = None
    api_response2 = None
    try:
        logger.info(f"Sending FIRST POST request to {API_URL} for request_id {request_id}")
        api_response1 = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        logger.info(f"API Response 1 Status Code: {api_response1.status_code}")
        assert api_response1.status_code == 200, f"First API call returned {api_response1.status_code}, expected 200."
        response_data1 = api_response1.json()
        assert response_data1.get("request_id") == request_id, "Response 1 body did not contain matching request_id"

        # Send Request to API Gateway - Second time (identical payload)
        # Add a small delay, although idempotency should handle near-simultaneous requests too
        time.sleep(0.5)
        logger.info(f"Sending SECOND POST request to {API_URL} for request_id {request_id}")
        api_response2 = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        logger.info(f"API Response 2 Status Code: {api_response2.status_code}")
        assert api_response2.status_code == 200, f"Second API call returned {api_response2.status_code}, expected 200."
        response_data2 = api_response2.json()
        assert response_data2.get("request_id") == request_id, "Response 2 body did not contain matching request_id"

    except requests.exceptions.Timeout:
         pytest.fail(f"API request timed out during one of the calls.")
    except requests.exceptions.RequestException as e:
        response_text = e.response.text if e.response is not None else "No response body"
        logger.error(f"API Request failed unexpectedly: {e}. Response: {response_text}")
        pytest.fail(f"API request failed unexpectedly: {e}")
    except json.JSONDecodeError:
         pytest.fail("API response was not valid JSON during one of the calls.")

    # Poll DynamoDB for the expected final status ('initial_message_sent')
    # The processor should handle the duplicate SQS message gracefully (due to DynamoDB conditional writes)
    logger.info("Polling DynamoDB conversations table for final status...")
    final_item = poll_conversation_status(
        primary_channel_key=recipient_tel,
        request_id=request_id,
        expected_status="initial_message_sent", # Expect success despite duplicate send
        test_start_time_iso=test_start_time_iso,
        timeout=120, # Allow generous time
        interval=15
    )

    # Assert the polling found the record and it has the correct *final* status
    assert final_item is not None, \
        f"Polling timed out or failed to find record for request_id '{request_id}' with primary_channel '{recipient_tel}'"
    final_status = final_item.get("conversation_status")
    assert final_status == "initial_message_sent", \
        f"Final conversation_status was '{final_status}', expected 'initial_message_sent'. Item: {final_item}"

    # Verify only ONE record exists for this request_id
    logger.info(f"Querying table again to verify only one record exists for request_id '{request_id}'")
    # Use a slightly longer time window for safety, though the LSI query is efficient
    query_timeout_seconds = 10
    query_start_time = time.time()
    items_with_request_id = []
    table = get_dynamodb_table(CONVERSATIONS_TABLE)
    while time.time() - query_start_time < query_timeout_seconds:
        try:
            response = table.query(
                IndexName=CONVERSATIONS_CREATED_AT_LSI,
                KeyConditionExpression=
                    boto3.dynamodb.conditions.Key('primary_channel').eq(recipient_tel) & 
                    boto3.dynamodb.conditions.Key('created_at').gt(test_start_time_iso),
                ScanIndexForward=False,
                Limit=50 # Increase limit slightly for this check if needed
            )
            items = response.get('Items', [])
            items_with_request_id = [item for item in items if item.get('request_id') == request_id]
            # In theory, we should find it on the first query page given the polling already succeeded
            # but loop briefly just in case of eventual consistency delays affecting the index read
            if items_with_request_id:
                break
            if not response.get('LastEvaluatedKey'): # Stop if no more pages
                 break 
            # (Pagination logic could be added here if strictly necessary, but unlikely for this test)
            time.sleep(1)
        except ClientError as e:
             logger.error(f"Error querying DynamoDB LSI during final count check: {e}. Retrying...")
             time.sleep(1)
        except Exception as e:
             logger.error(f"Unexpected error during final count check: {e}. Retrying...")
             time.sleep(1)

    assert len(items_with_request_id) == 1, \
        f"Expected exactly 1 record for request_id '{request_id}', but found {len(items_with_request_id)}. Found items: {items_with_request_id}"
    logger.info("Verified exactly one conversation record exists for the request_id.")

    logger.info(f"--- Test Passed: test_idempotency_e2e (Request ID: {request_id}) ---")
    print(f"\nMANUAL CHECK REQUIRED: Verify ONLY ONE WhatsApp message was received for test {request_id} on {recipient_tel}") 