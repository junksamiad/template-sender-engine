import pytest
import time
import threading
from unittest.mock import patch, MagicMock, ANY
from botocore.exceptions import ClientError
import logging

# Module to test
from src_dev.channel_processor.whatsapp.app.utils import sqs_heartbeat
# Reload the module to ensure mocks are applied correctly if tests run multiple times
from importlib import reload
reload(sqs_heartbeat)
SQSHeartbeat = sqs_heartbeat.SQSHeartbeat


# --- Test Fixtures ---

@pytest.fixture(autouse=True)
def mock_boto3_client():
    """Auto-used fixture to mock boto3.client('sqs')."""
    mock_sqs = MagicMock()
    mock_sqs.change_message_visibility.return_value = {} # Default success

    # Patch boto3.client specifically within the sqs_heartbeat module
    with patch('src_dev.channel_processor.whatsapp.app.utils.sqs_heartbeat.boto3.client') as mock_client:
        mock_client.return_value = mock_sqs
        yield mock_client, mock_sqs # Yield the client mock and the SQS service mock

@pytest.fixture
def heartbeat_params():
    """Provides default parameters for SQSHeartbeat."""
    return {
        "queue_url": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue",
        "receipt_handle": "test-receipt-handle-long-string",
        "interval_sec": 1, # Short interval for testing
        "visibility_timeout_sec": 5 # Longer than interval
    }

@pytest.fixture
def heartbeat(heartbeat_params):
    """Creates an SQSHeartbeat instance for testing."""
    hb = SQSHeartbeat(**heartbeat_params)
    yield hb
    # Teardown: ensure thread is stopped if running
    if hb.running:
        hb.stop()

# --- Test Cases ---

def test_init_success(heartbeat, heartbeat_params):
    """Test successful initialization."""
    assert heartbeat.queue_url == heartbeat_params["queue_url"]
    assert heartbeat.receipt_handle == heartbeat_params["receipt_handle"]
    assert heartbeat.interval_sec == heartbeat_params["interval_sec"]
    assert heartbeat.visibility_timeout_sec == heartbeat_params["visibility_timeout_sec"]
    assert not heartbeat.running
    assert heartbeat.check_for_errors() is None
    assert isinstance(heartbeat._stop_event, threading.Event)
    assert heartbeat._thread is None

def test_init_invalid_params():
    """Test initialization raises ValueError for invalid parameters."""
    with pytest.raises(ValueError, match="queue_url and receipt_handle cannot be empty."):
        SQSHeartbeat(queue_url="", receipt_handle="handle", interval_sec=1)
    with pytest.raises(ValueError, match="queue_url and receipt_handle cannot be empty."):
        SQSHeartbeat(queue_url="url", receipt_handle="", interval_sec=1)
    with pytest.raises(ValueError, match="interval_sec must be positive."):
        SQSHeartbeat(queue_url="url", receipt_handle="handle", interval_sec=0)
    with pytest.raises(ValueError, match="interval_sec must be positive."):
        SQSHeartbeat(queue_url="url", receipt_handle="handle", interval_sec=-1)

def test_init_warning_log(heartbeat_params, caplog):
    """Test warning log if visibility timeout is not longer than interval."""
    params = heartbeat_params.copy()
    params["interval_sec"] = 5
    params["visibility_timeout_sec"] = 5
    SQSHeartbeat(**params)
    assert "Visibility timeout (5s) is not significantly longer than interval (5s)" in caplog.text

def test_init_boto_client_fails(mock_boto3_client):
    """Test initialization raises RuntimeError if boto3 client creation fails."""
    mock_client, _ = mock_boto3_client
    mock_client.side_effect = Exception("Boto init failed")
    with pytest.raises(RuntimeError, match="Could not initialize SQS client"):
        SQSHeartbeat(queue_url="url", receipt_handle="handle", interval_sec=1)

def test_start_success(heartbeat, mock_boto3_client):
    """Test start successfully starts the thread and sets state."""
    _, mock_sqs = mock_boto3_client
    assert not heartbeat.running
    heartbeat.start()
    assert heartbeat.running
    assert heartbeat._thread is not None
    assert heartbeat._thread.is_alive()
    assert not heartbeat._stop_event.is_set()
    assert heartbeat.check_for_errors() is None

    # Allow some time for the thread to run and make a call
    time.sleep(heartbeat.interval_sec * 1.5)
    mock_sqs.change_message_visibility.assert_called_once_with(
        QueueUrl=heartbeat.queue_url,
        ReceiptHandle=heartbeat.receipt_handle,
        VisibilityTimeout=heartbeat.visibility_timeout_sec
    )
    heartbeat.stop() # Clean up

def test_start_already_running(heartbeat, caplog):
    """Test starting an already running heartbeat logs a warning."""
    heartbeat.start()
    assert heartbeat.running
    caplog.clear()
    heartbeat.start() # Try starting again
    assert "Heartbeat thread already running." in caplog.text
    heartbeat.stop() # Clean up

