# tests/unit/channel_router/services/test_sqs_service.py

import pytest
import os
import boto3
from moto import mock_aws
import json
from botocore.exceptions import ClientError
import sys
from unittest.mock import patch, MagicMock
import time

# Add src_dev parent directory to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import the function to test
from src_dev.channel_router.app.services.sqs_service import send_message_to_queue

# --- Test Constants ---
QUEUE_NAME = 'test-channel-queue'
TEST_REGION = 'eu-north-1'

# --- Fixtures ---

@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = TEST_REGION

@pytest.fixture(scope='function')
def sqs_queue(aws_credentials):
    """Creates a mock SQS queue for testing."""
    with mock_aws():
        sqs = boto3.client('sqs', region_name=TEST_REGION)
        response = sqs.create_queue(QueueName=QUEUE_NAME)
        queue_url = response['QueueUrl']
        yield queue_url # Provide the queue URL to the test

@pytest.fixture
def sample_context_object():
    """Provides a sample context object."""
    # Based loosely on context_builder output structure
    return {
        "metadata": {"router_version": "1.0"},
        "frontend_payload": {
            "company_data": {"company_id": "c1", "project_id": "p1"},
            "recipient_data": {"recipient_tel": "+123", "recipient_email": "a@b.c"},
            "request_data": {"request_id": "r1"}
        },
        "company_data_payload": {"config": "data"},
        "conversation_data": {"conversation_id": "c1#p1#r1#123", "status": "init"}
    }

# --- Test Cases ---

@mock_aws
def test_send_message_success(sqs_queue, sample_context_object, aws_credentials):
    """Test sending a message successfully to the mock queue."""
    result = send_message_to_queue(sqs_queue, sample_context_object, 'whatsapp')
    assert result is True

    # Verify message content and attributes
    sqs = boto3.client('sqs', region_name=TEST_REGION)
    messages = sqs.receive_message(
        QueueUrl=sqs_queue,
        MaxNumberOfMessages=1,
        MessageAttributeNames=['All']
    )['Messages']

    assert len(messages) == 1
    message = messages[0]
    assert json.loads(message['Body']) == sample_context_object

    attributes = message['MessageAttributes']
    assert attributes['channelMethod']['StringValue'] == 'whatsapp'
    assert attributes['conversationId']['StringValue'] == sample_context_object['conversation_data']['conversation_id']
    assert 'routerTimestamp' in attributes
    assert attributes['recipientTel']['StringValue'] == sample_context_object['frontend_payload']['recipient_data']['recipient_tel']
    assert 'recipientEmail' not in attributes # Should only add for email channel

@mock_aws
def test_send_message_email_channel_attributes(sqs_queue, sample_context_object, aws_credentials):
    """Test message attributes are correct for the email channel."""
    sample_context_object['frontend_payload']['request_data']['channel_method'] = 'email' # Correctly simulate channel
    result = send_message_to_queue(sqs_queue, sample_context_object, 'email')
    assert result is True

    # Verify message attributes
    sqs = boto3.client('sqs', region_name=TEST_REGION)
    messages = sqs.receive_message(
        QueueUrl=sqs_queue,
        MaxNumberOfMessages=1,
        MessageAttributeNames=['All']
    )['Messages']

    assert len(messages) == 1
    attributes = messages[0]['MessageAttributes']
    assert attributes['channelMethod']['StringValue'] == 'email'
    assert attributes['recipientEmail']['StringValue'] == sample_context_object['frontend_payload']['recipient_data']['recipient_email']
    assert 'recipientTel' not in attributes

def test_send_message_no_queue_url(sample_context_object):
    """Test behavior when queue_url is empty."""
    result = send_message_to_queue("", sample_context_object, 'whatsapp')
    assert result is False

def test_send_message_serialization_error():
    """Test behavior when context_object cannot be serialized."""
    # Create an object that cannot be JSON serialized (like a set)
    invalid_context = {"data": {1, 2, 3}}
    # Need a dummy queue_url, doesn't matter as serialization fails first
    result = send_message_to_queue("dummy_url", invalid_context, 'whatsapp')
    assert result is False

@patch('src_dev.channel_router.app.services.sqs_service.sqs') # Patch the boto3 client initialized in the module
@patch('time.sleep', return_value=None) # Mock time.sleep to speed up retry tests
def test_send_message_retry_logic(mock_sleep, mock_sqs_client, sample_context_object):
    """Test that ClientErrors like ServiceUnavailable are NOT retried by the application."""
    queue_url = "mock_queue_url"
    error_response = {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Mock service error'}}
    # Simulate failure (side_effect list only needs the first error now)
    mock_sqs_client.send_message.side_effect = [
        ClientError(error_response, 'SendMessage')
        # The other entries simulating retry/success are removed as they won't be reached
    ]

    result = send_message_to_queue(queue_url, sample_context_object, 'whatsapp')

    assert result is False # Should fail immediately now
    assert mock_sqs_client.send_message.call_count == 1 # Should not retry ClientError
    assert mock_sleep.call_count == 0 # Should not sleep

@patch('src_dev.channel_router.app.services.sqs_service.sqs')
@patch('time.sleep', return_value=None)
def test_send_message_retry_fails_permanently(mock_sleep, mock_sqs_client, sample_context_object):
    """Test when retries are exhausted for a transient error."""
    queue_url = "mock_queue_url"
    error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Mock throttle error'}}
    # Simulate failure on all attempts
    mock_sqs_client.send_message.side_effect = ClientError(error_response, 'SendMessage')

    result = send_message_to_queue(queue_url, sample_context_object, 'whatsapp')

    assert result is False # Should fail immediately
    assert mock_sqs_client.send_message.call_count == 1 # Should not retry ClientError
    assert mock_sleep.call_count == 0 # Should not sleep

@patch('src_dev.channel_router.app.services.sqs_service.sqs')
def test_send_message_non_retryable_client_error(mock_sqs_client, sample_context_object):
    """Test a non-transient ClientError (e.g., InvalidParameterValue) is not retried."""
    queue_url = "mock_queue_url"
    # Simulate a non-retryable error (defined by not being in retry_exceptions tuple)
    error_response = {'Error': {'Code': 'InvalidParameterValue', 'Message': 'Mock param error'}}
    mock_sqs_client.send_message.side_effect = ClientError(error_response, 'SendMessage')

    result = send_message_to_queue(queue_url, sample_context_object, 'whatsapp')

    assert result is False # Should fail immediately
    assert mock_sqs_client.send_message.call_count == 1 # Should not retry

@patch('src_dev.channel_router.app.services.sqs_service.sqs')
def test_send_message_unexpected_error(mock_sqs_client, sample_context_object):
    """Test handling of unexpected non-ClientError exceptions."""
    queue_url = "mock_queue_url"
    mock_sqs_client.send_message.side_effect = ValueError("Something totally unexpected")

    result = send_message_to_queue(queue_url, sample_context_object, 'whatsapp')

    assert result is False # Should fail immediately
    assert mock_sqs_client.send_message.call_count == 1 # Should not retry 