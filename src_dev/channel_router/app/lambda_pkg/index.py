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

# Import core modules using relative paths for package execution
from .utils import request_parser
from .utils import validators
from .services import dynamodb_service
from .services import sqs_service
from .core import context_builder
from .utils import response_builder

# Initialize logger
logger = logging.getLogger()

# Set logger level based on environment variable
log_level_name = os.environ.get('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_name, logging.INFO)
logger.setLevel(log_level)
logger.info(f"Logger initialized with level: {log_level_name}")

# Boto3 clients are initialized within their respective service modules.

def lambda_handler(
    event: Dict[str, Any],
    context: Any,
    *, # Force keyword arguments for injected dependencies
    req_parser=request_parser,
    req_validator=validators,
    db_service=dynamodb_service,
    queue_service=sqs_service,
    ctx_builder=context_builder,
    resp_builder=response_builder,
    log=logger,
    id_generator=uuid # Inject uuid for easier request_id testing
) -> Dict[str, Any]:
    """
    Main entry point for the Channel Router Lambda (Development).
    Injectable dependencies: req_parser, req_validator, db_service, queue_service, ctx_builder, resp_builder, log, id_generator

    Args:
        event: API Gateway Lambda Proxy Integration event.
        context: Lambda context object (provides runtime info).

    Returns:
        API Gateway Lambda Proxy Integration response object.
    """
    # Log initialization message inside handler with potentially patched logger
    log.info(f"Logger initialized with level: {log_level_name}")

    # --- Load Environment Variables INSIDE handler ---
    # This ensures mocks work correctly during testing
    company_data_table = os.environ.get('COMPANY_DATA_TABLE')
    whatsapp_queue_url = os.environ.get('WHATSAPP_QUEUE_URL')
    email_queue_url = os.environ.get('EMAIL_QUEUE_URL')
    sms_queue_url = os.environ.get('SMS_QUEUE_URL')
    router_version = os.environ.get('VERSION', '0.0.0-dev')

    # Check essential config loaded inside handler
    if not company_data_table:
        log.error("FATAL: COMPANY_DATA_TABLE environment variable not set!")
        # Cannot proceed without table name, return generic internal error
        # Note: request_id might not be known yet if parsing fails later
        # Returning a simple generic error here.
        return resp_builder.create_error_response(
            error_code='CONFIGURATION_ERROR',
            error_message='Server configuration error (missing table info).',
            request_id=str(uuid.uuid4()), # Use default uuid directly here for simplicity
            status_code_hint=500
        )
    log.info(f"Router Version: {router_version}") # Log version inside handler

    # Default request ID, might be updated from payload later
    request_id = str(id_generator.uuid4()) # Use injected uuid
    
    try:
        log.info(f"Received event for default request_id: {request_id}")
        # logger.debug(f"Full event: {json.dumps(event)}") # Use debug for full event
        
        # 1. Parse Request Body using injected parser
        frontend_payload_dict = req_parser.parse_request_body(event)
        if frontend_payload_dict is None:
            # Parsing failed, error already logged by parse_request_body
            return resp_builder.create_error_response(
                error_code='INVALID_REQUEST',
                error_message='Invalid or missing request body',
                request_id=request_id, # Use default ID as we couldn't parse one
                status_code_hint=400
            )
        
        # Update request_id from payload if available
        request_id = frontend_payload_dict.get('request_data', {}).get('request_id', request_id)
        log.info(f"Processing request_id: {request_id}")

        # 2. Extract Company/Project Info
        company_data_from_body = frontend_payload_dict.get('company_data', {})
        company_id = company_data_from_body.get('company_id')
        project_id = company_data_from_body.get('project_id')

        if not company_id or not project_id:
            log.error(f"Missing company_id or project_id in request body for request_id {request_id}")
            return resp_builder.create_error_response(
                error_code='MISSING_IDENTIFIERS',
                error_message='company_id and project_id are required in company_data',
                request_id=request_id,
                status_code_hint=400
            )
        log.info(f"Extracted company_id: {company_id}, project_id: {project_id}")

        # 3. Validate Request Body using injected validator
        validation_error = req_validator.validate_initiate_request(frontend_payload_dict)
        if validation_error:
            error_code, error_message = validation_error
            log.warning(f"Validation failed: {error_code} - {error_message} (Request ID: {request_id})")
            return resp_builder.create_error_response(
                error_code=error_code,
                error_message=error_message,
                request_id=request_id,
                status_code_hint=400
            )
        log.info(f"Request body validation successful for request_id: {request_id}")

        # 4. Fetch Company Configuration from DynamoDB using injected service
        company_config_result = db_service.get_company_config(company_id, project_id)
        if isinstance(company_config_result, tuple):
            error_code, error_message = company_config_result
            log.error(f"Failed to get company config: {error_code} - {error_message} (Request ID: {request_id})")
            # Determine appropriate status code based on specific DB error type
            status_code = 500 # Default for DB/Config errors
            if error_code == 'COMPANY_NOT_FOUND': status_code = 404
            if error_code == 'PROJECT_INACTIVE': status_code = 403
            
            return resp_builder.create_error_response(
                error_code=error_code,
                error_message=error_message,
                request_id=request_id,
                status_code_hint=status_code
            )
        company_data_dict = company_config_result 
        log.info("Successfully retrieved company configuration.")
        
        # 5. Check Project Status and Allowed Channels
        allowed_channels = company_data_dict.get('allowed_channels', [])
        requested_channel = frontend_payload_dict.get('request_data', {}).get('channel_method', '').lower()

        if requested_channel not in allowed_channels:
            log.warning(f"Channel '{requested_channel}' not allowed for {company_id}/{project_id}. Allowed: {allowed_channels} (Request ID: {request_id})")
            return resp_builder.create_error_response(
                error_code='CHANNEL_NOT_ALLOWED',
                error_message=f"Channel '{requested_channel}' is not permitted for this project.",
                request_id=request_id,
                status_code_hint=403
            )
        log.info(f"Requested channel '{requested_channel}' is allowed for {company_id}/{project_id}.")

        # 6. Build Context Object for SQS Message using injected builder
        context_object = ctx_builder.build_context_object(frontend_payload_dict, company_data_dict, router_version)
        log.info(f"Context object built for request {request_id}")

        # 7. Route Context Object to Appropriate SQS Queue
        queue_url_map = {
            'whatsapp': whatsapp_queue_url,
            'email': email_queue_url,
            'sms': sms_queue_url,
        }
        queue_url = queue_url_map.get(requested_channel)
        if not queue_url:
             log.error(f"No queue URL configured or found for channel: {requested_channel} (Request ID: {request_id})")
             return resp_builder.create_error_response(
                 error_code='CONFIGURATION_ERROR',
                 error_message=f'Processing queue for channel \'{requested_channel}\' is not configured.',
                 request_id=request_id,
                 status_code_hint=500
              )

        # Send the message using the SQS service (injected)
        send_result = queue_service.send_message_to_queue(queue_url, context_object, requested_channel)
        if not send_result:
             # Error already logged within sqs_service
             return resp_builder.create_error_response(
                 error_code='QUEUE_ERROR',
                 error_message='Failed to send message to processing queue.',
                 request_id=request_id,
                 status_code_hint=500
              )
        log.info(f"Successfully queued message for request {request_id} to {requested_channel} queue.")

        # 8. Return Success Response using injected builder
        log.info(f"Request {request_id} processed successfully and queued.")
        return resp_builder.create_success_response(request_id)

    except json.JSONDecodeError as e:
        # Handle JSON parsing error early, request_id might be the default one
        log.error(f"Failed to decode JSON body: {str(e)} (Request ID: {request_id})")
        return resp_builder.create_error_response(
            error_code='INVALID_REQUEST',
            error_message=f'Invalid JSON format in request body: {str(e)}',
            request_id=request_id, # May be the default UUID if parsing failed early
            status_code_hint=400
         )
    except Exception as e:
        # Catch-all for any other unhandled exceptions
        log.error(f"Unhandled exception for request_id {request_id}: {str(e)}", exc_info=True)
        return resp_builder.create_error_response(
             error_code='INTERNAL_ERROR',
             error_message='An internal server error occurred.',
             request_id=request_id,
             status_code_hint=500
         )
