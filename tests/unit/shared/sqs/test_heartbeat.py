"""Unit tests for the SQS heartbeat pattern implementation."""

import unittest
from unittest.mock import patch, MagicMock, call
import threading
import time
from botocore.exceptions import ClientError

from src.shared.sqs.heartbeat import (
    HeartbeatConfig,
    SQSHeartbeat,
    setup_heartbeat,
    with_heartbeat,
)
from src.shared.errors.exceptions import SQSHeartbeatError


class TestHeartbeatConfig(unittest.TestCase):
    """Test the HeartbeatConfig class."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        config = HeartbeatConfig(queue_url="https://sqs.example.com/queue")
        
        self.assertEqual(config.queue_url, "https://sqs.example.com/queue")
        self.assertEqual(config.visibility_timeout_seconds, 600)
        self.assertEqual(config.heartbeat_interval_seconds, 300)
        self.assertEqual(config.jitter_seconds, 15)

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        config = HeartbeatConfig(
            queue_url="https://sqs.example.com/queue",
            visibility_timeout_seconds=300,
            heartbeat_interval_seconds=120,
            jitter_seconds=5,
        )
        
        self.assertEqual(config.queue_url, "https://sqs.example.com/queue")
        self.assertEqual(config.visibility_timeout_seconds, 300)
        self.assertEqual(config.heartbeat_interval_seconds, 120)
        self.assertEqual(config.jitter_seconds, 5)


class TestSQSHeartbeat(unittest.TestCase):
    """Test the SQSHeartbeat class."""

    def setUp(self):
        """Set up test fixtures."""
        self.queue_url = "https://sqs.example.com/queue"
        self.receipt_handle = "receipt-handle-123"
        self.config = HeartbeatConfig(
            queue_url=self.queue_url,
            visibility_timeout_seconds=600,
            heartbeat_interval_seconds=1,  # Short interval for testing
            jitter_seconds=0,  # No jitter for predictable tests
        )
        
        # Create a mock SQS client
        self.mock_sqs_client = MagicMock()
        
        # Create the heartbeat object with the mock client
        self.heartbeat = SQSHeartbeat(
            config=self.config,
            receipt_handle=self.receipt_handle,
            sqs_client=self.mock_sqs_client,
        )

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.heartbeat.config, self.config)
        self.assertEqual(self.heartbeat.receipt_handle, self.receipt_handle)
        self.assertEqual(self.heartbeat.sqs_client, self.mock_sqs_client)
        self.assertIsNone(self.heartbeat.heartbeat_thread)
        self.assertFalse(self.heartbeat.running)
        self.assertEqual(self.heartbeat.extension_count, 0)

    @patch('boto3.client')
    def test_init_without_sqs_client(self, mock_boto3_client):
        """Test initialization without providing an SQS client."""
        mock_sqs = MagicMock()
        mock_boto3_client.return_value = mock_sqs
        
        heartbeat = SQSHeartbeat(
            config=self.config,
            receipt_handle=self.receipt_handle,
        )
        
        mock_boto3_client.assert_called_once_with("sqs")
        self.assertEqual(heartbeat.sqs_client, mock_sqs)

    def test_start_stop(self):
        """Test starting and stopping the heartbeat."""
        # Start the heartbeat
        self.heartbeat.start()
        
        # Verify that it's running
        self.assertTrue(self.heartbeat.running)
        self.assertIsNotNone(self.heartbeat.heartbeat_thread)
        self.assertTrue(self.heartbeat.heartbeat_thread.is_alive())
        
        # Stop the heartbeat
        self.heartbeat.stop()
        
        # Verify that it's stopped
        self.assertFalse(self.heartbeat.running)
        
        # Wait for the thread to exit (should be quick)
        if self.heartbeat.heartbeat_thread and self.heartbeat.heartbeat_thread.is_alive():
            self.heartbeat.heartbeat_thread.join(1.0)
        
        self.assertFalse(self.heartbeat.heartbeat_thread.is_alive())

    def test_start_already_running(self):
        """Test starting an already running heartbeat."""
        # Start the heartbeat
        self.heartbeat.start()
        thread = self.heartbeat.heartbeat_thread
        
        # Try to start it again
        self.heartbeat.start()
        
        # Verify that the thread wasn't recreated
        self.assertEqual(self.heartbeat.heartbeat_thread, thread)
        
        # Clean up
        self.heartbeat.stop()

    def test_stop_not_running(self):
        """Test stopping a heartbeat that's not running."""
        # The heartbeat is not started yet
        self.assertFalse(self.heartbeat.running)
        
        # Stop should be a no-op
        self.heartbeat.stop()
        
        # Verify that the status is still not running
        self.assertFalse(self.heartbeat.running)

    def test_heartbeat_loop_success(self):
        """Test that the heartbeat loop successfully extends visibility timeout."""
        # Set up the heartbeat with a very short interval for testing
        self.config.heartbeat_interval_seconds = 0.1
        
        # Start the heartbeat
        self.heartbeat.start()
        
        # Wait for at least one extension
        time.sleep(0.2)
        
        # Stop the heartbeat
        self.heartbeat.stop()
        
        # Verify that the client was called at least once
        self.mock_sqs_client.change_message_visibility.assert_called_with(
            QueueUrl=self.queue_url,
            ReceiptHandle=self.receipt_handle,
            VisibilityTimeout=600,
        )
        
        # Verify that the extension count was incremented
        self.assertGreaterEqual(self.heartbeat.extension_count, 1)

    def test_heartbeat_loop_error(self):
        """Test handling of errors in the heartbeat loop."""
        # Configure the mock to raise an exception
        self.mock_sqs_client.change_message_visibility.side_effect = ClientError(
            {
                "Error": {
                    "Code": "InvalidParameterValue",
                    "Message": "Value for parameter VisibilityTimeout is invalid",
                }
            },
            "ChangeMessageVisibility",
        )
        
        # Set up the heartbeat with a very short interval for testing
        self.config.heartbeat_interval_seconds = 0.1
        
        # Start the heartbeat
        self.heartbeat.start()
        
        # Wait for the error to occur and be recorded
        time.sleep(0.2)
        
        # Verify that the error event was set
        self.assertTrue(self.heartbeat.error_event.is_set())
        
        # Verify that the last error was recorded
        self.assertIsNotNone(self.heartbeat.last_error)
        self.assertIsInstance(self.heartbeat.last_error, ClientError)
        
        # Check for errors should raise an exception
        with self.assertRaises(SQSHeartbeatError):
            self.heartbeat.check_for_errors()
        
        # Clean up
        self.heartbeat.stop()

    def test_context_manager(self):
        """Test using the heartbeat as a context manager."""
        with patch.object(self.heartbeat, 'start') as mock_start, \
             patch.object(self.heartbeat, 'stop') as mock_stop:
            
            # Use as context manager
            with self.heartbeat as hb:
                self.assertEqual(hb, self.heartbeat)
                mock_start.assert_called_once()
            
            # Verify that stop was called when exiting the context
            mock_stop.assert_called_once()


