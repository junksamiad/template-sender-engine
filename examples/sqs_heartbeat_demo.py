"""
SQS Heartbeat Pattern - Usage Example

This example demonstrates how to use the SQS heartbeat pattern
to handle long-running operations in Lambda functions triggered by SQS.
"""

import json
import time
import random
import os
import boto3
import structlog

from src.shared.sqs.heartbeat import with_heartbeat, setup_heartbeat, SQSHeartbeat, HeartbeatConfig
from src.shared.errors.exceptions import SQSHeartbeatError

# Set up logging
logger = structlog.get_logger()


def simulate_long_operation(duration_seconds):
    """Simulate a long-running operation like calling an external API."""
    logger.info(f"Starting simulated long operation ({duration_seconds} seconds)")
    time.sleep(duration_seconds)
    logger.info("Completed simulated long operation")
    return {"result": "Success", "duration": duration_seconds}


# Example 1: Using the decorator
@with_heartbeat(queue_url=os.environ.get("SQS_QUEUE_URL", "https://example.queue.amazonaws.com/queue"))
def lambda_handler_with_decorator(event, context):
    """
    Lambda handler using the decorator approach for heartbeat.
    
    This is the simplest approach for most use cases.
    """
    try:
        # Parse the SQS message
        message = event["Records"][0]
        message_body = json.loads(message["body"])
        
        logger.info("Processing message", message_id=message["messageId"])
        
        # Simulate a long-running operation that takes between 5-15 seconds
        duration = random.randint(5, 15)
        result = simulate_long_operation(duration)
        
        # Process the result
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Successfully processed message",
                "result": result
            })
        }
    except Exception as e:
        logger.error("Error processing message", error=str(e))
        raise


# Example 2: Using the function-based approach
def lambda_handler_with_function(event, context):
    """
    Lambda handler using the function-based approach for heartbeat.
    
    This gives more control over the heartbeat configuration and lifecycle.
    """
    heartbeat = None
    
    try:
        # Parse the SQS message
        message = event["Records"][0]
        receipt_handle = message["receiptHandle"]
        message_body = json.loads(message["body"])
        
        logger.info("Processing message", message_id=message["messageId"])
        
        # Set up the heartbeat
        queue_url = os.environ.get("SQS_QUEUE_URL", "https://example.queue.amazonaws.com/queue")
        heartbeat, stop_heartbeat = setup_heartbeat(
            queue_url=queue_url,
            receipt_handle=receipt_handle,
            visibility_timeout_seconds=600,  # 10 minutes
            heartbeat_interval_seconds=240,  # 4 minutes
            jitter_seconds=30,               # Add up to 30 seconds of jitter
        )
        
        # Simulate a long-running operation that takes between 5-15 seconds
        duration = random.randint(5, 15)
        result = simulate_long_operation(duration)
        
        # Process the result
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Successfully processed message",
                "result": result
            })
        }
    except Exception as e:
        logger.error("Error processing message", error=str(e))
        raise
    finally:
        # Always clean up the heartbeat if it exists
        if heartbeat:
            heartbeat.stop()


# Example 3: Using the class-based approach with context manager
def lambda_handler_with_context_manager(event, context):
    """
    Lambda handler using the context manager approach for heartbeat.
    
    This is good for controlling the exact scope of the heartbeat.
    """
    try:
        # Parse the SQS message
        message = event["Records"][0]
        receipt_handle = message["receiptHandle"]
        message_body = json.loads(message["body"])
        
        logger.info("Processing message", message_id=message["messageId"])
        
        # Set up the heartbeat configuration
        queue_url = os.environ.get("SQS_QUEUE_URL", "https://example.queue.amazonaws.com/queue")
        config = HeartbeatConfig(
            queue_url=queue_url,
            visibility_timeout_seconds=600,  # 10 minutes
            heartbeat_interval_seconds=240,  # 4 minutes
            jitter_seconds=30,               # Add up to 30 seconds of jitter
        )
        
        # Use context manager for automatic cleanup
        with SQSHeartbeat(config, receipt_handle) as heartbeat:
            # The heartbeat is now active and will extend the message visibility
            
            # Check for any initial errors
            heartbeat.check_for_errors()
            
            # Simulate a long-running operation that takes between 5-15 seconds
            duration = random.randint(5, 15)
            result = simulate_long_operation(duration)
            
            # Check for any errors that occurred during processing
            heartbeat.check_for_errors()
            
            # The heartbeat will automatically stop when exiting the context
        
        # Process the result
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Successfully processed message",
                "result": result
            })
        }
    except SQSHeartbeatError as e:
        logger.error("SQS heartbeat error", error=str(e))
        # Handle heartbeat-specific errors appropriately
        raise
    except Exception as e:
        logger.error("Error processing message", error=str(e))
        raise


# Example of how this might be used in a real AWS Lambda function processing SQS messages
"""
import json
import os
import boto3
import time

from src.shared.sqs.heartbeat import with_heartbeat
from src.services.openai import OpenAIService
from src.database.dynamodb import ConversationsTable

# Lambda handler protected by SQS heartbeat
@with_heartbeat(queue_url=os.environ["QUEUE_URL"])
def lambda_handler(event, context):
    # Extract SQS message
    message = event["Records"][0]
    message_body = json.loads(message["body"])
    
    # Initialize services
    openai_service = OpenAIService()
    conversations_table = ConversationsTable()
    
    try:
        # Create conversation record
        conversation_id = message_body["conversation_id"]
        conversations_table.create_conversation(conversation_id, "processing")
        
        # Call OpenAI API (potentially long-running operation)
        # The heartbeat will keep the SQS message invisible while this runs
        ai_response = openai_service.generate_response(message_body["prompt"])
        
        # Process the AI response
        conversations_table.update_conversation(conversation_id, "completed", ai_response)
        
        return {
            "statusCode": 200,
            "body": json.dumps({"conversation_id": conversation_id, "status": "completed"})
        }
    except Exception as e:
        # Log the error
        print(f"Error processing message: {str(e)}")
        
        # Update conversation status to failed
        conversations_table.update_conversation(conversation_id, "failed", error=str(e))
        
        # Re-raise to let SQS retry or move to DLQ
        raise
""" 