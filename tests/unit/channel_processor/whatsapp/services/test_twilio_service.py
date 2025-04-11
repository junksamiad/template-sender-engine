import pytest
import os
import json
from unittest.mock import patch, MagicMock
from twilio.base.exceptions import TwilioRestException

# Module to test
from src_dev.channel_processor.whatsapp.app.services import twilio_service
# Reload the module to ensure mocks are applied correctly
from importlib import reload
reload(twilio_service)

# --- Test Data ---

@pytest.fixture
def mock_twilio_config():
    return {
        "twilio_account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "twilio_auth_token": "authxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "twilio_template_sid": "HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }

@pytest.fixture
def valid_send_args(mock_twilio_config):
    return {
        "twilio_config": mock_twilio_config,
        "recipient_tel": "+15551112222",
        "twilio_sender_number": "+15553334444",
        "content_variables": {"1": "TestName", "2": "OfferCode"}
    }

@pytest.fixture
def mock_twilio_message():
    message_mock = MagicMock()
    message_mock.sid = "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    message_mock.status = "queued"
    message_mock.body = "Rendered template with TestName and OfferCode."
    return message_mock

@pytest.fixture
def patch_twilio_client(mock_twilio_message):
    # Patch the Client constructor within the twilio_service module
    with patch('src_dev.channel_processor.whatsapp.app.services.twilio_service.Client') as MockTwilioClient:
        # Configure the instance returned by the constructor
        mock_client_instance = MockTwilioClient.return_value
        # Configure the messages.create method on the instance
        mock_client_instance.messages.create.return_value = mock_twilio_message
        yield MockTwilioClient, mock_client_instance

# --- Test Cases ---

def test_send_success(patch_twilio_client, valid_send_args, mock_twilio_message):
    """Test successful message sending."""
    MockTwilioClient, mock_client_instance = patch_twilio_client

    result = twilio_service.send_whatsapp_template_message(**valid_send_args)

    assert result is not None
    assert result["message_sid"] == mock_twilio_message.sid
    assert result["body"] == mock_twilio_message.body

    # Verify Client constructor was called correctly
    MockTwilioClient.assert_called_once_with(
        valid_send_args['twilio_config']['twilio_account_sid'],
        valid_send_args['twilio_config']['twilio_auth_token']
    )
    # Verify messages.create was called correctly
    mock_client_instance.messages.create.assert_called_once_with(
        content_sid=valid_send_args['twilio_config']['twilio_template_sid'],
        from_=f"whatsapp:{valid_send_args['twilio_sender_number']}",
        content_variables=json.dumps(valid_send_args['content_variables']),
        to=f"whatsapp:{valid_send_args['recipient_tel']}"
    )

def test_send_missing_config(valid_send_args, caplog):
    """Test failure with missing Twilio configuration."""
    args = valid_send_args.copy()
    del args['twilio_config']['twilio_auth_token']
    result = twilio_service.send_whatsapp_template_message(**args)
    assert result is None
    assert "Missing required Twilio configuration" in caplog.text

def test_send_missing_recipient(valid_send_args, caplog):
    """Test failure with missing recipient number."""
    args = valid_send_args.copy()
    args['recipient_tel'] = ""
    result = twilio_service.send_whatsapp_template_message(**args)
    assert result is None
    assert "Missing recipient phone number." in caplog.text

def test_send_missing_sender(valid_send_args, caplog):
    """Test failure with missing sender number."""
    args = valid_send_args.copy()
    args['twilio_sender_number'] = None
    result = twilio_service.send_whatsapp_template_message(**args)
    assert result is None
    assert "Missing Twilio sender phone number." in caplog.text

def test_send_serialization_error(patch_twilio_client, valid_send_args, caplog):
    """Test failure when content_variables cannot be serialized."""
    args = valid_send_args.copy()
    # Use a non-serializable object (like a set)
    args['content_variables'] = {"1": "TestName", "2": set([1, 2])}

    result = twilio_service.send_whatsapp_template_message(**args)
    assert result is None
    assert "Failed to serialize content_variables to JSON" in caplog.text

def test_send_twilio_rest_exception(patch_twilio_client, valid_send_args, caplog):
    """Test handling of TwilioRestException during send."""
    MockTwilioClient, mock_client_instance = patch_twilio_client

    # Configure messages.create to raise an exception
    rest_exception = TwilioRestException(
        status=400,
        uri="/Messages",
        msg="Mock Twilio Error",
        code=63016 # Example: Failed to send template message
    )
    mock_client_instance.messages.create.side_effect = rest_exception

    result = twilio_service.send_whatsapp_template_message(**valid_send_args)
    assert result is None
    assert "Twilio API error sending message" in caplog.text
    assert "Mock Twilio Error" in caplog.text
    assert "Code: 63016" in caplog.text

def test_send_unexpected_exception(patch_twilio_client, valid_send_args, caplog):
    """Test handling of unexpected exceptions during send."""
    MockTwilioClient, mock_client_instance = patch_twilio_client

    # Configure messages.create to raise a generic exception
    mock_client_instance.messages.create.side_effect = ValueError("Something broke")

    result = twilio_service.send_whatsapp_template_message(**valid_send_args)
    assert result is None
    assert "Unexpected error sending message via Twilio" in caplog.text
    assert "ValueError: Something broke" in caplog.text

def test_send_client_init_exception(patch_twilio_client, valid_send_args, caplog):
    """Test handling of exceptions during Twilio client initialization."""
    MockTwilioClient, mock_client_instance = patch_twilio_client

    # Configure the Client constructor to raise an exception
    MockTwilioClient.side_effect = Exception("Client init failed")

    result = twilio_service.send_whatsapp_template_message(**valid_send_args)
    assert result is None
    assert "Unexpected error sending message via Twilio" in caplog.text
    assert "Client init failed" in caplog.text 