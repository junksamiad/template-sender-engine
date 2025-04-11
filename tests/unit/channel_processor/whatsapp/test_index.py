import pytest
import os
import json
import time
from unittest.mock import patch, MagicMock
import sys
from importlib import reload

# --- Print sys.path for debugging ---
print(f"sys.path during collection: {sys.path}")
# -------------------------------------

# --- Path Setup Removed --- # Handled by pytest.ini

# Module to test (main handler)
from src_dev.channel_processor.whatsapp.app import index
# Keep reload to ensure env vars are picked up by the module
reload(index)

# --- Constants ---
DUMMY_TABLE_NAME = "test-conversations-table"
DUMMY_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
DUMMY_REGION = "eu-north-1"
DUMMY_HEARTBEAT_MS = "30000"

# --- Fixtures ---

@pytest.fixture(scope="function", autouse=True)
def set_environment_variables():
    """Set required environment variables for the handler."""
    original_env = os.environ.copy()
    env_vars = {
        "CONVERSATIONS_TABLE": DUMMY_TABLE_NAME,
        "WHATSAPP_QUEUE_URL": DUMMY_QUEUE_URL,
        "SECRETS_MANAGER_REGION": DUMMY_REGION,
        "SQS_HEARTBEAT_INTERVAL_MS": DUMMY_HEARTBEAT_MS,
        "VERSION": "test-processor-0.1",
        "LOG_LEVEL": "DEBUG"
    }
    os.environ.update(env_vars)
    # Reload index module AFTER setting env vars
    reload(index)
    yield
    os.environ.clear()
    os.environ.update(original_env)
    # Reload again to restore
    reload(index)

# --- Mocks for Service Functions and Utilities ---

@pytest.fixture
def mock_context_utils():
    # Patching the functions where they are imported into index
    with patch('src_dev.channel_processor.whatsapp.app.index.deserialize_context') as mock_deserialize, \
         patch('src_dev.channel_processor.whatsapp.app.index.validate_context') as mock_validate:
        mock_deserialize.return_value = {"key": "value"} # Default return
        mock_validate.return_value = [] # Default return (no errors)
        yield {'deserialize_context': mock_deserialize, 'validate_context': mock_validate}

@pytest.fixture
def mock_sqs_heartbeat():
    mock_instance = MagicMock()
    mock_instance.running = True
    mock_instance.check_for_errors.return_value = None
    with patch('src_dev.channel_processor.whatsapp.app.index.SQSHeartbeat') as MockSQSHeartbeat:
        MockSQSHeartbeat.return_value = mock_instance
        yield MockSQSHeartbeat, mock_instance

@pytest.fixture
def mock_dynamodb_service():
    # Patch the functions where they are imported into index
    with patch('src_dev.channel_processor.whatsapp.app.index.create_initial_conversation_record') as mock_create, \
         patch('src_dev.channel_processor.whatsapp.app.index.update_conversation_after_send') as mock_update:
        mock_create.return_value = True # Default success
        mock_update.return_value = True # Default success
        # Yield dict mapping original function names to mocks
        yield {'create_initial_conversation_record': mock_create, 'update_conversation_after_send': mock_update}

@pytest.fixture
def mock_secrets_manager_service():
    # Keep full path for patch target module
    with patch('src_dev.channel_processor.whatsapp.app.index.get_secret') as mock_get_secret:
        def side_effect(secret_ref):
            if "openai" in secret_ref:
                return {"ai_api_key": "sk-dummykey"}
            elif "channel" in secret_ref:
                return {"twilio_account_sid": "ACdummy", "twilio_auth_token": "authdummy", "twilio_template_sid": "HXdummy"}
            return None
        mock_get_secret.side_effect = side_effect
        yield mock_get_secret

