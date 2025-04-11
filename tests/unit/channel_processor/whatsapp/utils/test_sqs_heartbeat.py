import pytest
import time
import threading
from unittest.mock import patch, MagicMock, ANY
from botocore.exceptions import ClientError
import logging

# Update the import path to reflect the new code structure
from src_dev.channel_processor.whatsapp.app.lambda_pkg.utils import sqs_heartbeat
# Reload the module to ensure mocks are applied correctly if tests run multiple times
from importlib import reload
reload(sqs_heartbeat)
SQSHeartbeat = sqs_heartbeat.SQSHeartbeat


# --- Test Fixtures ---

@pytest.fixture(autouse=True)
def mock_boto3_client():
    """Auto-used fixture to mock boto3.client('sqs')."""
    mock_sqs_instance = MagicMock()
    mock_sqs_instance.change_message_visibility.return_value = {} # Default success

    # Patch boto3.client specifically within the sqs_heartbeat module using the correct path
    with patch('src_dev.channel_processor.whatsapp.app.lambda_pkg.utils.sqs_heartbeat.boto3.client') as mock_client_constructor:
        # Configure the constructor to return our specific SQS client mock instance
        mock_client_constructor.return_value = mock_sqs_instance
        # Yield the *instance* mock for tests to configure/assert against
        yield mock_sqs_instance

@pytest.fixture
def heartbeat(mock_boto3_client): # Ensure mock is activated before heartbeat init
    """Provides a fresh SQSHeartbeat instance for each test."""
    # Reload the module to pick up the patched boto3 client if necessary,
    # although patching the specific import is usually sufficient.
    reload(sqs_heartbeat)
    # Provide necessary arguments
    return sqs_heartbeat.SQSHeartbeat(
        queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
        receipt_handle="test-receipt-handle-long-string",
        interval_sec=1 # Short interval for testing
    )

# --- Test Cases ---

def test_init_success(heartbeat):
    """Test successful initialization with valid parameters."""
    assert heartbeat.queue_url == "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
    assert heartbeat.receipt_handle == "test-receipt-handle-long-string"
    assert heartbeat.interval_sec == 1
    assert heartbeat.visibility_timeout_sec == 600 # Default visibility extension (Updated expected value)
    assert not heartbeat.running
    assert heartbeat._thread is None
    assert heartbeat._stop_event is not None
    assert not heartbeat._stop_event.is_set()
    assert heartbeat._error is None
    # Check if _sqs_client was set (it should be if mock_boto3_client worked)
    assert heartbeat._sqs_client is not None

def test_init_invalid_params():
    """Test initialization raises ValueError for invalid parameters."""
    with pytest.raises(ValueError):
        sqs_heartbeat.SQSHeartbeat("q", "r", 0) # Zero interval
    with pytest.raises(ValueError):
        sqs_heartbeat.SQSHeartbeat("q", "r", -1) # Negative interval
    with pytest.raises(ValueError):
        sqs_heartbeat.SQSHeartbeat("", "r", 1) # Empty queue URL
    with pytest.raises(ValueError):
        sqs_heartbeat.SQSHeartbeat("q", "", 1) # Empty receipt handle

def test_init_warning_log(caplog):
    """Test warning log when interval is not shorter than visibility extension."""
    sqs_heartbeat.SQSHeartbeat("q", "r", interval_sec=5, visibility_timeout_sec=5)
    assert "Visibility timeout (5s) is not significantly longer than interval (5s)" in caplog.text

def test_init_boto_client_fails():
    """Test initialization raises RuntimeError if boto3 client creation fails."""
    # Need to patch boto3.client specifically for *this test* to raise an error
    with patch('src_dev.channel_processor.whatsapp.app.lambda_pkg.utils.sqs_heartbeat.boto3.client') as mock_boto_constructor:
        mock_boto_constructor.side_effect = Exception("Boto init failed")
        with pytest.raises(RuntimeError, match="Could not initialize SQS client"):
             # Reload module *inside* patch context if needed, but might be complex
             # Trying without reload first
            sqs_heartbeat.SQSHeartbeat("q", "r", 1)

def test_start_success(heartbeat, mock_boto3_client):
    """Test start successfully starts the thread and sets state."""
    mock_sqs_instance = mock_boto3_client # Fixture now yields the instance
    assert not heartbeat.running
    heartbeat.start()
    assert heartbeat.running
    assert heartbeat._thread is not None
    assert heartbeat._thread.is_alive()
    assert not heartbeat._stop_event.is_set()
    assert heartbeat.check_for_errors() is None

    # Allow some time for the thread to run and make a call
    time.sleep(heartbeat.interval_sec * 1.5)
    # Assert against the *instance* mock
    mock_sqs_instance.change_message_visibility.assert_called_once_with(
        QueueUrl=heartbeat.queue_url,
        ReceiptHandle=heartbeat.receipt_handle,
        VisibilityTimeout=heartbeat.visibility_timeout_sec
    )

