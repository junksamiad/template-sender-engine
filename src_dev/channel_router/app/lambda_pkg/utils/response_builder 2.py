"""
Response Builder Utility

Provides helper functions to create standardized API Gateway Lambda Proxy responses.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger()

# Standard headers including CORS
COMMON_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*', # Adjust restrictive origins in production
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'OPTIONS,POST' # Adjust allowed methods as needed
}

def create_success_response(request_id: str) -> Dict[str, Any]:
    """
    Creates a standard success response (HTTP 200 OK).

    Args:
        request_id: The unique identifier for the request.

    Returns:
        API Gateway Lambda Proxy Integration response dictionary.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    body = {
        'status': 'success',
        'request_id': request_id,
        'message': 'Request accepted and queued for processing',
        'queue_timestamp': timestamp
    }
    
    return {
        'statusCode': 200,
        'headers': COMMON_HEADERS,
        'body': json.dumps(body)
    }

def create_error_response(error_code: str, error_message: str, request_id: Optional[str] = None, status_code_hint: int = 500) -> Dict[str, Any]:
    """
    Creates a standard error response with appropriate HTTP status code.

    Args:
        error_code: An internal error code string (e.g., 'INVALID_REQUEST').
        error_message: A descriptive error message.
        request_id: The unique identifier for the request (if available).
        status_code_hint: A suggested HTTP status code (used if error_code not mapped).

    Returns:
        API Gateway Lambda Proxy Integration response dictionary.
    """
    # Map internal error codes to HTTP status codes
    # Consistent with original build and common practices
    status_code_mapping = {
        'INVALID_REQUEST': 400,
        'MISSING_IDENTIFIERS': 400,
        'MISSING_COMPANY_DATA': 400,      # Kept from original for potential future use
        'MISSING_RECIPIENT_DATA': 400,    # Kept from original
        'MISSING_REQUEST_DATA': 400,      # Kept from original
        'MISSING_COMPANY_FIELD': 400,     # Kept from original
        'MISSING_REQUEST_ID': 400,        # Kept from original
        'INVALID_REQUEST_ID': 400,        # Kept from original
        'MISSING_CHANNEL_METHOD': 400,    # Kept from original
        'UNSUPPORTED_CHANNEL': 400,       # Kept from original
        'MISSING_INITIAL_REQUEST_TIMESTAMP': 400, # Kept from original
        'INVALID_TIMESTAMP': 400,         # Kept from original
        'TIMESTAMP_EXPIRED': 400,         # Kept from original
        'MISSING_RECIPIENT_TEL': 400,     # Kept from original
        'MISSING_RECIPIENT_EMAIL': 400,   # Kept from original
        'PAYLOAD_TOO_LARGE': 400,         # Kept from original
        'COMPANY_NOT_FOUND': 404,
        'PROJECT_INACTIVE': 403,
        'CHANNEL_NOT_ALLOWED': 403,
        'UNAUTHORIZED': 401,              # Kept from original
        'AUTHENTICATION_ERROR': 401,      # Kept from original
        'AUTHORIZATION_ERROR': 403,       # Kept from original
        'RATE_LIMIT_EXCEEDED': 429,
        'DATABASE_ERROR': 500,
        'QUEUE_ERROR': 500,
        'CONFIGURATION_ERROR': 500,
        'INTERNAL_ERROR': 500
    }

    # Determine the status code
    status_code = status_code_mapping.get(error_code, status_code_hint)
    
    # Use 'unknown' if request_id wasn't determined before the error
    request_id_to_use = request_id if request_id else 'unknown'

    body = {
        'status': 'error',
        'error_code': error_code,
        'message': error_message,
        'request_id': request_id_to_use
    }
    
    # Log specific error types if needed (optional, mirroring original)
    if error_code in ('AUTHENTICATION_ERROR', 'AUTHORIZATION_ERROR', 'UNAUTHORIZED'):
        logger.warning(f"Security error response generated: {error_code} - {error_message} (Request ID: {request_id_to_use})")
    elif status_code >= 500:
         logger.error(f"Server error response generated: {error_code} - {error_message} (Request ID: {request_id_to_use})")

    return {
        'statusCode': status_code,
        'headers': COMMON_HEADERS,
        'body': json.dumps(body)
    }
