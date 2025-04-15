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
# Define the LSI name as a constant
CONVERSATIONS_CREATED_AT_LSI = "created-at-index" # LSI defined in template.yaml
# DLQ Name (from template.yaml: ${ProjectPrefix}-whatsapp-dlq-${EnvironmentName})
DLQ_NAME = "ai-multi-comms-whatsapp-dlq-dev"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Configure basic logging for visibility

# --- Helper Functions ---

# Consider moving helpers to tests/e2e/conftest.py if reused across test files
_dynamodb_resource = None
_sqs_client = None
_account_id = None
_aws_region = "eu-north-1" # Assuming same region as API

def get_aws_account_id():
    """Gets AWS Account ID using STS."""
    global _account_id
    if _account_id is None:
        try:
            sts_client = boto3.client("sts")
            _account_id = sts_client.get_caller_identity()["Account"]
            logger.info(f"Fetched AWS Account ID: {_account_id}")
        except Exception as e:
            logger.warning(f"Could not fetch AWS Account ID: {e}. Using placeholder.")
            _account_id = "YOUR_ACCOUNT_ID_HERE" # Placeholder
    return _account_id

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

def get_sqs_client():
    """Gets a cached SQS client."""
    global _sqs_client
    if _sqs_client is None:
        _sqs_client = boto3.client('sqs', region_name=_aws_region)
    return _sqs_client

# Construct DLQ URL
ACCOUNT_ID = get_aws_account_id()
DLQ_URL = f"https://sqs.{_aws_region}.amazonaws.com/{ACCOUNT_ID}/{DLQ_NAME}" if ACCOUNT_ID != "YOUR_ACCOUNT_ID_HERE" else None
if not DLQ_URL:
    logger.warning(f"Could not construct DLQ URL automatically. Set manually or ensure AWS credentials are configured.")
    DLQ_URL = "YOUR_DLQ_URL_HERE" # Placeholder

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

def poll_dlq_and_verify_message(dlq_url, expected_request_id, timeout=60, interval=10):
    """
    Polls the specified SQS DLQ, looking for a message containing the expected request_id.
    Deletes the message if found.

    Args:
        dlq_url (str): The URL of the Dead Letter Queue.
        expected_request_id (str): The request_id expected within the message body.
        timeout (int): Maximum time to poll in seconds.
        interval (int): Time to wait between polls in seconds.

    Returns:
        bool: True if a matching message was found and deleted, False otherwise.
    """
    if not dlq_url or dlq_url == "YOUR_DLQ_URL_HERE":
        logger.warning("DLQ URL is not configured. Skipping DLQ check.")
        pytest.skip("DLQ URL not configured, skipping DLQ check.")
        return False # Should be skipped by pytest.skip, but return for safety

    logger.info(f"Polling DLQ '{dlq_url}' for message containing request_id: '{expected_request_id}'")
    sqs = get_sqs_client()
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = sqs.receive_message(
                QueueUrl=dlq_url,
                MaxNumberOfMessages=10, # Receive up to 10 messages at once
                WaitTimeSeconds=5 # Use long polling
            )

            messages = response.get('Messages', [])
            if not messages:
                logger.debug(f"No messages received from DLQ. Waiting {interval}s...")
                time.sleep(interval)
                continue

            logger.info(f"Received {len(messages)} message(s) from DLQ.")
            for message in messages:
                receipt_handle = message.get('ReceiptHandle')
                body = message.get('Body', '')
                logger.debug(f"DLQ Message Body: {body[:500]}...") # Log truncated body

                # Check if the expected request_id is in the body
                # Assuming the SQS message body pushed by Lambda (on failure/retry)
                # is the original Context Object JSON string.
                if expected_request_id in body:
                    logger.info(f"Found message in DLQ containing request_id '{expected_request_id}'. Deleting message...")
                    try:
                        sqs.delete_message(
                            QueueUrl=dlq_url,
                            ReceiptHandle=receipt_handle
                        )
                        logger.info(f"Successfully deleted message {message.get('MessageId')} from DLQ.")
                        return True # Found and deleted
                    except ClientError as del_e:
                        logger.error(f"Failed to delete message {message.get('MessageId')} from DLQ: {del_e}")
                        # Don't return False yet, maybe another message matches
                        continue # Continue checking other messages
                else:
                    # Message didn't match, ideally leave it for manual inspection or
                    # make the check more robust if needed.
                    # For now, we just ignore non-matching messages in this poll cycle.
                    logger.debug(f"DLQ message {message.get('MessageId')} did not contain expected request_id.")

            # If no matching message found in this batch, wait and retry
            time.sleep(interval)

        except ClientError as e:
            logger.error(f"Error receiving messages from DLQ '{dlq_url}': {e}. Retrying...")
            time.sleep(interval)
        except Exception as e:
            logger.error(f"Unexpected error during DLQ polling: {e}. Retrying...")
            time.sleep(interval)

    logger.error(f"Timeout ({timeout}s) reached waiting for message with request_id '{expected_request_id}' in DLQ '{dlq_url}'")
    return False