@pytest.fixture
def mock_openai_service():
    # Keep full path for patch target module
    with patch('src_dev.channel_processor.whatsapp.app.index.process_message_with_ai') as mock_process:
        mock_process.return_value = {
            "content_variables": {"1": "Mock Name", "2": "Mock Offer"},
            "thread_id": "th_mockopenai123",
            "prompt_tokens": 50,
            "completion_tokens": 25,
            "total_tokens": 75
        }
        yield mock_process

@pytest.fixture
def mock_twilio_service():
    # Keep full path for patch target module
    with patch('src_dev.channel_processor.whatsapp.app.index.send_whatsapp_template_message') as mock_send:
        mock_send.return_value = {
            "message_sid": "SMmocktwilio123",
            "body": "Mock rendered message."
        }
        yield mock_send

# --- Helper to create SQS Event ---

def create_sqs_event(message_body: dict, message_id="msg1", receipt_handle="handle1"):
    return {
        "Records": [
            {
                "messageId": message_id,
                "receiptHandle": receipt_handle,
                "body": json.dumps(message_body),
                "attributes": {},
                "messageAttributes": {},
                "md5OfBody": "dummy",
                "eventSource": "aws:sqs",
                "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:test-queue",
                "awsRegion": "us-east-1"
            }
        ]
    }

# --- Test Cases for lambda_handler ---

def test_lambda_handler_success_path(
    mock_context_utils, mock_sqs_heartbeat, mock_dynamodb_service,
    mock_secrets_manager_service, mock_openai_service, mock_twilio_service
):
    """Test the main success path through the handler."""
    # Setup: Provide a valid context object
    valid_context = {
        'metadata': {}, # Added missing metadata key
        'frontend_payload': {
            'request_data': {'request_id': 'req_1', 'channel_method': 'whatsapp'},
            'recipient_data': {'recipient_tel': '+123'},
            'project_data': {}
        },
        'conversation_data': {'conversation_id': 'conv_1'},
        'company_data_payload': {
            'channel_config': {'whatsapp': {'whatsapp_credentials_id': 'channel_secret_ref', 'company_whatsapp_number': '+456'}},
            'ai_config': {'openai_config': {'whatsapp': {'api_key_reference': 'openai_secret_ref', 'assistant_id_template_sender': 'asst_1'}}}
        }
    }
    mock_context_utils['deserialize_context'].return_value = valid_context
    MockSQSHeartbeat, mock_heartbeat_instance = mock_sqs_heartbeat

    # Create event
    event = create_sqs_event(valid_context) # Body is the context itself for test clarity

    # Execute
    response = index.lambda_handler(event, None)

    # Assertions
    assert response == {"batchItemFailures": []} # No failures expected

    # Check mocks were called
    mock_context_utils['deserialize_context'].assert_called_once_with(json.dumps(valid_context))
    mock_context_utils['validate_context'].assert_called_once_with(valid_context)
    MockSQSHeartbeat.assert_called_once()
    mock_heartbeat_instance.start.assert_called_once()
    mock_dynamodb_service['create_initial_conversation_record'].assert_called_once_with(valid_context)
    assert mock_secrets_manager_service.call_count == 2
    mock_secrets_manager_service.assert_any_call('openai_secret_ref')
    mock_secrets_manager_service.assert_any_call('channel_secret_ref')
    mock_openai_service.assert_called_once()
    # Check key details passed to OpenAI service
    openai_call_args = mock_openai_service.call_args[0]
    assert openai_call_args[0]['conversation_id'] == 'conv_1'
    assert openai_call_args[0]['assistant_id'] == 'asst_1'
    assert openai_call_args[1] == {"ai_api_key": "sk-dummykey"} # Credentials
    mock_twilio_service.assert_called_once()
    # Check key details passed to Twilio service using kwargs
    twilio_call_kwargs = mock_twilio_service.call_args.kwargs
    assert twilio_call_kwargs['twilio_config'] == {"twilio_account_sid": "ACdummy", "twilio_auth_token": "authdummy", "twilio_template_sid": "HXdummy"}
    assert twilio_call_kwargs['recipient_tel'] == '+123'
    assert twilio_call_kwargs['twilio_sender_number'] == '+456'
    assert twilio_call_kwargs['content_variables'] == {"1": "Mock Name", "2": "Mock Offer"}
    mock_dynamodb_service['update_conversation_after_send'].assert_called_once()
    mock_heartbeat_instance.stop.assert_called_once()

