import pytest
import requests
import boto3
import json
import uuid
import time
from datetime import datetime, timezone
import os # For loading sample data
from boto3.dynamodb.conditions import Key, Attr # Import Attr for FilterExpression

# --- Configuration ---
# Using known dev resource names and URLs
# API_ENDPOINT_URL = "https://xlijn1k4xh.execute-api.eu-north-1.amazonaws.com/dev/" # Ensure trailing slash
# Retrieve API endpoint from environment variable set by CI/CD or .env file for local
API_ENDPOINT_BASE_URL = os.environ.get("API_ENDPOINT")
if not API_ENDPOINT_BASE_URL:
    # Fallback or error if not set
    print("ERROR: API_ENDPOINT environment variable not set. Using hardcoded value.")
    # Use a hardcoded fallback url that doesn't duplicate the path
    API_ENDPOINT_URL = "https://xlijn1k4xh.execute-api.eu-north-1.amazonaws.com/dev/initiate-conversation"
else:
    # Ensure we don't end up with a duplicate path segment
    if API_ENDPOINT_BASE_URL.endswith('/initiate-conversation'):
        API_ENDPOINT_URL = API_ENDPOINT_BASE_URL
    else:
        API_ENDPOINT_URL = f"{API_ENDPOINT_BASE_URL.rstrip('/')}/initiate-conversation"

API_KEY = os.environ.get("API_KEY", "YbgTABlGlg6s2YZ9gcyuB4AUhi5jJcC05yeKcCWR") # Get API key from env or use default (less secure)

DYNAMODB_COMPANY_TABLE_NAME = "ai-multi-comms-company-data-dev"
DYNAMODB_CONVERSATIONS_TABLE_NAME = "ai-multi-comms-conversations-dev"
REGION = "eu-north-1"
# Sample data file paths (relative to project root)
# COMPANY_DATA_SAMPLE_PATH = "samples/recruitment_company_data_record_example_dev.json"
E2E_PAYLOAD_TEMPLATE_PATH = "scripts/e2e_test_curl_dev.sh" # Path to the script template

# --- Fixtures --- (Assumes conftest.py fixtures are available)

# Helper function to parse JSON payload from the curl script template
def parse_payload_template_from_script(script_path):
    print(f"\nParsing payload template from {script_path}...")
    try:
        with open(script_path, 'r') as f:
            content = f.read()
        # Find the start and end of the JSON block within the heredoc
        start_marker = "<<'EOF'\n"
        end_marker = "\nEOF"
        start_index = content.find(start_marker) + len(start_marker)
        end_index = content.find(end_marker)
        if start_index == -1 or end_index == -1 or start_index >= end_index:
            raise ValueError("Could not find heredoc markers EOF in script template")
        json_string = content[start_index:end_index]
        payload_template = json.loads(json_string)
        print("Payload template parsed successfully.")
        return payload_template
    except Exception as e:
        pytest.fail(f"Failed to parse JSON payload template from {script_path}: {e}")

# --- Test Case ---

