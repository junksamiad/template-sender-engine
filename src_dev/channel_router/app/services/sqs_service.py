"""
SQS Service Module

Handles sending messages to AWS SQS queues.
"""

import json
import logging
import time
import random
from datetime import datetime, timezone
from typing import Dict, Any, Optional, TYPE_CHECKING

import boto3
import botocore

# Import boto3 types for type hinting if available
if TYPE_CHECKING:
    from mypy_boto3_sqs.client import SQSClient

# Initialize logger
logger = logging.getLogger()

# Initialize SQS client - REMOVED
# It's generally recommended to initialize clients outside the handler/function
# for potential reuse across invocations.
# sqs = boto3.client('sqs')

def send_message_to_queue(
    queue_url: str,
    context_object: Dict[str, Any],
    channel_method: str,
    # Add optional client argument for DI
    sqs_client: Optional['SQSClient'] = None
) -> bool:
    """
    Sends the context object to the specified SQS queue with retry logic.

    Args:
        queue_url: The URL of the target SQS queue.
        context_object: The context object dictionary to send.
        channel_method: The communication channel method (e.g., 'whatsapp').
        sqs_client (SQSClient, optional): The boto3 SQS client. If None, attempts to initialize.

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    # Initialize client inside function if not provided
    if sqs_client is None:
        try:
            sqs_client = boto3.client("sqs")
            logger.debug("Initialized default SQS client.")
        except Exception as e:
            logger.exception("Failed to initialize default SQS client.")
            return False

    # Check again after attempting initialization
    if sqs_client is None:
        logger.error("SQS client could not be initialized.")
        return False

    if not queue_url:
        logger.error("Queue URL is not provided or is empty.")
        return False

    # Extract relevant information for message attributes
    # Use .get() for safe access in case keys are missing
    frontend_payload = context_object.get('frontend_payload', {})
    conversation_data = context_object.get('conversation_data', {})
    recipient_data = frontend_payload.get('recipient_data', {})

    # Use explicit defaults to highlight if expected keys are missing
    conversation_id = conversation_data.get('conversation_id', 'MISSING_conversation_id')

    # Prepare message attributes
    message_attributes = {
        'channelMethod': {
            'DataType': 'String',
            'StringValue': channel_method
        },
        'conversationId': {
            'DataType': 'String',
            'StringValue': conversation_id
        },
        'routerTimestamp': {
            'DataType': 'String',
            'StringValue': datetime.now(timezone.utc).isoformat()
        }
    }

    # Add channel-specific recipient identifier attributes if available and valid
    if channel_method.lower() in ['whatsapp', 'sms']:
        recipient_tel = recipient_data.get('recipient_tel', 'MISSING_recipient_tel')
        if recipient_tel != 'MISSING_recipient_tel' and recipient_tel: # Check not default and not empty
            message_attributes['recipientTel'] = {
                'DataType': 'String',
                'StringValue': recipient_tel
            }
    elif channel_method.lower() == 'email':
        recipient_email = recipient_data.get('recipient_email', 'MISSING_recipient_email')
        if recipient_email != 'MISSING_recipient_email' and recipient_email: # Check not default and not empty
            message_attributes['recipientEmail'] = {
                'DataType': 'String',
                'StringValue': recipient_email
            }

    # --- Retry Logic Configuration --- 
    max_retries = 3
    # Define exceptions considered transient for retry purposes
    retry_exceptions = (
        # botocore.exceptions.ClientError, # Catching broadly retries non-transient errors too
        botocore.exceptions.ConnectTimeoutError,
        botocore.exceptions.ReadTimeoutError,
        botocore.exceptions.ConnectionError,
        # Add other specific transient error codes from ClientError if needed
    )
    base_delay = 0.5  # Base delay in seconds
    # ---------------------------------

    # Try sending the message with retries for transient errors
    for attempt in range(max_retries):
        try:
            # Prepare message parameters for each attempt
            message_body = json.dumps(context_object)
            message_params = {
                'QueueUrl': queue_url,
                'MessageBody': message_body,
                'MessageAttributes': message_attributes
            }

            # Note: MessageGroupId and MessageDeduplicationId are for FIFO queues.
            # If using standard queues, these are not needed.
            # if queue_url.endswith('.fifo'):
            #     # Ensure conversation_id is suitable or adapt grouping strategy
            #     message_params['MessageGroupId'] = conversation_id 
            #     # Use a unique identifier for deduplication, request_id is often suitable if available
            #     # request_id_for_fifo = frontend_payload.get('request_data', {}).get('request_id', conversation_id)
            #     # message_params['MessageDeduplicationId'] = request_id_for_fifo 

            # Send message to SQS queue using the provided/initialized client
            response = sqs_client.send_message(**message_params)
            
            # Log success details
            logger.info(f"Message sent to {channel_method} queue. MessageId: {response.get('MessageId')}, ConversationId: {conversation_id}")
            return True # Success!

        except retry_exceptions as e:
            # Check if it's the last attempt
            if attempt < max_retries - 1:
                # Calculate delay with exponential backoff and jitter
                delay = (base_delay * (2 ** attempt)) + (random.random() * 0.1)
                logger.warning(f"Transient error sending to {queue_url} (Attempt {attempt + 1}/{max_retries}). Retrying in {delay:.2f}s. Error: {str(e)}")
                time.sleep(delay)
            else:
                # Last attempt failed
                logger.error(f"Failed to send message to {queue_url} after {max_retries} attempts. Final Error: {str(e)}")
                return False # Final failure after retries
        
        except json.JSONDecodeError as e:
            # Error serializing the context_object - non-retryable
            logger.error(f"Failed to serialize context_object to JSON for queue {queue_url}. Error: {str(e)}")
            return False # Cannot proceed

        except Exception as e:
            # Catch any other unexpected exceptions - non-retryable
            logger.error(f"Unexpected error sending message to {queue_url}. Error: {str(e)}", exc_info=True)
            return False # Failed

    # This line should technically not be reached if max_retries > 0, but included for safety.
    return False 