def test_lambda_handler_deserialize_fails(mock_context_utils):
    """Test failure when context deserialization fails."""
    mock_context_utils['deserialize_context'].side_effect = ValueError("Bad JSON")
    event = create_sqs_event({"malformed": "json"})

    response = index.lambda_handler(event, None)

    assert response["batchItemFailures"] == [{"itemIdentifier": "msg1"}]
    mock_context_utils['validate_context'].assert_not_called()

def test_lambda_handler_validate_fails(mock_context_utils):
    """Test failure when context validation fails."""
    mock_context_utils['deserialize_context'].return_value = {'metadata': {}, "key": "value"}
    mock_context_utils['validate_context'].return_value = ["Missing field X"]
    event = create_sqs_event({"key": "value"})

    response = index.lambda_handler(event, None)

    assert response["batchItemFailures"] == [{"itemIdentifier": "msg1"}]
    mock_context_utils['deserialize_context'].assert_called_once()

def test_lambda_handler_dynamodb_create_fails(mock_context_utils, mock_dynamodb_service):
    """Test failure when initial DynamoDB record creation fails."""
    valid_context = {
        'metadata': {}, # Added!
        'frontend_payload': {'request_data': {'request_id': 'req_1', 'channel_method': 'whatsapp'}, 'recipient_data': {}},
        'conversation_data': {'conversation_id': 'conv_1'},
        'company_data_payload': {'channel_config': {}, 'ai_config': {}}
    }
    mock_context_utils['deserialize_context'].return_value = valid_context
    mock_dynamodb_service['create_initial_conversation_record'].return_value = False # Simulate failure
    event = create_sqs_event(valid_context)

    response = index.lambda_handler(event, None)

    assert response["batchItemFailures"] == [{"itemIdentifier": "msg1"}]
    mock_dynamodb_service['update_conversation_after_send'].assert_not_called()

def test_lambda_handler_secrets_fetch_fails(mock_context_utils, mock_dynamodb_service, mock_secrets_manager_service):
    """Test failure when fetching secrets fails."""
    valid_context = {
        'metadata': {}, # Added!
        'frontend_payload': {'request_data': {'request_id': 'req_1', 'channel_method': 'whatsapp'}, 'recipient_data': {}},
        'conversation_data': {'conversation_id': 'conv_1'},
        'company_data_payload': {
            'channel_config': {'whatsapp': {'whatsapp_credentials_id': 'channel_ref'}},
            'ai_config': {'openai_config': {'whatsapp': {'api_key_reference': 'openai_ref'}}}
        }
    }
    mock_context_utils['deserialize_context'].return_value = valid_context
    mock_secrets_manager_service.side_effect = ValueError("Secrets Error") # Simulate failure
    event = create_sqs_event(valid_context)

    response = index.lambda_handler(event, None)

    assert response["batchItemFailures"] == [{"itemIdentifier": "msg1"}]

def test_lambda_handler_openai_fails(mock_context_utils, mock_dynamodb_service, mock_secrets_manager_service, mock_openai_service):
    """Test failure during OpenAI processing."""
    valid_context = {
        'metadata': {}, # Added!
        'frontend_payload': {
            'request_data': {'request_id': 'req_1', 'channel_method': 'whatsapp'},
            'recipient_data': {'recipient_tel': '+123'},
            'project_data': {}
        },
        'conversation_data': {'conversation_id': 'conv_1'},
        'company_data_payload': {
            'channel_config': {'whatsapp': {'whatsapp_credentials_id': 'channel_secret_ref', 'company_whatsapp_number': '+456'}},
            'ai_config': {'openai_config': {'whatsapp': {'api_key_reference': 'openai_secret_ref', 'assistant_id_template_sender': 'asst_1'}}}
        }
    }
    mock_context_utils['deserialize_context'].return_value = valid_context
    mock_openai_service.return_value = None # Simulate OpenAI failure
    event = create_sqs_event(valid_context)

    response = index.lambda_handler(event, None)

    assert response["batchItemFailures"] == [{"itemIdentifier": "msg1"}]

