"""
Utility function for parsing the request body from API Gateway events.
"""

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger()

def parse_request_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Safely extracts and parses the JSON body from an API Gateway event.

    Args:
        event: The API Gateway Lambda Proxy Integration event dictionary.

    Returns:
        A dictionary representing the parsed JSON body if successful,
        otherwise None if the body is missing, not a string, or invalid JSON.
    """
    body = None
    try:
        if 'body' not in event or event['body'] is None:
            logger.warning("Request event is missing 'body'.")
            return None

        body_str = event['body']
        if not isinstance(body_str, str):
            logger.warning(f"Request body is not a string, type: {type(body_str)}.")
            return None
        
        if not body_str.strip(): # Handle empty string body
            logger.warning("Request body is an empty string.")
            return None

        body = json.loads(body_str)
        logger.debug("Successfully parsed request body.") # Use debug level for success
        return body

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON body: {str(e)}")
        return None
    except Exception as e:
        # Catch any other unexpected errors during parsing
        logger.error(f"Unexpected error parsing request body: {str(e)}", exc_info=True)
        return None
