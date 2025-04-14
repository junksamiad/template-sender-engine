import pytest
import requests
import boto3
import json
import uuid
import time
from datetime import datetime, timezone
import os # For loading sample data

# --- Configuration ---
# Using known dev resource names and URLs
API_ENDPOINT_URL = "https://xlijn1k4xh.execute-api.eu-north-1.amazonaws.com/dev/" # Ensure trailing slash
API_KEY = "YbgTABlGlg6s2YZ9gcyuB4AUhi5jJcC05yeKcCWR"
DYNAMODB_COMPANY_TABLE_NAME = "ai-multi-comms-company-data-dev"
DYNAMODB_CONVERSATIONS_TABLE_NAME = "ai-multi-comms-conversations-dev"
REGION = "eu-north-1"
# Sample data file paths (relative to project root)
COMPANY_DATA_SAMPLE_PATH = "samples/recruitment_company_data_record_example_dev.json"
E2E_PAYLOAD_SAMPLE_PATH = "samples/e2e_test_curl_dev.sh" # We'll parse the JSON from this

# --- Fixtures ---

# @pytest.fixture(scope="module")
# def dynamodb_client():
#     """Boto3 DynamoDB client configured for the correct region."""
#     print(f"\nCreating DynamoDB client fixture for region: {REGION}")
#     return boto3.client("dynamodb", region_name=REGION)
#
# @pytest.fixture(scope="function")
# def setup_e2e_company_data(dynamodb_client):
#     """Ensures the specific company data record exists for the E2E test and cleans up."""
#     print(f"\n--- Fixture Setup: Loading Company Data from {COMPANY_DATA_SAMPLE_PATH} ---")
#     try:
#         with open(COMPANY_DATA_SAMPLE_PATH, 'r') as f:
#             company_data_item = json.load(f)
#     except Exception as e:
#         pytest.fail(f"Failed to load company data sample: {e}")
#     
#     company_id = company_data_item.get("company_id")
#     project_id = company_data_item.get("project_id")
#     if not company_id or not project_id:
#         pytest.fail("Company/Project ID missing in sample data file.")
#
#     print(f"Ensuring company data exists: {company_id}/{project_id} in {DYNAMODB_COMPANY_TABLE_NAME}")
#     # Use put_item for simplicity (create or overwrite)
#     # Note: DynamoDB expects specific type descriptors (S, N, M, L, BOOL)
#     # Need a helper to format the JSON correctly for put_item
#     try:
#         formatted_item = format_json_for_dynamodb(company_data_item)
#         dynamodb_client.put_item(
#             TableName=DYNAMODB_COMPANY_TABLE_NAME,
#             Item=formatted_item
#         )
#         print("Company data put/overwrite successful.")
#     except Exception as e:
#         pytest.fail(f"Failed to put company data item into DynamoDB: {e}")
#
#     yield company_id, project_id # Provide IDs to the test if needed
#
#     # --- Teardown --- 
#     print(f"\n--- Fixture Teardown: Deleting Company Data {company_id}/{project_id} ---")
#     try:
#         dynamodb_client.delete_item(
#             TableName=DYNAMODB_COMPANY_TABLE_NAME,
#             Key={"company_id": {"S": company_id}, "project_id": {"S": project_id}}
#         )
#         print("Company data deleted successfully.")
#     except Exception as e:
#         print(f"Warning: Error during company data cleanup: {e}")
#
# Helper function to format JSON for DynamoDB put_item
# This is a simplified version; a more robust one would handle all types
# def format_json_for_dynamodb(data):
#    # ... function body removed ...

# Helper function to parse JSON payload from the curl script
def parse_payload_from_curl_script(script_path):
    print(f"\nParsing payload from {script_path}...")
    try:
        with open(script_path, 'r') as f:
            content = f.read()
        # Find the start and end of the JSON block within the heredoc
        start_marker = "<<'EOF'\n"
        end_marker = "\nEOF"
        start_index = content.find(start_marker) + len(start_marker)
        end_index = content.find(end_marker)
        if start_index == -1 or end_index == -1 or start_index >= end_index:
            raise ValueError("Could not find heredoc markers EOF in script")
        json_string = content[start_index:end_index]
        payload = json.loads(json_string)
        print("Payload parsed successfully.")
        return payload
    except Exception as e:
        pytest.fail(f"Failed to parse JSON payload from {script_path}: {e}")