def test_lambda_handler_twilio_fails(mock_context_utils, mock_dynamodb_service, mock_secrets_manager_service, mock_openai_service, mock_twilio_service):
    """Test failure during Twilio send."""
    valid_context = {
        'metadata': {}, # Added!
        'frontend_payload': {
            'request_data': {'request_id': 'req_1', 'channel_method': 'whatsapp'},
            'recipient_data': {'recipient_tel': '+123'},
            'project_data': {}
        },
        'conversation_data': {'conversation_id': 'conv_1'},
        'company_data_payload': {
            'channel_config': {'whatsapp': {'whatsapp_credentials_id': 'channel_secret_ref', 'company_whatsapp_number': '+456'}},
            'ai_config': {'openai_config': {'whatsapp': {'api_key_reference': 'openai_secret_ref', 'assistant_id_template_sender': 'asst_1'}}}
        }
    }
    mock_context_utils['deserialize_context'].return_value = valid_context
    mock_twilio_service.return_value = None # Simulate Twilio failure
    event = create_sqs_event(valid_context)

    response = index.lambda_handler(event, None)

    assert response["batchItemFailures"] == [{"itemIdentifier": "msg1"}]
    # Crucially, the final DB update should NOT be called if Twilio fails
    mock_dynamodb_service['update_conversation_after_send'].assert_not_called()

# Test case for when final DB update fails (should NOT cause batch failure)
# Modified based on LLD: Failure here is logged critically but allows SQS message deletion
def test_lambda_handler_final_db_update_fails(mock_context_utils, mock_dynamodb_service, mock_secrets_manager_service, mock_openai_service, mock_twilio_service, caplog):
    """Test that failure during final DB update logs critically but doesn't fail SQS message."""
    valid_context = {
        'metadata': {}, # Added!
        'frontend_payload': {
            'request_data': {'request_id': 'req_1', 'channel_method': 'whatsapp'},
            'recipient_data': {'recipient_tel': '+123'},
            'project_data': {}
        },
        'conversation_data': {'conversation_id': 'conv_1'},
        'company_data_payload': {
            'channel_config': {'whatsapp': {'whatsapp_credentials_id': 'channel_secret_ref', 'company_whatsapp_number': '+456'}},
            'ai_config': {'openai_config': {'whatsapp': {'api_key_reference': 'openai_secret_ref', 'assistant_id_template_sender': 'asst_1'}}}
        }
    }
    mock_context_utils['deserialize_context'].return_value = valid_context
    mock_dynamodb_service['update_conversation_after_send'].return_value = False # Simulate final update failure
    event = create_sqs_event(valid_context)

    response = index.lambda_handler(event, None)

    # Expect NO batch item failures despite DB error
    assert response == {"batchItemFailures": []}
    # Check for critical log message
    assert "CRITICAL:" in caplog.text
    assert "final DynamoDB update failed" in caplog.text
    assert "Manual intervention required" in caplog.text
    assert "conv_1" in caplog.text
    assert "SMmocktwilio123" in caplog.text # Ensure message SID logged

    # Ensure all preceding steps were called
    mock_dynamodb_service['create_initial_conversation_record'].assert_called_once()
    mock_openai_service.assert_called_once()
    mock_twilio_service.assert_called_once()
    mock_dynamodb_service['update_conversation_after_send'].assert_called_once() 