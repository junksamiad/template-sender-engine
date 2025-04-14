"""
Lambda handler for the Channel Router (Development Environment).

This module serves as the entry point for the Channel Router Lambda.
It orchestrates the process of receiving API Gateway requests, validating them,
fetching configuration, building context, and routing to the appropriate SQS queue.
Authentication is handled upstream by API Gateway's API Key feature.
"""

import json
import os
import logging
import uuid
from typing import Dict, Any

# Import core modules
from .utils.request_parser import parse_request_body
from .utils.validators import validate_initiate_request
from .services import dynamodb_service
from .services import sqs_service
from .core.context_builder import build_context_object
from .utils.response_builder import create_success_response, create_error_response

# Initialize logger
logger = logging.getLogger()

# Set logger level based on environment variable
log_level_name = os.environ.get('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_name, logging.INFO)
logger.setLevel(log_level)
logger.info(f"Logger initialized with level: {log_level_name}")

# Boto3 clients are initialized within their respective service modules.

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main entry point for the Channel Router Lambda (Development).

    Args:
        event: API Gateway Lambda Proxy Integration event.
        context: Lambda context object (provides runtime info).

    Returns:
        API Gateway Lambda Proxy Integration response object.
    """
    # --- Load Environment Variables INSIDE handler ---
    # This ensures mocks work correctly during testing
    company_data_table = os.environ.get('COMPANY_DATA_TABLE')
    whatsapp_queue_url = os.environ.get('WHATSAPP_QUEUE_URL')
    email_queue_url = os.environ.get('EMAIL_QUEUE_URL')
    sms_queue_url = os.environ.get('SMS_QUEUE_URL')
    router_version = os.environ.get('VERSION', '0.0.0-dev')

    # Check essential config loaded inside handler
    if not company_data_table:
        logger.error("FATAL: COMPANY_DATA_TABLE environment variable not set!")
        # Cannot proceed without table name, return generic internal error
        # Note: request_id might not be known yet if parsing fails later
        # Returning a simple generic error here.
        return create_error_response(
            error_code='CONFIGURATION_ERROR',
            error_message='Server configuration error (missing table info).',
            request_id=str(uuid.uuid4()), # Generate a default UUID for this specific error case
            status_code_hint=500
        )
    logger.info(f"Router Version: {router_version}") # Log version inside handler

    # Default request ID, might be updated from payload later
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"Received event for default request_id: {request_id}")
        # logger.debug(f"Full event: {json.dumps(event)}") # Use debug for full event
        
        # 1. Parse Request Body
        frontend_payload_dict = parse_request_body(event)
        if frontend_payload_dict is None:
            # Parsing failed, error already logged by parse_request_body
            return create_error_response(
                error_code='INVALID_REQUEST',
                error_message='Invalid or missing request body',
                request_id=request_id, # Use default ID as we couldn't parse one
                status_code_hint=400
            )
        
        # Update request_id from payload if available
        request_id = frontend_payload_dict.get('request_data', {}).get('request_id', request_id)
        logger.info(f"Processing request_id: {request_id}")

        # 2. Extract Company/Project Info
        company_data_from_body = frontend_payload_dict.get('company_data', {})
        company_id = company_data_from_body.get('company_id')
        project_id = company_data_from_body.get('project_id')

        if not company_id or not project_id:
            logger.error(f"Missing company_id or project_id in request body for request_id {request_id}")
            return create_error_response(
                error_code='MISSING_IDENTIFIERS',
                error_message='company_id and project_id are required in company_data',
                request_id=request_id,
                status_code_hint=400
            )
        logger.info(f"Extracted company_id: {company_id}, project_id: {project_id}")

        # 3. Validate Request Body
        validation_error = validate_initiate_request(frontend_payload_dict)
        if validation_error:
            error_code, error_message = validation_error
            logger.warning(f"Validation failed: {error_code} - {error_message} (Request ID: {request_id})")
            return create_error_response(
                error_code=error_code,
                error_message=error_message,
                request_id=request_id,
                status_code_hint=400
            )
        logger.info(f"Request body validation successful for request_id: {request_id}")

        # 4. Fetch Company Configuration from DynamoDB
        company_config_result = dynamodb_service.get_company_config(company_id, project_id)
        if isinstance(company_config_result, tuple):
            error_code, error_message = company_config_result
            logger.error(f"Failed to get company config: {error_code} - {error_message} (Request ID: {request_id})")
            # Determine appropriate status code based on specific DB error type
            status_code = 500 # Default for DB/Config errors
            if error_code == 'COMPANY_NOT_FOUND': status_code = 404
            if error_code == 'PROJECT_INACTIVE': status_code = 403
            
            return create_error_response(
                error_code=error_code,
                error_message=error_message,
                request_id=request_id,
                status_code_hint=status_code
            )
        company_data_dict = company_config_result 
        logger.info("Successfully retrieved company configuration.")
        
        # 5. Check Project Status and Allowed Channels
        allowed_channels = company_data_dict.get('allowed_channels', [])
        requested_channel = frontend_payload_dict.get('request_data', {}).get('channel_method', '').lower()

        if requested_channel not in allowed_channels:
            logger.warning(f"Channel '{requested_channel}' not allowed for {company_id}/{project_id}. Allowed: {allowed_channels} (Request ID: {request_id})")
            return create_error_response(
                error_code='CHANNEL_NOT_ALLOWED',
                error_message=f"Channel '{requested_channel}' is not permitted for this project.",
                request_id=request_id,
                status_code_hint=403
            )
        logger.info(f"Requested channel '{requested_channel}' is allowed for {company_id}/{project_id}.")

        # 6. Build Context Object for SQS Message
        context_object = build_context_object(frontend_payload_dict, company_data_dict, router_version)
        logger.info(f"Context object built for request {request_id}")

        # 7. Route Context Object to Appropriate SQS Queue
        queue_url_map = {
            'whatsapp': whatsapp_queue_url,
            'email': email_queue_url,
            'sms': sms_queue_url,
        }
        queue_url = queue_url_map.get(requested_channel)
        if not queue_url:
             logger.error(f"No queue URL configured or found for channel: {requested_channel} (Request ID: {request_id})")
             return create_error_response(
                 error_code='CONFIGURATION_ERROR',
                 error_message=f'Processing queue for channel \'{requested_channel}\' is not configured.',
                 request_id=request_id,
                 status_code_hint=500
              )

        # Send the message using the SQS service
        send_result = sqs_service.send_message_to_queue(queue_url, context_object, requested_channel)
        if not send_result:
             # Error already logged within sqs_service
             return create_error_response(
                 error_code='QUEUE_ERROR',
                 error_message='Failed to send message to processing queue.',
                 request_id=request_id,
                 status_code_hint=500
              )
        logger.info(f"Successfully queued message for request {request_id} to {requested_channel} queue.")

        # 8. Return Success Response
        logger.info(f"Request {request_id} processed successfully and queued.")
        return create_success_response(request_id)

    except json.JSONDecodeError as e:
        # Handle JSON parsing error early, request_id might be the default one
        logger.error(f"Failed to decode JSON body: {str(e)} (Request ID: {request_id})")
        return create_error_response(
            error_code='INVALID_REQUEST',
            error_message=f'Invalid JSON format in request body: {str(e)}',
            request_id=request_id, # May be the default UUID if parsing failed early
            status_code_hint=400
         )
    except Exception as e:
        # Catch-all for any other unhandled exceptions
        logger.error(f"Unhandled exception for request_id {request_id}: {str(e)}", exc_info=True)
        return create_error_response(
             error_code='INTERNAL_ERROR',
             error_message='An internal server error occurred.',
             request_id=request_id,
             status_code_hint=500
         )
