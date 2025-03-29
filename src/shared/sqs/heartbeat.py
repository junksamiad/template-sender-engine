"""
SQS Heartbeat Pattern Implementation.

This module implements the SQS Heartbeat Pattern to handle long-running
operations in Lambda functions that process SQS messages. The pattern extends
message visibility timeouts periodically to prevent message re-processing
while long-running operations complete.
"""

import time
import threading
import logging
import functools
import random
from typing import Any, Callable, Dict, Optional, Tuple, Union
import boto3
from botocore.exceptions import ClientError

import structlog

from src.shared.errors.exceptions import SQSHeartbeatError

# Configure structured logger
logger = structlog.get_logger()


class HeartbeatConfig:
    """Configuration for the SQS Heartbeat pattern."""

    def __init__(
        self,
        queue_url: str,
        visibility_timeout_seconds: int = 600,  # 10 minutes
        heartbeat_interval_seconds: int = 300,  # 5 minutes
        jitter_seconds: int = 15,  # Add 0-15 seconds of jitter
    ):
        """
        Initialize the HeartbeatConfig.

        Args:
            queue_url: The SQS queue URL
            visibility_timeout_seconds: The visibility timeout to set when extending
            heartbeat_interval_seconds: How often to extend the visibility timeout
            jitter_seconds: Random seconds to add to interval to prevent synchronized extensions
        """
        self.queue_url = queue_url
        self.visibility_timeout_seconds = visibility_timeout_seconds
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self.jitter_seconds = jitter_seconds


