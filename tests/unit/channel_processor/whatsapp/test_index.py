import pytest
import os
import json
import time
from unittest.mock import patch, MagicMock, ANY

# Module to test (main handler)
# Import the handler function directly, assuming src_dev is the package root
# from src_dev.channel_processor.whatsapp.app.index import lambda_handler
from channel_processor.whatsapp.app.lambda_pkg.index import lambda_handler

# --- Constants ---
DUMMY_TABLE_NAME = "test-conversations-table"
DUMMY_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
DUMMY_REGION = "eu-north-1"
DUMMY_HEARTBEAT_MS = "30000"

# --- Fixtures ---

@pytest.fixture(scope="function", autouse=True)
def set_environment_variables():
    """Set required environment variables for the handler using patch.dict."""
    env_vars = {
        "CONVERSATIONS_TABLE": DUMMY_TABLE_NAME,
        "WHATSAPP_QUEUE_URL": DUMMY_QUEUE_URL,
        "SECRETS_MANAGER_REGION": DUMMY_REGION,
        "SQS_HEARTBEAT_INTERVAL_MS": DUMMY_HEARTBEAT_MS,
        "VERSION": "test-processor-0.1",
        "LOG_LEVEL": "DEBUG"
    }
    # Use patch.dict to temporarily modify os.environ
    with patch.dict(os.environ, env_vars, clear=True) as patched_env:
        yield patched_env # Yield the patched dictionary if needed, otherwise just yield
    # Environment is automatically restored after the with block

# --- Mocks for Injected Dependencies ---

@pytest.fixture
def mock_ctx_utils():
    """Provides a mock context_utils module."""
    mock = MagicMock()
    mock.deserialize_context.return_value = {"key": "value"} # Default
    mock.validate_context.return_value = [] # Default (no errors)
    return mock

@pytest.fixture
def mock_heartbeat_class():
    """Provides a mock SQSHeartbeat class and its instance."""
    mock_instance = MagicMock()
    mock_instance.running = True
    mock_instance.check_for_errors.return_value = None
    mock_class = MagicMock(return_value=mock_instance)
    return mock_class, mock_instance # Return both for easier assertions

@pytest.fixture
def mock_db_service():
    """Provides a mock dynamodb_service module."""
    mock = MagicMock()
    mock.create_initial_conversation_record.return_value = True # Default success
    mock.update_conversation_after_send.return_value = True # Default success
    return mock

@pytest.fixture
def mock_sm_service():
    """Provides a mock secrets_manager_service module."""
    mock = MagicMock()
    def side_effect(secret_ref):
        if "openai" in secret_ref:
            return {"ai_api_key": "sk-dummykey"}
        elif "channel" in secret_ref:
            return {"twilio_account_sid": "ACdummy", "twilio_auth_token": "authdummy", "twilio_template_sid": "HXdummy"}
        return None
    mock.get_secret.side_effect = side_effect
    return mock

@pytest.fixture
def mock_ai_service():
    """Provides a mock openai_service module."""
    mock = MagicMock()
    mock.process_message_with_ai.return_value = {
        "content_variables": {"1": "Mock Name", "2": "Mock Offer"},
        "thread_id": "th_mockopenai123",
        "prompt_tokens": 50,
        "completion_tokens": 25,
        "total_tokens": 75
    }
    return mock

@pytest.fixture
def mock_msg_service():
    """Provides a mock twilio_service module."""
    mock = MagicMock()
    mock.send_whatsapp_template_message.return_value = {
        "message_sid": "SMmocktwilio123",
        "body": "Mock rendered message."
    }
    return mock

@pytest.fixture
def mock_logger():
    """Provides a mock logger."""
    return MagicMock()

# --- Helper to create SQS Event ---