def test_whatsapp_happy_path(dynamodb_client, setup_e2e_company_data):
    """
    Tests the full end-to-end happy path for initiating a WhatsApp conversation.
    Sends request, waits, verifies final DynamoDB state, and cleans up.
    Manual verification of received WhatsApp message is required separately.
    """
    # Generate unique data for this test run
    request_id = str(uuid.uuid4())
    request_timestamp = datetime.now(timezone.utc).isoformat()

    # Load payload template and inject unique data
    request_payload = parse_payload_template_from_script(E2E_PAYLOAD_TEMPLATE_PATH)
    request_payload["request_data"]["request_id"] = request_id
    request_payload["request_data"]["initial_request_timestamp"] = request_timestamp
    
    primary_channel = request_payload["recipient_data"]["recipient_tel"] # Use for cleanup query
    
    # Ensure company data is set up by using the fixture
    company_id, project_id = setup_e2e_company_data
    
    try:
        # 1. Send API Request
        headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
        
        print(f"\n--- Test: E2E Happy Path --- ")
        print(f"Request ID for this run: {request_id}")
        print(f"Sending E2E request to {API_ENDPOINT_URL}")
        response = requests.post(API_ENDPOINT_URL, headers=headers, json=request_payload)
        print(f"API Response Status: {response.status_code}")
        print(f"API Response Body: {response.text}")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data.get("status") == "success"
        assert response_data.get("request_id") == request_id
        print("API request successful.")
        
        # 2. Wait for processing
        # Reduced wait time, adjust based on typical processing latency
        wait_seconds = 25 
        print(f"Waiting {wait_seconds} seconds for end-to-end processing...")
        time.sleep(wait_seconds)
        
        # 3. Verify Final State in Conversations DynamoDB
        conversation_record = None
        print(f"\n--- Verification Attempt --- ")
        print(f"Checking {DYNAMODB_CONVERSATIONS_TABLE_NAME} for record with request_id {request_id}...")
        
        # Query by PK and filter by request_id
        query_response = dynamodb_client.query(
            TableName=DYNAMODB_CONVERSATIONS_TABLE_NAME,
            KeyConditionExpression="primary_channel = :pk",
            FilterExpression="request_id = :rid",
            ExpressionAttributeValues={
                ":pk": {"S": primary_channel},
                ":rid": {"S": request_id}
            },
            ConsistentRead=True # Use consistent read for testing immediately after action
        )
            
        items = query_response.get('Items', [])
        print(f"Found {len(items)} conversation item(s) matching request_id {request_id}.")

        if not items:
            pytest.fail(f"Could not find conversation record for request_id {request_id} after {wait_seconds}s wait.") 
        elif len(items) > 1:
             pytest.fail(f"Found multiple conversation records for request_id {request_id}. This should not happen.")
        else:
            conversation_record = items[0] # Store the found record for cleanup
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
            assert conversation_record.get("company_id", {}).get("S") == company_id
            assert conversation_record.get("project_id", {}).get("S") == project_id

            # Verify channel_method and conditional recipient identifier
            channel_method_in_record = conversation_record.get("channel_method", {}).get("S")
            assert channel_method_in_record == "whatsapp", f"Expected channel_method 'whatsapp', got '{channel_method_in_record}'"
            if channel_method_in_record in ["whatsapp", "sms"]:
                assert conversation_record.get("recipient_tel", {}).get("S") == primary_channel, "Recipient telephone number mismatch in record"
                print("Verified recipient_tel matches payload.")
            elif channel_method_in_record == "email":
                recipient_email = request_payload["recipient_data"]["recipient_email"]
                assert conversation_record.get("recipient_email", {}).get("S") == recipient_email, "Recipient email mismatch in record"
                print("Verified recipient_email matches payload.")

            assert conversation_record.get("request_id", {}).get("S") == request_id # Check request id propagation
            # --- End detailed assertions --- #
                
            print("DynamoDB final state verification successful.")

    except AssertionError as ae:
        pytest.fail(f"Assertion failed during verification: {ae}")
    except Exception as e:
        pytest.fail(f"Error during test execution: {e}")

    finally:
        # --- Cleanup: Delete the specific conversation record --- #
        try:
            if 'conversation_record' in locals() and conversation_record:
                # Check record format and extract keys
                convo_id = conversation_record.get('conversation_id', {}).get('S')
                pk = conversation_record.get('primary_channel', {}).get('S')
                
                if convo_id and pk:
                    print(f"Cleaning up conversation record: {pk}/{convo_id}")
                    dynamodb_client.delete_item(
                        TableName=DYNAMODB_CONVERSATIONS_TABLE_NAME,
                        Key={"primary_channel": {"S": pk}, "conversation_id": {"S": convo_id}}
                    )
                    print("Record deleted successfully")
                else:
                    print("Conversation record missing required key information for deletion")
            else:
                # Try to find it directly with a query using the primary_channel and request_id
                print(f"Checking if there's a record to clean up for request_id {request_id}")
                query_response = dynamodb_client.query(
                    TableName=DYNAMODB_CONVERSATIONS_TABLE_NAME,
                    KeyConditionExpression="primary_channel = :pk",
                    FilterExpression="request_id = :rid",
                    ExpressionAttributeValues={
                        ":pk": {"S": primary_channel},
                        ":rid": {"S": request_id}
                    }
                )
                
                items = query_response.get('Items', [])
                if items:
                    item = items[0]
                    convo_id = item.get('conversation_id', {}).get('S')
                    pk = item.get('primary_channel', {}).get('S')
                    
                    if convo_id and pk:
                        print(f"Found record to clean up: {pk}/{convo_id}")
                        dynamodb_client.delete_item(
                            TableName=DYNAMODB_CONVERSATIONS_TABLE_NAME,
                            Key={"primary_channel": {"S": pk}, "conversation_id": {"S": convo_id}}
                        )
                        print("Record deleted successfully")
                    else:
                        print("Found record missing required key information for deletion")
                else:
                    print(f"No record found for cleanup with request_id {request_id}")
        except Exception as e:
            print(f"Error during cleanup: {e}")
            
    print("\n--- E2E Happy Path Test Complete --- ")
    print(f"--> MANUAL VERIFICATION NEEDED: Check WhatsApp on {primary_channel} for received message.")

# Removed separate cleanup function
# def cleanup_dynamodb_record(dynamodb_client, conversation_record, recipient_tel):
#    # ... 

# Add more E2E tests based on plan... 