# --- Test Cases ---

def test_processor_failure_missing_secret(setup_e2e_company_data, modify_company_data_invalid_openai_secret):
    """
    E2E Test: Verify processor handles missing OpenAI secret correctly.
    - Ensures company data exists via setup_e2e_company_data fixture.
    - Modifies company data to point OpenAI key ref to an invalid secret.
    - Sends a valid request via API Gateway.
    - Asserts API response is 200 OK.
    - Polls conversations table until status is 'failed_unknown'.
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

    # Poll DynamoDB for the expected final status ('failed_unknown')
    logger.info("Polling DynamoDB conversations table for final status...")
    final_item = poll_conversation_status(
        primary_channel_key=recipient_tel, # Pass the phone number
        request_id=request_id,
        expected_status="failed_unknown",
        test_start_time_iso=test_start_time_iso, # Pass the start time
        timeout=120,
        interval=15
    )

    # Assert the polling was successful and the status is correct
    assert final_item is not None, \
        f"Polling timed out or failed to find record for request_id '{request_id}'"

    final_status = final_item.get("conversation_status")
    assert final_status == "failed_unknown", \
        f"Final conversation_status was '{final_status}', expected 'failed_unknown'. Item: {final_item}"

    # --- DLQ Check (Commented out due to long SQS retry delays) ---
    # logger.info(f"Verifying message for request_id '{request_id}' reached DLQ '{DLQ_URL}'")
    # dlq_found = poll_dlq_and_verify_message(
    #     dlq_url=DLQ_URL,
    #     expected_request_id=request_id,
    #     timeout=90, # Needs to be > maxReceiveCount * VisibilityTimeout (e.g., 3 * 905s = ~45 min)
    #     interval=15
    # )
    # assert dlq_found, f"Message for request_id '{request_id}' not found in DLQ after timeout."
    # logger.info("Successfully verified message in DLQ.")
    logger.info("Skipping DLQ check due to potentially long SQS retry delays.")

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

    # --- DLQ Check (Commented out due to long SQS retry delays) ---
    # logger.info(f"Verifying message for request_id '{request_id}' reached DLQ '{DLQ_URL}'")
    # dlq_found = poll_dlq_and_verify_message(
    #     dlq_url=DLQ_URL,
    #     expected_request_id=request_id,
    #     timeout=90, # Needs to be > maxReceiveCount * VisibilityTimeout
    #     interval=15
    # )
    # assert dlq_found, f"Message for request_id '{request_id}' not found in DLQ after timeout."
    # logger.info("Successfully verified message in DLQ.")
    logger.info("Skipping DLQ check due to potentially long SQS retry delays.")

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

# --- API/Router Validation Tests ---

def test_api_invalid_key():
    """
    E2E Test: Verify API Gateway rejects requests with an invalid API key.
    - Sends a request with an incorrect 'x-api-key' header.
    - Asserts the API response status code is 403 Forbidden.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"--- Starting Test: test_api_invalid_key (Request ID: {request_id}) ---")

    # Prepare minimal payload (content doesn't matter much)
    payload = {
      "company_data": {"company_id": TEST_COMPANY_ID, "project_id": TEST_PROJECT_ID},
      "recipient_data": {"recipient_tel": "+447000000000", "comms_consent": True},
      "project_data": {"jobID": "api-test-job-001"},
      "request_data": {
        "request_id": request_id,
        "channel_method": "whatsapp",
        "initial_request_timestamp": datetime.now(timezone.utc).isoformat()
      }
    }

    # Use an INVALID API Key
    invalid_api_key = "invalid-api-key-for-testing-12345"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": invalid_api_key
    }

    api_response = None
    try:
        logger.info(f"Sending POST request to {API_URL} with INVALID API Key")
        api_response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        logger.info(f"API Response Status Code: {api_response.status_code}")
        # We EXPECT this to fail, so raise_for_status() should trigger the HTTPError
        api_response.raise_for_status()

        # If raise_for_status() doesn't raise an error (e.g., 2xx), the test failed
        pytest.fail(f"API request unexpectedly succeeded with status {api_response.status_code} when 403 was expected.")

    except requests.exceptions.HTTPError as e:
        # This is the expected path
        logger.info(f"Received expected HTTPError: {e}")
        assert e.response.status_code == 403, \
            f"Expected status code 403 Forbidden, but got {e.response.status_code}. Response: {e.response.text}"
        # Optional: Check response body for specific message if API Gateway provides one
        # response_body = e.response.json()
        # assert response_body.get("message") == "Forbidden", "Expected Forbidden message in response body"
        logger.info("Successfully verified API returned 403 Forbidden.")

    except requests.exceptions.RequestException as e:
        # Catch other potential request errors (timeout, connection error)
        logger.error(f"API Request failed unexpectedly (non-HTTPError): {e}")
        pytest.fail(f"API request failed unexpectedly (non-HTTPError): {e}")

    logger.info(f"--- Test Passed: test_api_invalid_key ---")

