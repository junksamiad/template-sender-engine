"""
Implements an SQS Heartbeat mechanism using a background thread
to extend the visibility timeout of an SQS message.
"""

import threading
import time
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Optional

# Initialize logger for this module
logger = logging.getLogger(__name__)

# Default visibility timeout extension duration (matches queue default)
DEFAULT_VISIBILITY_TIMEOUT_EXTENSION_SEC = 600 # 10 minutes

class SQSHeartbeat:
    """
    Manages extending the visibility timeout for an SQS message in a background thread.
    """
    def __init__(self, queue_url: str, receipt_handle: str,
                 interval_sec: int, visibility_timeout_sec: int = DEFAULT_VISIBILITY_TIMEOUT_EXTENSION_SEC):
        """
        Initializes the SQSHeartbeat instance.

        Args:
            queue_url: The URL of the SQS queue.
            receipt_handle: The receipt handle of the message to extend.
            interval_sec: The interval (in seconds) at which to extend the visibility timeout.
                          This should be significantly less than visibility_timeout_sec.
            visibility_timeout_sec: The new visibility timeout (in seconds) to set on each extension.
        """
        if not all([queue_url, receipt_handle]):
             raise ValueError("queue_url and receipt_handle cannot be empty.")
        if interval_sec <= 0:
             raise ValueError("interval_sec must be positive.")
        if visibility_timeout_sec <= interval_sec:
             logger.warning(f"Visibility timeout ({visibility_timeout_sec}s) is not significantly longer than interval ({interval_sec}s). Heartbeat may not be effective.")

        self.queue_url = queue_url
        self.receipt_handle = receipt_handle
        self.interval_sec = interval_sec
        self.visibility_timeout_sec = visibility_timeout_sec

        # Internal state
        self._stop_event = threading.Event()
        self._thread = None
        self._error = None
        self._running = False
        self._lock = threading.Lock() # Protects access to _error and _running

        # Initialize SQS client within the class
        # The Lambda execution role must have sqs:ChangeMessageVisibility permission
        try:
            self._sqs_client = boto3.client("sqs")
        except Exception as e:
            logger.exception("Failed to initialize boto3 SQS client for heartbeat.")
            raise RuntimeError("Could not initialize SQS client for heartbeat") from e


    def _run(self):
        """The target function for the background heartbeat thread."""
        logger.info(f"Heartbeat thread started for receipt handle: ...{self.receipt_handle[-10:]}")
        while not self._stop_event.wait(self.interval_sec): # Wait for interval or stop signal
            try:
                logger.info(f"Extending visibility timeout by {self.visibility_timeout_sec}s for receipt handle: ...{self.receipt_handle[-10:]}")
                self._sqs_client.change_message_visibility(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=self.receipt_handle,
                    VisibilityTimeout=self.visibility_timeout_sec
                )
                logger.debug(f"Successfully extended visibility for ...{self.receipt_handle[-10:]}")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                logger.error(f"Heartbeat failed for ...{self.receipt_handle[-10:]}. Error: {error_code} - {e}")
                with self._lock:
                    if self._error is None:
                       self._error = e
                # Only set the stop event, don't call stop() from within the thread
                self._stop_event.set()
                break # Exit the loop immediately after setting stop event
            except Exception as e:
                logger.exception(f"Unexpected error in heartbeat thread for ...{self.receipt_handle[-10:]}: {e}")
                with self._lock:
                    if self._error is None:
                       self._error = e
                # Only set the stop event
                self._stop_event.set()
                break

        logger.info(f"Heartbeat thread stopped for receipt handle: ...{self.receipt_handle[-10:]}")
        with self._lock:
            self._running = False # Ensure running flag is set to false when thread exits

    def start(self):
        """Starts the background heartbeat thread."""
        with self._lock:
            if self._running:
                logger.warning("Heartbeat thread already running.")
                return
            if self._thread is not None and self._thread.is_alive():
                 logger.warning("Attempting to start heartbeat when previous thread might still be alive.")
                 # Optionally wait for previous thread? For now, just log.

            self._stop_event.clear() # Ensure stop event is not set
            self._error = None       # Clear any previous error
            self._thread = threading.Thread(target=self._run, daemon=True)
            # Daemon=True allows the main program to exit even if this thread is running
            # (important for Lambda execution environment)
            self._thread.start()
            self._running = True
            logger.info(f"Heartbeat thread initiated for ...{self.receipt_handle[-10:]}")

    def stop(self):
        """Signals the heartbeat thread to stop and waits for it to terminate."""
        if self._thread is None:
            logger.debug("Stop called but heartbeat thread was never started.")
            return

        if not self._stop_event.is_set():
            logger.info(f"Stopping heartbeat thread for ...{self.receipt_handle[-10:]}...")
            self._stop_event.set() # Signal the thread to stop waiting

        # Wait for the thread to finish, but don't join if it's the current thread
        current_thread = threading.current_thread()
        if self._thread is not current_thread and self._thread.is_alive():
            self._thread.join(timeout=self.interval_sec + 5) # Wait a bit longer than the interval
            if self._thread.is_alive():
                 logger.warning(f"Heartbeat thread for ...{self.receipt_handle[-10:]} did not terminate gracefully after stop signal.")
            else:
                 logger.debug(f"Heartbeat thread for ...{self.receipt_handle[-10:]} joined successfully.")
        elif self._thread is current_thread:
             logger.debug("Stop called from within the heartbeat thread itself; join skipped.")
        else:
            logger.debug(f"Stop called but heartbeat thread for ...{self.receipt_handle[-10:]} was already finished.")


        # Reset thread state after stopping
        self._thread = None
        # Note: _running flag is set to False inside the _run method when it exits.

    def check_for_errors(self) -> Optional[Exception]:
        """
        Checks if any errors occurred in the heartbeat thread.

        Returns:
            The first Exception encountered, or None if no errors occurred.
        """
        with self._lock:
            return self._error

    @property
    def running(self) -> bool:
        """Returns True if the heartbeat thread is currently marked as running."""
        with self._lock:
            # Check both the flag and the thread's liveness for robustness
            is_alive = self._thread is not None and self._thread.is_alive()
            return self._running and is_alive