def test_start_already_running(heartbeat, caplog):
    """Test starting an already running heartbeat logs a warning and does nothing."""
    heartbeat.start()
    thread_before = heartbeat._thread
    heartbeat.start() # Start again
    assert heartbeat.running
    assert heartbeat._thread is thread_before # Should be the same thread
    assert "Heartbeat thread already running" in caplog.text

def test_stop_success(heartbeat, mock_boto3_client):
    """Test stop signals the thread and joins it."""
    mock_sqs_instance = mock_boto3_client # Fixture now yields the instance
    heartbeat.start()
    assert heartbeat.running
    thread_before_stop = heartbeat._thread

    # Let it run once
    time.sleep(heartbeat.interval_sec * 1.5)
    # Assert against the *instance* mock
    assert mock_sqs_instance.change_message_visibility.call_count >= 1

    heartbeat.stop()
    assert not heartbeat.running
    assert heartbeat._stop_event.is_set()
    assert thread_before_stop is not None
    # Check if thread actually joined (might need timeout)
    thread_before_stop.join(timeout=2) # Wait up to 2 seconds
    assert not thread_before_stop.is_alive()
    # Check no error was recorded
    assert heartbeat.check_for_errors() is None

def test_stop_when_not_running(heartbeat):
    """Test stop does nothing if the heartbeat is not running."""
    assert not heartbeat.running
    heartbeat.stop() # Should not raise error
    assert not heartbeat.running
    assert heartbeat._thread is None

def test_heartbeat_runs_periodically(heartbeat, mock_boto3_client):
    """Test change_message_visibility is called multiple times."""
    mock_sqs_instance = mock_boto3_client # Fixture now yields the instance
    heartbeat.start()

    # Wait for slightly longer than 2 intervals
    time.sleep(heartbeat.interval_sec * 2.5)
    heartbeat.stop()

    # Assert against the *instance* mock
    assert mock_sqs_instance.change_message_visibility.call_count >= 2 # Should have called at least twice

def test_heartbeat_stops_on_client_error(heartbeat, mock_boto3_client, caplog):
    """Test heartbeat thread stops and logs error on ClientError."""
    mock_sqs_instance = mock_boto3_client # Fixture now yields the instance
    error_response = {'Error': {'Code': 'ReceiptHandleIsInvalid', 'Message': 'Test error'}}
    client_error = ClientError(error_response, 'ChangeMessageVisibility')
    # Set side effect on the *instance* mock
    mock_sqs_instance.change_message_visibility.side_effect = client_error

    heartbeat.start()
    # Wait for the error to occur and thread to stop
    time.sleep(heartbeat.interval_sec * 1.5)

    assert not heartbeat.running # Thread should stop itself
    assert heartbeat.check_for_errors() is client_error
    assert "Heartbeat failed" in caplog.text
    assert "ReceiptHandleIsInvalid" in caplog.text

def test_heartbeat_stops_on_unexpected_error(heartbeat, mock_boto3_client, caplog):
    """Test heartbeat thread stops and logs error on unexpected Exception."""
    mock_sqs_instance = mock_boto3_client # Fixture now yields the instance
    unexpected_error = ValueError("Something else broke")
    # Set side effect on the *instance* mock
    mock_sqs_instance.change_message_visibility.side_effect = unexpected_error

    heartbeat.start()
    # Wait for the error to occur and thread to stop
    time.sleep(heartbeat.interval_sec * 1.5)

    assert not heartbeat.running # Thread should stop itself
    assert heartbeat.check_for_errors() is unexpected_error
    assert "Unexpected error in heartbeat thread" in caplog.text
    assert "Something else broke" in caplog.text

def test_check_for_errors(heartbeat, mock_boto3_client):
    """Test check_for_errors returns None or the exception."""
    mock_sqs_instance = mock_boto3_client # Fixture now yields the instance
    error_response = {'Error': {'Code': 'TestError', 'Message': 'Test error'}}
    client_error = ClientError(error_response, 'ChangeMessageVisibility')

    # Scenario 1: No error
    heartbeat.start()
    time.sleep(heartbeat.interval_sec * 0.5) # Let it run briefly
    assert heartbeat.check_for_errors() is None
    heartbeat.stop()

    # Scenario 2: Error occurs
    # Reset the mock side effect for this scenario
    mock_sqs_instance.change_message_visibility.side_effect = client_error
    mock_sqs_instance.change_message_visibility.reset_mock() # Reset call count if needed
    heartbeat.start()
    time.sleep(heartbeat.interval_sec * 1.5) # Wait for error
    assert heartbeat.check_for_errors() is client_error

def test_running_property(heartbeat):
    """Test the 'running' property reflects the thread state."""
    assert not heartbeat.running
    heartbeat.start()
    assert heartbeat.running
    heartbeat.stop()
    assert not heartbeat.running 