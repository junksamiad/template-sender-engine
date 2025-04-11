"""
Utility functions for handling the Context Object.
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def deserialize_context(context_json: str) -> Dict[str, Any]:
    """
    Deserializes the context object JSON string into a Python dictionary.

    Args:
        context_json: The JSON string received from the SQS message body.

    Returns:
        A dictionary representation of the context object.

    Raises:
        ValueError: If the context_json is not valid JSON.
    """
    logger.info("Deserializing context object...")
    try:
        context_object = json.loads(context_json)
        if not isinstance(context_object, dict):
            # Ensure the top level is actually a dictionary
            raise ValueError("Deserialized context is not a dictionary.")
        logger.info("Successfully deserialized context object.")
        return context_object
    except json.JSONDecodeError as e:
        logger.error(f"Failed to deserialize context JSON: {e}")
        logger.debug(f"Invalid JSON string received: {context_json[:500]}...") # Log first 500 chars
        raise ValueError("Invalid Context JSON string received.") from e
    except Exception as e:
        logger.error(f"Unexpected error during context deserialization: {str(e)}", exc_info=True)
        raise

def validate_context(context: Dict[str, Any]) -> List[str]:
    """
    Validates the structure and presence of key fields in the deserialized context object.
    This should align with the structure produced by the Channel Router's context_builder.py
    and the requirements of the Channel Processor.

    Args:
        context: The deserialized context object dictionary.

    Returns:
        A list of strings describing validation errors. An empty list indicates success.
    """
    logger.info("Validating context object structure...")
    errors = []

    # Check if the root is a dictionary
    if not isinstance(context, dict):
        errors.append("Context object root is not a dictionary.")
        # If not a dict, cannot proceed with key checks, return immediately
        logger.warning(f"Context validation failed: {errors}")
        return errors

    # 1. Check for top-level sections expected from context_builder.py
    required_top_level_keys = [
        "metadata",
        "frontend_payload",
        "company_data_payload",
        "conversation_data"
    ]
    for key in required_top_level_keys:
        if key not in context:
            errors.append(f"Missing required top-level key: '{key}'")
        elif not isinstance(context[key], dict):
            errors.append(f"Top-level key '{key}' is not a dictionary.")

    # If fundamental structure is missing, return early
    if errors:
        logger.warning(f"Context validation failed with fundamental errors: {errors}")
        return errors

    # 2. Validate nested structures (add more specific checks as needed)

    # --- frontend_payload checks ---
    fp = context.get("frontend_payload", {})
    if not fp.get("company_data", {}).get("company_id"):
        errors.append("Missing 'frontend_payload.company_data.company_id'")
    if not fp.get("company_data", {}).get("project_id"):
        errors.append("Missing 'frontend_payload.company_data.project_id'")
    if not fp.get("recipient_data", {}).get("recipient_tel"):
        # For WhatsApp processor, telephone is crucial
        errors.append("Missing 'frontend_payload.recipient_data.recipient_tel'")
    if not fp.get("request_data", {}).get("request_id"):
        errors.append("Missing 'frontend_payload.request_data.request_id'")
    if fp.get("request_data", {}).get("channel_method") != "whatsapp":
        # This processor specifically handles whatsapp
        errors.append("'frontend_payload.request_data.channel_method' is not 'whatsapp'")

    # --- company_data_payload checks ---
    cdp = context.get("company_data_payload", {})
    if not cdp.get("channel_config", {}).get("whatsapp", {}).get("whatsapp_credentials_id"):
        errors.append("Missing 'company_data_payload.channel_config.whatsapp.whatsapp_credentials_id'")
    # We might need company_whatsapp_number later for certain flows/logging
    if not cdp.get("channel_config", {}).get("whatsapp", {}).get("company_whatsapp_number"):
        errors.append("Missing 'company_data_payload.channel_config.whatsapp.company_whatsapp_number'")
    # Check for AI config reference if AI processing is intended
    ai_config = cdp.get("ai_config", {})
    openai_config = ai_config.get("openai_config", {})
    whatsapp_ai_config = openai_config.get("whatsapp", {})

    if not whatsapp_ai_config.get("api_key_reference"):
        errors.append("Missing 'company_data_payload.ai_config.openai_config.whatsapp.api_key_reference'")

    if not whatsapp_ai_config.get("assistant_id_template_sender"): # Assuming we need this one for initial send
         errors.append("Missing 'company_data_payload.ai_config.openai_config.whatsapp.assistant_id_template_sender'")

    # --- conversation_data checks ---
    conv_data = context.get("conversation_data", {})
    if not conv_data.get("conversation_id"):
        # The router *should* always generate this
        errors.append("Missing 'conversation_data.conversation_id'")

    if errors:
        logger.warning(f"Context validation failed: {errors}")
    else:
        logger.info("Context object validation successful.")

    return errors 