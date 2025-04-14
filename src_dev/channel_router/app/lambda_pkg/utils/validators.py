"""
Request validation functions for the Channel Router.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger()

# Define supported channels
SUPPORTED_CHANNELS = ['whatsapp', 'email', 'sms']

def validate_initiate_request(body: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """
    Validates the structure and content of the payload for the initiate request.

    Checks for required sections, fields, formats, and channel-specific requirements.

    Args:
        body: The parsed request body dictionary.

    Returns:
        None if validation is successful.
        A tuple containing (error_code, error_message) if validation fails.
    """

    # 1. Check for required top-level sections
    required_sections = ['company_data', 'recipient_data', 'request_data']
    for section in required_sections:
        if section not in body:
            logger.warning(f"Validation Error: Missing top-level section '{section}'.")
            return f"MISSING_{section.upper()}", f"'{section}' section is required"
        if not isinstance(body[section], dict):
             logger.warning(f"Validation Error: Section '{section}' is not a dictionary.")
             return f"INVALID_{section.upper()}_TYPE", f"'{section}' must be a dictionary"

    # Note: company_id and project_id presence is checked in index.py Step 2

    # 2. Check for required fields within request_data
    request_data = body['request_data']
    required_request_fields = ['request_id', 'channel_method', 'initial_request_timestamp']
    for field in required_request_fields:
        if field not in request_data:
            logger.warning(f"Validation Error: Missing '{field}' in request_data.")
            return f"MISSING_{field.upper()}", f"'{field}' is required in request_data"
        # Basic check for non-empty string value (further format checks below)
        if not isinstance(request_data[field], str) or not request_data[field].strip():
             logger.warning(f"Validation Error: Field '{field}' must be a non-empty string.")
             return f"INVALID_{field.upper()}_FORMAT", f"'{field}' must be a non-empty string"

    # 3. Validate request_id format (UUID v4)
    request_id = request_data['request_id']
    try:
        uuid_obj = uuid.UUID(request_id, version=4)
        # Ensure the string representation matches the input exactly
        if str(uuid_obj) != request_id:
             logger.warning(f"Validation Error: request_id '{request_id}' is not a valid canonical UUID v4.")
             return "INVALID_REQUEST_ID", "request_id must be a valid UUID v4 string"
    except ValueError:
        logger.warning(f"Validation Error: request_id '{request_id}' format is invalid.")
        return "INVALID_REQUEST_ID", "request_id must be a valid UUID v4 string"

    # 4. Validate channel_method value
    channel_method = request_data['channel_method'].lower()
    if channel_method not in SUPPORTED_CHANNELS:
        logger.warning(f"Validation Error: Unsupported channel_method '{channel_method}'.")
        return "UNSUPPORTED_CHANNEL", f"Channel method '{request_data['channel_method']}' is not supported. Must be one of: {SUPPORTED_CHANNELS}"

    # 5. Validate initial_request_timestamp format (ISO 8601)
    timestamp = request_data['initial_request_timestamp']
    try:
        # Attempt parsing after handling potential 'Z' UTC notation
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError:
        logger.warning(f"Validation Error: Invalid timestamp format '{timestamp}'.")
        return "INVALID_TIMESTAMP", "initial_request_timestamp must be a valid ISO 8601 string (e.g., YYYY-MM-DDTHH:MM:SSZ or YYYY-MM-DDTHH:MM:SS+00:00)"

    # 6. Validate channel-specific requirements in recipient_data
    recipient_data = body['recipient_data']
    if channel_method in ['whatsapp', 'sms']:
        if 'recipient_tel' not in recipient_data:
             logger.warning("Validation Error: Missing 'recipient_tel' for whatsapp/sms channel.")
             return "MISSING_RECIPIENT_TEL", f"{channel_method} channel requires 'recipient_tel' in recipient_data"
        if not isinstance(recipient_data['recipient_tel'], str) or not recipient_data['recipient_tel'].strip():
             logger.warning("Validation Error: 'recipient_tel' must be a non-empty string.")
             return "INVALID_RECIPIENT_TEL", "'recipient_tel' must be a non-empty string"

    elif channel_method == 'email':
        if 'recipient_email' not in recipient_data:
             logger.warning("Validation Error: Missing 'recipient_email' for email channel.")
             return "MISSING_RECIPIENT_EMAIL", "email channel requires 'recipient_email' in recipient_data"
        if not isinstance(recipient_data['recipient_email'], str) or not recipient_data['recipient_email'].strip():
            logger.warning("Validation Error: 'recipient_email' must be a non-empty string.")
            return "INVALID_RECIPIENT_EMAIL", "'recipient_email' must be a non-empty string"
        # TODO: Consider adding email format validation (e.g., using regex or a library)

    # 7. Validate comms_consent in recipient_data
    if 'comms_consent' not in recipient_data:
        logger.warning("Validation Error: Missing 'comms_consent' in recipient_data.")
        return "MISSING_COMMS_CONSENT", "'comms_consent' is required in recipient_data"
    
    if not isinstance(recipient_data['comms_consent'], bool):
        logger.warning(f"Validation Error: 'comms_consent' must be a boolean (true/false), got {type(recipient_data['comms_consent'])}.")
        return "INVALID_COMMS_CONSENT_TYPE", "'comms_consent' must be a boolean (true or false)"

    # If all checks pass
    logger.debug("Request body validation successful.")
    return None