def test_api_missing_body_field():
    """
    E2E Test: Verify API/Router rejects requests with missing required fields.
    - Sends a request with a valid API key but missing e.g. 'recipient_data'.
    - Asserts the API response status code is 400 Bad Request.
    """
    request_id = str(uuid.uuid4())
    logger.info(f"--- Starting Test: test_api_missing_body_field (Request ID: {request_id}) ---")

    # Prepare payload missing 'recipient_data'
    payload = {
      "company_data": {"company_id": TEST_COMPANY_ID, "project_id": TEST_PROJECT_ID},
      # "recipient_data": { ... } // MISSING!
      "project_data": {"jobID": "api-test-job-002"},
      "request_data": {
        "request_id": request_id,
        "channel_method": "whatsapp",
        "initial_request_timestamp": datetime.now(timezone.utc).isoformat()
      }
    }

    # Use the VALID API Key
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY # Valid key
    }

    api_response = None
    try:
        logger.info(f"Sending POST request to {API_URL} with missing 'recipient_data'")
        api_response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        logger.info(f"API Response Status Code: {api_response.status_code}")
        # We EXPECT this to fail with 400
        api_response.raise_for_status()

        # If raise_for_status() doesn't raise an error (e.g., 2xx), the test failed
        pytest.fail(f"API request unexpectedly succeeded with status {api_response.status_code} when 400 was expected.")

    except requests.exceptions.HTTPError as e:
        # This is the expected path
        logger.info(f"Received expected HTTPError: {e}")
        assert e.response.status_code == 400, \
            f"Expected status code 400 Bad Request, but got {e.response.status_code}. Response: {e.response.text}"
        
        # Optional: Check response body for specific error code from router
        try:
            response_body = e.response.json()
            # Based on router code, validation errors might return specific codes
            # Check for common required fields; adjust if router validation logic is different
            expected_error_code = "MISSING_RECIPIENT_DATA" # Specific code for missing recipient data
            actual_error_code = response_body.get("error_code")
            assert actual_error_code == expected_error_code, \
                   f"Expected error_code '{expected_error_code}', but got '{actual_error_code}'"
            # Check if the message still mentions the missing field
            assert "recipient_data" in response_body.get("message", "").lower(), \
                   f"Expected error message to mention 'recipient_data', but got: {response_body.get('message')}"
            logger.info(f"Successfully verified API returned 400 Bad Request with code '{actual_error_code}'.")
        except json.JSONDecodeError:
            logger.warning("Could not parse response body as JSON to check error code/message.")
        except KeyError:
             logger.warning("Response body did not contain expected 'error_code' or 'message' keys.")

    except requests.exceptions.RequestException as e:
        # Catch other potential request errors (timeout, connection error)
        logger.error(f"API Request failed unexpectedly (non-HTTPError): {e}")
        pytest.fail(f"API request failed unexpectedly (non-HTTPError): {e}")

    logger.info(f"--- Test Passed: test_api_missing_body_field ---")