def test_stop_success(heartbeat, mock_boto3_client):
    """Test stop signals the thread and joins it."""
    _, mock_sqs = mock_boto3_client
    heartbeat.start()
    assert heartbeat.running
    thread_before_stop = heartbeat._thread

    # Let it run once
    time.sleep(heartbeat.interval_sec * 1.5)
    assert mock_sqs.change_message_visibility.call_count >= 1

    heartbeat.stop()
    assert not heartbeat.running
    assert heartbeat._thread is None # Should be reset after stop
    assert not thread_before_stop.is_alive()
    assert heartbeat._stop_event.is_set() # Should be set by stop

def test_stop_when_not_running(heartbeat, caplog):
    """Test stop does nothing if thread is not running."""
    caplog.set_level(logging.DEBUG) # Ensure DEBUG messages are captured
    assert not heartbeat.running
    caplog.clear()
    heartbeat.stop()
    assert "Stop called but heartbeat thread was never started." in caplog.text
    assert not heartbeat.running

def test_heartbeat_runs_periodically(heartbeat, mock_boto3_client):
    """Test change_message_visibility is called multiple times."""
    _, mock_sqs = mock_boto3_client
    heartbeat.start()

    # Wait for slightly longer than 2 intervals
    time.sleep(heartbeat.interval_sec * 2.5)
    heartbeat.stop()

    assert mock_sqs.change_message_visibility.call_count >= 2 # Should have called at least twice
    mock_sqs.change_message_visibility.assert_called_with( # Check last call args
        QueueUrl=heartbeat.queue_url,
        ReceiptHandle=heartbeat.receipt_handle,
        VisibilityTimeout=heartbeat.visibility_timeout_sec
    )

def test_heartbeat_stops_on_client_error(heartbeat, mock_boto3_client, caplog):
    """Test heartbeat thread stops and logs error on ClientError."""
    mock_client, mock_sqs = mock_boto3_client
    error_response = {'Error': {'Code': 'ReceiptHandleIsInvalid', 'Message': 'Test error'}}
    client_error = ClientError(error_response, 'ChangeMessageVisibility')
    mock_sqs.change_message_visibility.side_effect = client_error

    heartbeat.start()
    # Wait for the error to occur and thread to stop
    time.sleep(heartbeat.interval_sec * 1.5)

    assert not heartbeat.running # Thread should stop itself
    assert "Heartbeat failed" in caplog.text
    assert "ReceiptHandleIsInvalid" in caplog.text
    assert isinstance(heartbeat.check_for_errors(), ClientError)
    assert heartbeat._stop_event.is_set() # Stop should be called internally

def test_heartbeat_stops_on_unexpected_error(heartbeat, mock_boto3_client, caplog):
    """Test heartbeat thread stops and logs error on unexpected Exception."""
    mock_client, mock_sqs = mock_boto3_client
    unexpected_error = ValueError("Something else broke")
    mock_sqs.change_message_visibility.side_effect = unexpected_error

    heartbeat.start()
    # Wait for the error to occur and thread to stop
    time.sleep(heartbeat.interval_sec * 1.5)

    assert not heartbeat.running # Thread should stop itself
    assert "Unexpected error in heartbeat thread" in caplog.text
    assert "ValueError: Something else broke" in caplog.text
    assert isinstance(heartbeat.check_for_errors(), ValueError)
    assert heartbeat._stop_event.is_set() # Stop should be called internally

def test_check_for_errors(heartbeat, mock_boto3_client):
    """Test check_for_errors returns None or the exception."""
    mock_client, mock_sqs = mock_boto3_client
    error_response = {'Error': {'Code': 'TestError', 'Message': 'Test error'}}
    client_error = ClientError(error_response, 'ChangeMessageVisibility')

    # Scenario 1: No error
    heartbeat.start()
    time.sleep(heartbeat.interval_sec * 0.5) # Let it run briefly
    assert heartbeat.check_for_errors() is None
    heartbeat.stop()

    # Scenario 2: Error occurs
    mock_sqs.change_message_visibility.side_effect = client_error
    heartbeat.start()
    time.sleep(heartbeat.interval_sec * 1.5) # Wait for error
    assert heartbeat.check_for_errors() is client_error
    # No need to stop, it stops itself on error

def test_running_property(heartbeat):
    """Test the running property reflects the thread state."""
    assert not heartbeat.running # Before start
    heartbeat.start()
    assert heartbeat.running # After start
    time.sleep(heartbeat.interval_sec * 0.5) # While running
    assert heartbeat.running
    heartbeat.stop()
    # Need a slight pause to ensure thread join completes and _running is updated
    time.sleep(0.1)
    assert not heartbeat.running # After stop 