class SQSHeartbeat:
    """
    Implements the SQS Heartbeat pattern for long-running operations.

    This class periodically extends the visibility timeout of an SQS message
    while a Lambda function is processing it. This prevents the message from
    becoming visible again and potentially being processed by another Lambda
    instance.
    """

    def __init__(
        self,
        config: HeartbeatConfig,
        receipt_handle: str,
        sqs_client: Optional[Any] = None,
    ):
        """
        Initialize the SQS Heartbeat.

        Args:
            config: Heartbeat configuration
            receipt_handle: The receipt handle of the SQS message
            sqs_client: Optional pre-configured boto3 SQS client
        """
        self.config = config
        self.receipt_handle = receipt_handle
        self.sqs_client = sqs_client or boto3.client("sqs")
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.error_event = threading.Event()
        self.last_error: Optional[Exception] = None
        self.extension_count = 0
        self.running = False

    def _heartbeat_loop(self) -> None:
        """
        The main heartbeat loop that runs in a background thread.
        Periodically extends the visibility timeout of the SQS message.
        """
        logger.info("Starting SQS heartbeat loop", receipt_handle=self.receipt_handle[:10] + "...")

        while not self.stop_event.is_set():
            try:
                # Extend the visibility timeout
                self.sqs_client.change_message_visibility(
                    QueueUrl=self.config.queue_url,
                    ReceiptHandle=self.receipt_handle,
                    VisibilityTimeout=self.config.visibility_timeout_seconds,
                )
                
                self.extension_count += 1
                
                # Log with structured logging
                logger.info(
                    "Extended SQS message visibility timeout",
                    receipt_handle=self.receipt_handle[:10] + "...",
                    visibility_timeout=self.config.visibility_timeout_seconds,
                    extension_count=self.extension_count,
                )
                
                # Sleep until the next heartbeat interval with jitter
                jitter = random.randint(0, self.config.jitter_seconds)
                sleep_time = self.config.heartbeat_interval_seconds + jitter
                
                # Use the stop_event to allow for clean shutdown
                # This allows the thread to be interrupted if stop() is called
                if self.stop_event.wait(timeout=sleep_time):
                    break
                    
            except ClientError as e:
                logger.error(
                    "Failed to extend SQS message visibility timeout",
                    receipt_handle=self.receipt_handle[:10] + "...",
                    error=str(e),
                    error_code=e.response.get("Error", {}).get("Code", "Unknown"),
                )
                
                self.last_error = e
                self.error_event.set()
                
                # Sleep for a short time before retrying
                # Use a shorter interval when errors occur
                if self.stop_event.wait(timeout=30):  # 30 seconds
                    break
            except Exception as e:
                logger.error(
                    "Unexpected error in SQS heartbeat thread",
                    receipt_handle=self.receipt_handle[:10] + "...",
                    error=str(e),
                )
                
                self.last_error = e
                self.error_event.set()
                
                # Use a shorter interval when errors occur
                if self.stop_event.wait(timeout=30):  # 30 seconds
                    break

        logger.info(
            "SQS heartbeat loop stopped",
            receipt_handle=self.receipt_handle[:10] + "...",
            extension_count=self.extension_count,
        )

    def start(self) -> 'SQSHeartbeat':
        """
        Start the heartbeat thread to periodically extend the message visibility timeout.
        
        Returns:
            self: Returns self for method chaining
        """
        if self.running:
            logger.warning(
                "SQS heartbeat already running",
                receipt_handle=self.receipt_handle[:10] + "..."
            )
            return self
            
        # Reset tracking properties
        self.stop_event.clear()
        self.error_event.clear()
        self.last_error = None
        self.extension_count = 0
        
        # Create and start the background thread
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,  # Daemon threads exit when main thread exits
        )
        self.heartbeat_thread.start()
        self.running = True
        
        logger.info(
            "Started SQS heartbeat thread",
            receipt_handle=self.receipt_handle[:10] + "...",
            interval_seconds=self.config.heartbeat_interval_seconds,
            visibility_timeout=self.config.visibility_timeout_seconds,
        )
        
        return self

    def stop(self) -> None:
        """
        Stop the heartbeat thread.
        
        This should be called when message processing is complete or has failed.
        """
        if not self.running:
            logger.debug(
                "SQS heartbeat not running, no need to stop",
                receipt_handle=self.receipt_handle[:10] + "..."
            )
            return
            
        logger.info(
            "Stopping SQS heartbeat thread",
            receipt_handle=self.receipt_handle[:10] + "...",
            extension_count=self.extension_count,
        )
        
        # Signal the thread to stop
        self.stop_event.set()
        
        # Wait for the thread to stop (with timeout)
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=2.0)
            
        self.running = False
        
        # Log completion
        logger.info(
            "SQS heartbeat thread stopped successfully",
            receipt_handle=self.receipt_handle[:10] + "...",
            extension_count=self.extension_count,
        )

    def check_for_errors(self) -> None:
        """
        Check if the heartbeat thread has encountered any errors.
        
        Raises:
            SQSHeartbeatError: If any errors occurred in the heartbeat thread
        """
        if self.error_event.is_set() and self.last_error:
            error_msg = f"SQS heartbeat encountered an error: {str(self.last_error)}"
            logger.error(
                "SQS heartbeat error detected",
                receipt_handle=self.receipt_handle[:10] + "...",
                error=str(self.last_error),
            )
            raise SQSHeartbeatError(error_msg, original_error=self.last_error)

    def __enter__(self) -> 'SQSHeartbeat':
        """
        Context manager entry.
        
        Returns:
            self: The SQSHeartbeat instance
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Context manager exit.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        self.stop()


# Function-based interface for more convenient usage
def setup_heartbeat(
    queue_url: str,
    receipt_handle: str,
    visibility_timeout_seconds: int = 600,
    heartbeat_interval_seconds: int = 300,
    jitter_seconds: int = 15,
    sqs_client: Optional[Any] = None,
) -> Tuple[SQSHeartbeat, Callable[[], None]]:
    """
    Set up an SQS heartbeat for a message.
    
    This is a convenience function that creates and starts a heartbeat thread.
    
    Args:
        queue_url: The SQS queue URL
        receipt_handle: The receipt handle of the SQS message
        visibility_timeout_seconds: The visibility timeout to set when extending
        heartbeat_interval_seconds: How often to extend the visibility timeout
        jitter_seconds: Random seconds to add to interval to prevent synchronized extensions
        sqs_client: Optional pre-configured boto3 SQS client
        
    Returns:
        Tuple containing:
        - The SQSHeartbeat instance
        - A function to stop the heartbeat
    """
    config = HeartbeatConfig(
        queue_url=queue_url,
        visibility_timeout_seconds=visibility_timeout_seconds,
        heartbeat_interval_seconds=heartbeat_interval_seconds,
        jitter_seconds=jitter_seconds,
    )
    
    heartbeat = SQSHeartbeat(config, receipt_handle, sqs_client)
    heartbeat.start()
    
    return heartbeat, heartbeat.stop
    

# Decorator for protecting functions with heartbeat
def with_heartbeat(
    queue_url: str,
    visibility_timeout_seconds: int = 600,
    heartbeat_interval_seconds: int = 300,
    jitter_seconds: int = 15,
):
    """
    Decorator to protect a function with the SQS heartbeat pattern.
    
    This decorator automatically sets up and tears down a heartbeat for the decorated function.
    The decorated function must take 'receipt_handle' as one of its parameters.
    
    Args:
        queue_url: The SQS queue URL
        visibility_timeout_seconds: The visibility timeout to set when extending
        heartbeat_interval_seconds: How often to extend the visibility timeout
        jitter_seconds: Random seconds to add to interval to prevent synchronized extensions
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract receipt_handle from args or kwargs
            receipt_handle = None
            if 'receipt_handle' in kwargs:
                receipt_handle = kwargs['receipt_handle']
            
            if not receipt_handle:
                # Try to find event in args or kwargs and extract receipt_handle
                event = None
                for arg in args:
                    if isinstance(arg, dict) and 'Records' in arg:
                        event = arg
                        break
                
                if not event and 'event' in kwargs and isinstance(kwargs['event'], dict):
                    event = kwargs['event']
                
                if event and 'Records' in event and len(event['Records']) > 0:
                    receipt_handle = event['Records'][0].get('receiptHandle')
            
            if not receipt_handle:
                logger.warning("Could not find receipt_handle, running without heartbeat")
                return func(*args, **kwargs)
            
            # Set up heartbeat
            config = HeartbeatConfig(
                queue_url=queue_url,
                visibility_timeout_seconds=visibility_timeout_seconds,
                heartbeat_interval_seconds=heartbeat_interval_seconds,
                jitter_seconds=jitter_seconds,
            )
            
            heartbeat = SQSHeartbeat(config, receipt_handle)
            
            try:
                # Start heartbeat and run the function
                heartbeat.start()
                return func(*args, **kwargs)
            finally:
                # Always stop the heartbeat
                heartbeat.stop()
                
        return wrapper
    return decorator 