def test_api_non_existent_company_project_id():
    """
    E2E Test: Verify API/Router rejects requests for non-existent company/project IDs.
    - Sends a request with a valid API key and valid structure.
    - Uses company_id/project_id values that do not exist in the company-data table.
    - Asserts the API response status code is 404 Not Found.
    """
    request_id = str(uuid.uuid4())
    non_existent_company_id = "non-existent-company-id-123"
    non_existent_project_id = "non-existent-project-id-456"
    logger.info(f"--- Starting Test: test_api_non_existent_company_project_id (Request ID: {request_id}) ---")

    # Prepare payload with non-existent company/project IDs
    payload = {
      "company_data": {
          "company_id": non_existent_company_id,
          "project_id": non_existent_project_id
      },
      "recipient_data": {
          "recipient_first_name": "Test",
          "recipient_last_name": "NotFound",
          "recipient_tel": "+447111999888",
          "comms_consent": True
       },
      "project_data": {"jobID": "api-test-job-003"},
      "request_data": {
        "request_id": request_id,
        "channel_method": "whatsapp",
        "initial_request_timestamp": datetime.now(timezone.utc).isoformat()
      }
    }

    # Use the VALID API Key
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY # Valid key
    }

    api_response = None
    try:
        logger.info(f"Sending POST request to {API_URL} with non-existent company/project ID")
        api_response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        logger.info(f"API Response Status Code: {api_response.status_code}")
        # We EXPECT this to fail with 404
        api_response.raise_for_status()

        pytest.fail(f"API request unexpectedly succeeded with status {api_response.status_code} when 404 was expected.")

    except requests.exceptions.HTTPError as e:
        logger.info(f"Received expected HTTPError: {e}")
        assert e.response.status_code == 404, \
            f"Expected status code 404 Not Found, but got {e.response.status_code}. Response: {e.response.text}"
        
        # Optional: Check response body for specific error code from router
        try:
            response_body = e.response.json()
            expected_error_code = "COMPANY_NOT_FOUND" # Based on router logic review
            actual_error_code = response_body.get("error_code")
            assert actual_error_code == expected_error_code, \
                   f"Expected error_code '{expected_error_code}', but got '{actual_error_code}'"
            logger.info(f"Successfully verified API returned 404 Not Found with code '{actual_error_code}'.")
        except json.JSONDecodeError:
            logger.warning("Could not parse response body as JSON to check error code/message.")
        except KeyError:
             logger.warning("Response body did not contain expected 'error_code' key.")

    except requests.exceptions.RequestException as e:
        logger.error(f"API Request failed unexpectedly (non-HTTPError): {e}")
        pytest.fail(f"API request failed unexpectedly (non-HTTPError): {e}")

    logger.info(f"--- Test Passed: test_api_non_existent_company_project_id ---")

def test_api_inactive_project_id(modify_company_data_inactive_project):
    """
    E2E Test: Verify API/Router rejects requests for inactive project IDs.
    - Uses a fixture to set the test project's status to 'inactive'.
    - Sends a valid request payload targeting that project.
    - Asserts the API response status code is 403 Forbidden.
    """
    # Use the fixture by including its name as an argument
    # modify_company_data_inactive_project implicitly depends on setup_e2e_company_data
    request_id = str(uuid.uuid4())
    logger.info(f"--- Starting Test: test_api_inactive_project_id (Request ID: {request_id}) ---")

    # Prepare payload targeting the now-inactive project
    payload = {
      "company_data": {
          "company_id": TEST_COMPANY_ID, # Standard test company
          "project_id": TEST_PROJECT_ID  # Standard test project (now inactive)
      },
      "recipient_data": {
          "recipient_first_name": "Test",
          "recipient_last_name": "Inactive",
          "recipient_tel": "+447111777666",
          "comms_consent": True
       },
      "project_data": {"jobID": "api-test-job-004"},
      "request_data": {
        "request_id": request_id,
        "channel_method": "whatsapp",
        "initial_request_timestamp": datetime.now(timezone.utc).isoformat()
      }
    }

    # Use the VALID API Key
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY # Valid key
    }

    api_response = None
    try:
        logger.info(f"Sending POST request to {API_URL} for inactive project {TEST_PROJECT_ID}")
        api_response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        logger.info(f"API Response Status Code: {api_response.status_code}")
        # We EXPECT this to fail with 403
        api_response.raise_for_status()

        pytest.fail(f"API request unexpectedly succeeded with status {api_response.status_code} when 403 was expected.")

    except requests.exceptions.HTTPError as e:
        logger.info(f"Received expected HTTPError: {e}")
        assert e.response.status_code == 403, \
            f"Expected status code 403 Forbidden, but got {e.response.status_code}. Response: {e.response.text}"
        
        # Optional: Check response body for specific error code from router
        try:
            response_body = e.response.json()
            expected_error_code = "PROJECT_INACTIVE" # Based on router logic review
            actual_error_code = response_body.get("error_code")
            assert actual_error_code == expected_error_code, \
                   f"Expected error_code '{expected_error_code}', but got '{actual_error_code}'"
            logger.info(f"Successfully verified API returned 403 Forbidden with code '{actual_error_code}'.")
        except json.JSONDecodeError:
            logger.warning("Could not parse response body as JSON to check error code/message.")
        except KeyError:
             logger.warning("Response body did not contain expected 'error_code' key.")

    except requests.exceptions.RequestException as e:
        logger.error(f"API Request failed unexpectedly (non-HTTPError): {e}")
        pytest.fail(f"API request failed unexpectedly (non-HTTPError): {e}")

    logger.info(f"--- Test Passed: test_api_inactive_project_id ---")