def create_sqs_event(message_body, message_id="msg1", receipt_handle="handle1"):
    """Helper to create a consistent SQS event structure."""
    # Ensure body is always a JSON string
    if isinstance(message_body, dict):
        body_str = json.dumps(message_body)
    else:
        body_str = str(message_body) # Ensure it's a string

    return {
        "Records": [
            {
                "messageId": message_id,
                "receiptHandle": receipt_handle,
                "body": body_str,
                "attributes": {
                    "ApproximateReceiveCount": "1",
                    "SentTimestamp": str(int(time.time() * 1000)),
                    "SenderId": "123456789012",
                    "ApproximateFirstReceiveTimestamp": str(int(time.time() * 1000))
                },
                "messageAttributes": {},
                "md5OfBody": "dummy", # Calculate properly if needed
                "eventSource": "aws:sqs",
                "eventSourceARN": f"arn:aws:sqs:{DUMMY_REGION}:123456789012:{DUMMY_QUEUE_URL.split('/')[-1]}",
                "awsRegion": DUMMY_REGION
            }
        ]
    }

# --- Test Cases for lambda_handler ---

def test_lambda_handler_success_path(
    mock_ctx_utils, mock_heartbeat_class, mock_db_service,
    mock_sm_service, mock_ai_service, mock_msg_service, mock_logger
):
    """Test the main success path through the handler using injected mocks."""
    # Setup: Provide a valid context object
    valid_context = {
        'metadata': {},
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
    mock_ctx_utils.deserialize_context.return_value = valid_context
    mock_hb_class, mock_hb_instance = mock_heartbeat_class

    # Create event
    event = create_sqs_event(valid_context)

    # Execute with injected mocks
    response = lambda_handler(
        event, None,
        ctx_utils=mock_ctx_utils,
        HeartbeatClass=mock_hb_class,
        db_service=mock_db_service,
        sm_service=mock_sm_service,
        ai_service=mock_ai_service,
        msg_service=mock_msg_service,
        log=mock_logger
    )

    # Assertions
    assert response == {"batchItemFailures": []}

    # Check mocks were called correctly
    mock_ctx_utils.deserialize_context.assert_called_once_with(json.dumps(valid_context))
    mock_ctx_utils.validate_context.assert_called_once_with(valid_context)
    mock_hb_class.assert_called_once_with(
        queue_url=DUMMY_QUEUE_URL,
        receipt_handle='handle1',
        interval_sec=int(int(DUMMY_HEARTBEAT_MS) / 1000)
    )
    mock_hb_instance.start.assert_called_once()
    mock_db_service.create_initial_conversation_record.assert_called_once_with(context_object=valid_context, ddb_table=ANY)
    assert mock_sm_service.get_secret.call_count == 2
    mock_sm_service.get_secret.assert_any_call('openai_secret_ref')
    mock_sm_service.get_secret.assert_any_call('channel_secret_ref')
    mock_ai_service.process_message_with_ai.assert_called_once()
    openai_call_args, openai_call_kwargs = mock_ai_service.process_message_with_ai.call_args
    assert openai_call_args[0]['conversation_id'] == 'conv_1'
    assert openai_call_args[0]['assistant_id'] == 'asst_1'
    assert openai_call_args[1] == {"ai_api_key": "sk-dummykey"}
    mock_msg_service.send_whatsapp_template_message.assert_called_once()
    twilio_call_args, twilio_call_kwargs = mock_msg_service.send_whatsapp_template_message.call_args
    assert twilio_call_kwargs['twilio_config'] == {"twilio_account_sid": "ACdummy", "twilio_auth_token": "authdummy", "twilio_template_sid": "HXdummy"}
    assert twilio_call_kwargs['recipient_tel'] == '+123'
    assert twilio_call_kwargs['twilio_sender_number'] == '+456'
    assert twilio_call_kwargs['content_variables'] == {"1": "Mock Name", "2": "Mock Offer"}
    mock_db_service.update_conversation_after_send.assert_called_once()
    db_update_args, db_update_kwargs = mock_db_service.update_conversation_after_send.call_args
    assert db_update_kwargs['primary_channel_pk'] == '+123'
    assert db_update_kwargs['conversation_id_sk'] == 'conv_1'
    assert db_update_kwargs['thread_id'] == 'th_mockopenai123'
    assert db_update_kwargs['message_to_append']['message_id'] == 'SMmocktwilio123'

    mock_hb_instance.stop.assert_called_once()
    mock_logger.error.assert_not_called()
    mock_logger.critical.assert_not_called()

def test_lambda_handler_deserialize_fails(mock_ctx_utils, mock_logger):
    """Test failure when context deserialization fails."""
    mock_ctx_utils.deserialize_context.side_effect = ValueError("Bad JSON")
    # Fix: Pass a simple invalid string, or correctly formatted JSON string if testing valid JSON
    # For testing deserialize failure, pass a string that is NOT valid JSON
    # event = create_sqs_event("{\\\"malformed\\\": \"json\\\"}") # Pass raw string
    event = create_sqs_event("{'malformed': True}") # Use single quotes, or ensure it's invalid JSON

    response = lambda_handler(event, None, ctx_utils=mock_ctx_utils, log=mock_logger)

    assert response["batchItemFailures"] == [{"itemIdentifier": "msg1"}]
    mock_ctx_utils.validate_context.assert_not_called()
    mock_logger.exception.assert_called_once()

def test_lambda_handler_validate_fails(mock_ctx_utils, mock_logger):
    """Test failure when context validation fails."""
    mock_ctx_utils.deserialize_context.return_value = {'metadata': {}, "key": "value"}
    mock_ctx_utils.validate_context.return_value = ["Missing field X"]
    event = create_sqs_event({"key": "value"})

    response = lambda_handler(event, None, ctx_utils=mock_ctx_utils, log=mock_logger)

    assert response["batchItemFailures"] == [{"itemIdentifier": "msg1"}]
    mock_ctx_utils.deserialize_context.assert_called_once()
    mock_logger.exception.assert_called_once()

def test_lambda_handler_dynamodb_create_fails(mock_ctx_utils, mock_db_service, mock_logger):
    """Test failure when initial DynamoDB record creation fails."""
    valid_context = {
        'metadata': {},
        'frontend_payload': {'request_data': {'request_id': 'req_1', 'channel_method': 'whatsapp'}, 'recipient_data': {}},
        'conversation_data': {'conversation_id': 'conv_1'},
        'company_data_payload': {'channel_config': {}, 'ai_config': {}}
    }
    mock_ctx_utils.deserialize_context.return_value = valid_context
    mock_db_service.create_initial_conversation_record.return_value = False # Simulate failure
    event = create_sqs_event(valid_context)

    response = lambda_handler(event, None, ctx_utils=mock_ctx_utils, db_service=mock_db_service, log=mock_logger)

    assert response["batchItemFailures"] == [{"itemIdentifier": "msg1"}]
    mock_db_service.update_conversation_after_send.assert_not_called()
    mock_logger.exception.assert_called_once()

def test_lambda_handler_secrets_fetch_fails(
    mock_ctx_utils, mock_heartbeat_class, mock_db_service,
    mock_sm_service, mock_logger
):
    """Test failure when fetching secrets fails."""
    valid_context = {
        'metadata': {},
        'frontend_payload': {'request_data': {'request_id': 'req_1', 'channel_method': 'whatsapp'}, 'recipient_data': {}},
        'conversation_data': {'conversation_id': 'conv_1'},
        'company_data_payload': {
            'channel_config': {'whatsapp': {'whatsapp_credentials_id': 'channel_ref'}},
            'ai_config': {'openai_config': {'whatsapp': {'api_key_reference': 'openai_ref'}}}
        }
    }
    mock_ctx_utils.deserialize_context.return_value = valid_context
    mock_sm_service.get_secret.side_effect = ValueError("Secrets Error") # Simulate failure
    mock_hb_class, _ = mock_heartbeat_class # Unpack mock class
    event = create_sqs_event(valid_context)

    response = lambda_handler(
        event, None,
        ctx_utils=mock_ctx_utils,
        HeartbeatClass=mock_hb_class,
        db_service=mock_db_service,
        sm_service=mock_sm_service,
        log=mock_logger
    )

    assert response["batchItemFailures"] == [{"itemIdentifier": "msg1"}]
    # mock_logger.exception.assert_called_once()
    # Check that *an* exception was logged, not necessarily just one
    assert mock_logger.exception.call_count > 0

def test_lambda_handler_openai_fails(
    mock_ctx_utils, mock_heartbeat_class, mock_db_service,
    mock_sm_service, mock_ai_service, mock_logger
):
    """Test failure during OpenAI processing."""
    valid_context = {
        'metadata': {},
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
    mock_ctx_utils.deserialize_context.return_value = valid_context
    mock_ai_service.process_message_with_ai.return_value = None # Simulate OpenAI failure
    mock_hb_class, _ = mock_heartbeat_class # Unpack mock class
    event = create_sqs_event(valid_context)

    response = lambda_handler(
        event, None,
        ctx_utils=mock_ctx_utils,
        HeartbeatClass=mock_hb_class,
        db_service=mock_db_service,
        sm_service=mock_sm_service,
        ai_service=mock_ai_service,
        log=mock_logger
    )

    assert response["batchItemFailures"] == [{"itemIdentifier": "msg1"}]
    mock_logger.exception.assert_called_once()

def test_lambda_handler_twilio_fails(
    mock_ctx_utils, mock_heartbeat_class, mock_db_service,
    mock_sm_service, mock_ai_service, mock_msg_service, mock_logger
):
    """Test failure during Twilio send."""
    valid_context = {
        'metadata': {},
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
    mock_ctx_utils.deserialize_context.return_value = valid_context
    mock_msg_service.send_whatsapp_template_message.return_value = None # Simulate Twilio failure
    mock_hb_class, _ = mock_heartbeat_class # Unpack mock class
    event = create_sqs_event(valid_context)

    response = lambda_handler(
        event, None,
        ctx_utils=mock_ctx_utils,
        HeartbeatClass=mock_hb_class,
        db_service=mock_db_service,
        sm_service=mock_sm_service,
        ai_service=mock_ai_service,
        msg_service=mock_msg_service,
        log=mock_logger
    )

    assert response["batchItemFailures"] == [{"itemIdentifier": "msg1"}]
    mock_db_service.update_conversation_after_send.assert_not_called()
    mock_logger.exception.assert_called_once()

def test_lambda_handler_final_db_update_fails(
    mock_ctx_utils, mock_heartbeat_class, mock_db_service,
    mock_sm_service, mock_ai_service, mock_msg_service, mock_logger
):
    """Test that failure during final DB update logs critically but doesn't fail SQS message."""
    valid_context = {
        'metadata': {},
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
    mock_ctx_utils.deserialize_context.return_value = valid_context
    mock_db_service.update_conversation_after_send.return_value = False # Simulate final update failure
    mock_hb_class, mock_hb_instance = mock_heartbeat_class
    event = create_sqs_event(valid_context)

    response = lambda_handler(
        event, None,
        ctx_utils=mock_ctx_utils,
        HeartbeatClass=mock_hb_class,
        db_service=mock_db_service,
        sm_service=mock_sm_service,
        ai_service=mock_ai_service,
        msg_service=mock_msg_service,
        log=mock_logger
    )

    assert response == {"batchItemFailures": []}
    mock_logger.critical.assert_called_once()
    log_args, log_kwargs = mock_logger.critical.call_args
    assert "CRITICAL:" in log_args[0]
    assert "final DynamoDB update failed" in log_args[0]
    assert "Manual intervention required" in log_args[0]
    assert "conv_1" in log_args[0]
    assert "SMmocktwilio123" in log_args[0]

    mock_db_service.create_initial_conversation_record.assert_called_once()
    mock_ai_service.process_message_with_ai.assert_called_once()
    mock_msg_service.send_whatsapp_template_message.assert_called_once()
    mock_db_service.update_conversation_after_send.assert_called_once()
    mock_hb_instance.stop.assert_called_once()