class TestSetupHeartbeat(unittest.TestCase):
    """Test the setup_heartbeat function."""

    @patch('src.shared.sqs.heartbeat.SQSHeartbeat')
    def test_setup_heartbeat(self, mock_heartbeat_class):
        """Test setting up a heartbeat with the function interface."""
        # Create a mock heartbeat instance
        mock_heartbeat = MagicMock()
        mock_heartbeat_class.return_value = mock_heartbeat
        
        # Call the function
        heartbeat, stop_func = setup_heartbeat(
            queue_url="https://sqs.example.com/queue",
            receipt_handle="receipt-handle-123",
            visibility_timeout_seconds=300,
            heartbeat_interval_seconds=150,
            jitter_seconds=10,
        )
        
        # Verify that the heartbeat was created with the correct config
        mock_heartbeat_class.assert_called_once()
        config = mock_heartbeat_class.call_args[0][0]
        self.assertEqual(config.queue_url, "https://sqs.example.com/queue")
        self.assertEqual(config.visibility_timeout_seconds, 300)
        self.assertEqual(config.heartbeat_interval_seconds, 150)
        self.assertEqual(config.jitter_seconds, 10)
        
        # Verify that the receipt handle was passed correctly
        self.assertEqual(mock_heartbeat_class.call_args[0][1], "receipt-handle-123")
        
        # Verify that the heartbeat was started
        mock_heartbeat.start.assert_called_once()
        
        # Verify that the stop function works
        stop_func()
        mock_heartbeat.stop.assert_called_once()


