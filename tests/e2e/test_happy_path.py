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

@pytest.fixture(scope="module")
def dynamodb_client():
    """Boto3 DynamoDB client configured for the correct region."""
    print(f"\nCreating DynamoDB client fixture for region: {REGION}")
    return boto3.client("dynamodb", region_name=REGION)

@pytest.fixture(scope="function")
def setup_e2e_company_data(dynamodb_client):
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
    # Note: DynamoDB expects specific type descriptors (S, N, M, L, BOOL)
    # Need a helper to format the JSON correctly for put_item
    try:
        formatted_item = format_json_for_dynamodb(company_data_item)
        dynamodb_client.put_item(
            TableName=DYNAMODB_COMPANY_TABLE_NAME,
            Item=formatted_item
        )
        print("Company data put/overwrite successful.")
    except Exception as e:
        pytest.fail(f"Failed to put company data item into DynamoDB: {e}")

    yield company_id, project_id # Provide IDs to the test if needed

    # --- Teardown --- 
    print(f"\n--- Fixture Teardown: Deleting Company Data {company_id}/{project_id} ---")
    try:
        dynamodb_client.delete_item(
            TableName=DYNAMODB_COMPANY_TABLE_NAME,
            Key={"company_id": {"S": company_id}, "project_id": {"S": project_id}}
        )
        print("Company data deleted successfully.")
    except Exception as e:
        print(f"Warning: Error during company data cleanup: {e}")

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
    
    # 3. Wait initially for processing (API -> Router -> SQS -> Processor -> OpenAI -> Twilio -> DDB Update)
    initial_wait_seconds = 30 # Reduced initial wait
    print(f"Waiting initial {initial_wait_seconds} seconds for end-to-end processing...")
    time.sleep(initial_wait_seconds)
    
    # 4. Verify Final State in Conversations DynamoDB with Retries
    max_retries = 3
    retry_delay_seconds = 10
    verification_success = False
    conversation_record = None
    final_exception = None

    for attempt in range(max_retries):
        print(f"\n--- Verification Attempt {attempt + 1}/{max_retries} --- ")
        print(f"Checking {DYNAMODB_CONVERSATIONS_TABLE_NAME} for final record state for recipient {recipient_tel}...")
        try:
            # Query using the primary channel (phone number)
            query_response = dynamodb_client.query(
                TableName=DYNAMODB_CONVERSATIONS_TABLE_NAME,
                KeyConditionExpression="primary_channel = :pk",
                ExpressionAttributeValues={":pk": {"S": recipient_tel}},
                ScanIndexForward=False, # Get newest items first
                Limit=5 # Check the last few conversations for this recipient
            )
            
            items = query_response.get('Items', [])
            print(f"Found {len(items)} conversation items for recipient {recipient_tel}")
            temp_conversation_record = None
            for item in items:
                # Check if this item matches our request_id (best match)
                if item.get('request_id', {}).get('S') == request_id:
                    temp_conversation_record = item
                    print(f"Found matching record by request_id: {item.get('conversation_id', {}).get('S')}")
                    break

            if temp_conversation_record is None:
                 print(f"Conversation record for request_id {request_id} not found yet.")
                 final_exception = AssertionError(f"Could not find conversation record for request_id {request_id}") # Store potential error
            else:
                conversation_record = temp_conversation_record # Store the found record
                # Verify final status
                final_status = conversation_record.get("conversation_status", {}).get("S")
                print(f"Final conversation status: {final_status}")
                assert final_status == "initial_message_sent"
                
                # Verify other expected fields exist
                assert "thread_id" in conversation_record
                assert "messages" in conversation_record
                assert len(conversation_record.get("messages", {}).get("L", [])) > 0 
                
                print("DynamoDB final state verification successful.")
                verification_success = True # Mark success
                break # Exit retry loop on success

        except AssertionError as ae: # Catch assertion errors specifically
            print(f"Assertion failed on attempt {attempt+1}: {ae}")
            final_exception = ae # Store the assertion error
        except Exception as e:
            print(f"Error querying or verifying conversations table on attempt {attempt+1}: {e}")
            final_exception = e # Store other errors
            # We might want to break immediately on unexpected Boto3 errors

        # Wait before retrying if verification failed and not the last attempt
        if not verification_success and attempt < max_retries - 1:
            print(f"Verification failed, waiting {retry_delay_seconds}s before retry...")
            time.sleep(retry_delay_seconds)
            
    # After the loop, assert that verification eventually succeeded
    if not verification_success:
        if final_exception:
             raise final_exception # Re-raise the last encountered exception/assertion error
        else:
             pytest.fail("Verification failed after multiple retries for unknown reasons.")

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