def test_api_disallowed_channel(modify_company_data_disallowed_channel):
    """
    E2E Test: Verify API/Router rejects requests for disallowed channels.
    - Uses a fixture to modify the project's allowed_channels to exclude 'whatsapp'.
    - Sends a valid request payload specifying 'whatsapp' as the channel_method.
    - Asserts the API response status code is 403 Forbidden.
    """
    # Use the fixture to modify allowed_channels
    request_id = str(uuid.uuid4())
    logger.info(f"--- Starting Test: test_api_disallowed_channel (Request ID: {request_id}) ---")

    # Prepare payload targeting the project, requesting the now-disallowed 'whatsapp' channel
    payload = {
      "company_data": {
          "company_id": TEST_COMPANY_ID, 
          "project_id": TEST_PROJECT_ID
      },
      "recipient_data": {
          "recipient_first_name": "Test",
          "recipient_last_name": "Disallowed",
          "recipient_tel": "+447111555444",
          "comms_consent": True
       },
      "project_data": {"jobID": "api-test-job-005"},
      "request_data": {
        "request_id": request_id,
        "channel_method": "whatsapp", # Request the disallowed channel
        "initial_request_timestamp": datetime.now(timezone.utc).isoformat()
      }
    }

    # Use the VALID API Key
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY # Valid key
    }

    api_response = None
    try:
        logger.info(f"Sending POST request to {API_URL} requesting disallowed channel 'whatsapp'")
        api_response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        logger.info(f"API Response Status Code: {api_response.status_code}")
        # We EXPECT this to fail with 403
        api_response.raise_for_status()

        pytest.fail(f"API request unexpectedly succeeded with status {api_response.status_code} when 403 was expected.")

    except requests.exceptions.HTTPError as e:
        logger.info(f"Received expected HTTPError: {e}")
        assert e.response.status_code == 403, \
            f"Expected status code 403 Forbidden, but got {e.response.status_code}. Response: {e.response.text}"
        
        # Optional: Check response body for specific error code from router
        try:
            response_body = e.response.json()
            expected_error_code = "CHANNEL_NOT_ALLOWED" # Based on router logic review
            actual_error_code = response_body.get("error_code")
            assert actual_error_code == expected_error_code, \
                   f"Expected error_code '{expected_error_code}', but got '{actual_error_code}'"
            logger.info(f"Successfully verified API returned 403 Forbidden with code '{actual_error_code}'.")
        except json.JSONDecodeError:
            logger.warning("Could not parse response body as JSON to check error code/message.")
        except KeyError:
             logger.warning("Response body did not contain expected 'error_code' key.")

    except requests.exceptions.RequestException as e:
        logger.error(f"API Request failed unexpectedly (non-HTTPError): {e}")
        pytest.fail(f"API request failed unexpectedly (non-HTTPError): {e}")

    logger.info(f"--- Test Passed: test_api_disallowed_channel ---") 