class TestWithHeartbeat(unittest.TestCase):
    """Test the with_heartbeat decorator."""

    @patch('src.shared.sqs.heartbeat.SQSHeartbeat')
    def test_with_heartbeat_decorator(self, mock_heartbeat_class):
        """Test the decorator with receipt_handle as a parameter."""
        # Create a mock heartbeat instance
        mock_heartbeat = MagicMock()
        mock_heartbeat_class.return_value = mock_heartbeat
        
        # Create a decorated function
        @with_heartbeat(queue_url="https://sqs.example.com/queue")
        def test_func(receipt_handle, other_param):
            return f"Processed {receipt_handle} with {other_param}"
        
        # Call the decorated function
        result = test_func(receipt_handle="receipt-handle-123", other_param="value")
        
        # Verify that the heartbeat was created with the correct config
        mock_heartbeat_class.assert_called_once()
        config = mock_heartbeat_class.call_args[0][0]
        self.assertEqual(config.queue_url, "https://sqs.example.com/queue")
        
        # Verify that the receipt handle was passed correctly
        self.assertEqual(mock_heartbeat_class.call_args[0][1], "receipt-handle-123")
        
        # Verify that the heartbeat was started and stopped
        mock_heartbeat.start.assert_called_once()
        mock_heartbeat.stop.assert_called_once()
        
        # Verify that the function was called and returned the expected result
        self.assertEqual(result, "Processed receipt-handle-123 with value")

    @patch('src.shared.sqs.heartbeat.SQSHeartbeat')
    def test_with_heartbeat_decorator_event_object(self, mock_heartbeat_class):
        """Test the decorator with an event object containing SQS records."""
        # Create a mock heartbeat instance
        mock_heartbeat = MagicMock()
        mock_heartbeat_class.return_value = mock_heartbeat
        
        # Create a decorated function
        @with_heartbeat(queue_url="https://sqs.example.com/queue")
        def test_func(event, context):
            return f"Processed event with {len(event['Records'])} records"
        
        # Create an SQS event object
        event = {
            "Records": [
                {
                    "messageId": "message-id-123",
                    "receiptHandle": "receipt-handle-123",
                    "body": "message body",
                }
            ]
        }
        
        # Call the decorated function
        result = test_func(event, {})
        
        # Verify that the heartbeat was created with the correct receipt handle
        mock_heartbeat_class.assert_called_once()
        self.assertEqual(mock_heartbeat_class.call_args[0][1], "receipt-handle-123")
        
        # Verify that the heartbeat was started and stopped
        mock_heartbeat.start.assert_called_once()
        mock_heartbeat.stop.assert_called_once()
        
        # Verify that the function was called and returned the expected result
        self.assertEqual(result, "Processed event with 1 records")

    @patch('src.shared.sqs.heartbeat.logger')
    def test_with_heartbeat_decorator_no_receipt_handle(self, mock_logger):
        """Test the decorator when no receipt handle can be found."""
        # Create a decorated function
        @with_heartbeat(queue_url="https://sqs.example.com/queue")
        def test_func(param):
            return f"Processed with {param}"
        
        # Call the decorated function without a receipt handle
        result = test_func(param="value")
        
        # Verify that a warning was logged
        mock_logger.warning.assert_called_once_with(
            "Could not find receipt_handle, running without heartbeat"
        )
        
        # Verify that the function was still called
        self.assertEqual(result, "Processed with value")


if __name__ == "__main__":
    unittest.main() 