# --- Test Case ---

def test_whatsapp_happy_path(dynamodb_client, setup_e2e_company_data):
    """
    Tests the full end-to-end happy path for initiating a WhatsApp conversation.
    Sends request, waits, verifies final DynamoDB state.
    Manual verification of received WhatsApp message is required separately.
    """
    # Record test start time for querying later
    test_start_timestamp = datetime.now(timezone.utc).isoformat()
    time.sleep(0.1) # Ensure a slight delay before request timestamp

    # 1. Get Payload
    request_payload = parse_payload_from_curl_script(E2E_PAYLOAD_SAMPLE_PATH)
    # Update request_id and timestamp for uniqueness
    request_id = str(uuid.uuid4())
    request_payload["request_data"]["request_id"] = request_id
    request_payload["request_data"]["initial_request_timestamp"] = datetime.now(timezone.utc).isoformat()
    
    recipient_tel = request_payload["recipient_data"]["recipient_tel"]
    
    # 2. Send API Request
    headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
    initiate_url = f"{API_ENDPOINT_URL.rstrip('/')}/initiate-conversation"
    
    print(f"\n--- Test: E2E Happy Path --- ")
    print(f"Sending E2E request to {initiate_url} with request_id: {request_id}")
    response = requests.post(initiate_url, headers=headers, json=request_payload)
    print(f"API Response Status: {response.status_code}")
    print(f"API Response Body: {response.text}")
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data.get("status") == "success"
    assert response_data.get("request_id") == request_id
    print("API request successful.")
    
    # 3. Wait for processing
    wait_seconds = 15 # Significantly reduced wait time
    print(f"Waiting {wait_seconds} seconds for end-to-end processing...")
    time.sleep(wait_seconds)
    
    # 4. Verify Final State in Conversations DynamoDB (Single Attempt)
    conversation_record = None
    final_exception = None # Keep track of errors

    # Record time *before* querying starts (approximate)
    query_start_time_iso = datetime.fromtimestamp(time.time() - wait_seconds - 1, tz=timezone.utc).isoformat()

    print(f"\n--- Verification Attempt --- ")
    print(f"Checking {DYNAMODB_CONVERSATIONS_TABLE_NAME} for final record state for recipient {recipient_tel}...")
    try:
        # Query using the created-at-index
        print(f"Querying created-at-index for items after {query_start_time_iso}")
        query_response = dynamodb_client.query(
            TableName=DYNAMODB_CONVERSATIONS_TABLE_NAME,
            IndexName='created-at-index', # Use the LSI
            KeyConditionExpression="primary_channel = :pk AND created_at > :start_ts", # Query PK and SK range
            ExpressionAttributeValues={
                ":pk": {"S": recipient_tel},
                ":start_ts": {"S": query_start_time_iso}
            },
            ScanIndexForward=False, # Get newest items first
            Limit=5 
        )
        
        items = query_response.get('Items', [])
        print(f"Found {len(items)} conversation items using created-at-index.")
        temp_conversation_record = None
        for item in items:
            # Check if this item matches our request_id (best match)
            if item.get('request_id', {}).get('S') == request_id:
                temp_conversation_record = item
                print(f"Found matching record by request_id: {item.get('conversation_id', {}).get('S')}")
                break

        if temp_conversation_record is None:
                print(f"Conversation record for request_id {request_id} not found.")
                # Fail immediately if not found after the wait
                pytest.fail(f"Could not find conversation record for request_id {request_id} after {wait_seconds}s wait.") 
        else:
            conversation_record = temp_conversation_record # Store the found record
            # Verify final status
            final_status = conversation_record.get("conversation_status", {}).get("S")
            print(f"Final conversation status: {final_status}")
            assert final_status == "initial_message_sent", f"Expected final status 'initial_message_sent', but got '{final_status}'"

            # --- Add more detailed assertions --- #
            print("Performing detailed assertions on conversation record...")

            # Check for OpenAI thread ID
            thread_id = conversation_record.get("thread_id", {}).get("S")
            assert thread_id is not None and thread_id.startswith("thread_"), f"Missing or invalid thread_id: {thread_id}"
            print(f"Found thread_id: {thread_id}")

            # Check messages list
            messages_list = conversation_record.get("messages", {}).get("L", [])
            assert len(messages_list) > 0, "Messages list should not be empty after successful send"
            print(f"Found {len(messages_list)} message(s) in history.")
            # Optional: Check first message details
            first_message = messages_list[0].get("M", {})
            assert first_message.get("role", {}).get("S") == "assistant", "First message role should be assistant"
            message_id_val = first_message.get("message_id", {}).get("S", "")
            assert message_id_val is not None and message_id_val != "", "First message should have a non-empty message_id"
            print(f"Found first message_id: {message_id_val}")

            # Check task_complete flag (should be 0 initially)
            task_complete = conversation_record.get("task_complete", {}).get("N")
            assert task_complete == "0", f"Expected task_complete to be 0 (Number), but got: {task_complete}"
            print(f"Found task_complete: {task_complete}")

            # Check processing_time_ms
            processing_time = conversation_record.get("initial_processing_time_ms", {}).get("N") # Correct attribute name
            assert processing_time is not None and int(processing_time) > 0, f"Invalid or missing processing_time_ms: {processing_time}"
            print(f"Found processing_time_ms: {processing_time}")

            # Check some key copied fields
            assert conversation_record.get("company_id", {}).get("S") == request_payload["company_data"]["company_id"]
            assert conversation_record.get("project_id", {}).get("S") == request_payload["company_data"]["project_id"]

            # Verify channel_method and conditional recipient identifier
            channel_method_in_record = conversation_record.get("channel_method", {}).get("S")
            assert channel_method_in_record == "whatsapp", f"Expected channel_method 'whatsapp', got '{channel_method_in_record}'"
            if channel_method_in_record in ["whatsapp", "sms"]:
                assert conversation_record.get("recipient_tel", {}).get("S") == recipient_tel, "Recipient telephone number mismatch in record"
                print("Verified recipient_tel matches payload.")
            elif channel_method_in_record == "email":
                # Add check for email if implementing email tests later
                recipient_email = request_payload["recipient_data"]["recipient_email"]
                assert conversation_record.get("recipient_email", {}).get("S") == recipient_email, "Recipient email mismatch in record"
                print("Verified recipient_email matches payload.")

            assert conversation_record.get("request_id", {}).get("S") == request_id # Check request id propagation
            # --- End detailed assertions --- #
                
            print("DynamoDB final state verification successful.")
            # verification_success = True # No longer needed
            # break # No longer needed

    except AssertionError as ae: # Catch assertion errors specifically
        # print(f"Assertion failed on attempt {attempt+1}: {ae}")
        # final_exception = ae # Store the assertion error
        pytest.fail(f"Assertion failed during verification: {ae}") # Fail immediately on assertion error
    except Exception as e:
        # print(f"Error querying or verifying conversations table on attempt {attempt+1}: {e}")
        # final_exception = e # Store other errors
        pytest.fail(f"Error querying or verifying conversations table: {e}") # Fail immediately on other errors
        # We might want to break immediately on unexpected Boto3 errors

    # Cleanup logic needs to be reliably executed
    cleanup_dynamodb_record(dynamodb_client, conversation_record, recipient_tel)
            
    print("\n--- E2E Happy Path Test Complete --- ")
    print(f"--> MANUAL VERIFICATION NEEDED: Check WhatsApp on {recipient_tel} for received message.")

# Separate cleanup function for clarity and reliability
def cleanup_dynamodb_record(dynamodb_client, conversation_record, recipient_tel):
    """Helper function to delete the conversation record if found."""
    if conversation_record:
        convo_id_to_delete = conversation_record.get('conversation_id', {}).get('S')
        if convo_id_to_delete:
            print(f"\nAttempting E2E test cleanup: Deleting conversation {recipient_tel} / {convo_id_to_delete}")
            try:
                dynamodb_client.delete_item(
                    TableName=DYNAMODB_CONVERSATIONS_TABLE_NAME,
                    Key={"primary_channel": {"S": recipient_tel}, "conversation_id": {"S": convo_id_to_delete}}
                )
                print("Conversation record deleted.")
            except Exception as e:
                print(f"Warning: Error during conversation record cleanup: {e}")
    else:
        print("\nSkipping conversation cleanup as record was not found/passed to cleanup.")

# Add more E2E tests based on plan... 