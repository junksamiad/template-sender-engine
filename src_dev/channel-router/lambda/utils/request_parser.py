"""
Utility function for parsing the request body from API Gateway events.
"""

import json
import logging
from typing import Dict, Any, Optional
import base64 # Import base64

logger = logging.getLogger()

def parse_request_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Safely extracts, potentially decodes (if Base64), and parses the JSON body 
    from an API Gateway event.

    Args:
        event: The API Gateway Lambda Proxy Integration event dictionary.

    Returns:
        A dictionary representing the parsed JSON body if successful,
        otherwise None if the body is missing, not a string, or invalid JSON.
    """
    body_str = None # Initialize to None
    try:
        if 'body' not in event or event['body'] is None:
            logger.warning("Request event is missing 'body'.")
            return None

        raw_body = event['body']
        if not isinstance(raw_body, str):
            logger.warning(f"Request body is not a string, type: {type(raw_body)}.")
            return None

        # Check if body is Base64 encoded
        if event.get('isBase64Encoded', False):
            logger.debug("Request body is Base64 encoded. Decoding...")
            try:
                body_str = base64.b64decode(raw_body).decode('utf-8')
            except (base64.binascii.Error, UnicodeDecodeError) as e:
                logger.error(f"Failed to decode Base64 body: {e}")
                return None
        else:
            body_str = raw_body # Use raw body if not encoded

        if not body_str or not body_str.strip(): # Handle empty string body (raw or decoded)
            logger.warning("Request body is effectively empty.")
            return None

        # Log the raw string before attempting to parse
        logger.debug(f"Attempting to parse body string: {body_str}")
        body = json.loads(body_str)
        logger.debug("Successfully parsed request body.") # Use debug level for success
        return body

    except json.JSONDecodeError as e:
        # Add body_str to the error log if available for better debugging
        log_body = body_str[:500] + '...' if body_str and len(body_str) > 500 else body_str
        logger.error(f"Failed to decode JSON body: {str(e)}. Body attempted: {log_body}") 
        return None
    except Exception as e:
        # Catch any other unexpected errors during parsing
        logger.error(f"Unexpected error parsing request body: {str(e)}", exc_info=True)
        return None
