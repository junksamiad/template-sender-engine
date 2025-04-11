"""
Handles interactions with the Twilio API for sending WhatsApp messages.
"""
import logging
import os
from typing import Dict, Any, Optional

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import json # Import json for content_variables formatting

# Initialize logger
logger = logging.getLogger(__name__)

def send_whatsapp_template_message(
    twilio_config: Dict[str, Any],
    recipient_tel: str,
    twilio_sender_number: str,
    content_variables: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Sends a WhatsApp message using a pre-approved Twilio Content Template.

    Args:
        twilio_config: Dictionary containing Twilio credentials.
                       Expected keys: 'twilio_account_sid', 'twilio_auth_token', 
                                      'twilio_template_sid'.
        recipient_tel: The recipient's phone number (e.g., "+14155238886").
        twilio_sender_number: The Twilio WhatsApp number sending the message (e.g., "+14155238886").
        content_variables: A dictionary of variables to substitute into the template.
                           Keys should match the {{#}} placeholders in the template.

    Returns:
        A dictionary containing 'message_sid' (str) and 'body' (str) if successful,
        None otherwise.
    """
    # Use the keys defined in the LLD secret structure
    account_sid = twilio_config.get('twilio_account_sid') 
    auth_token = twilio_config.get('twilio_auth_token')
    content_sid = twilio_config.get('twilio_template_sid') # Get template SID from config dict

    # Check core credentials from config
    if not all([account_sid, auth_token, content_sid]):
        logger.error("Missing required Twilio configuration: account_sid, auth_token, or whatsapp_sender_number.")
        return None

    if not recipient_tel:
        logger.error("Missing recipient phone number.")
        return None

    # Check the separately provided sender number
    if not twilio_sender_number:
        logger.error("Missing Twilio sender phone number.")
        return None

    # Ensure phone numbers are prefixed correctly for Twilio API
    formatted_sender = f"whatsapp:{twilio_sender_number}"
    formatted_recipient = f"whatsapp:{recipient_tel}"

    # Convert content_variables dict to JSON string for the API call
    try:
        content_variables_json = json.dumps(content_variables)
    except TypeError as e:
        logger.error(f"Failed to serialize content_variables to JSON: {e}. Variables: {content_variables}")
        return None

    logger.info(f"Attempting to send WhatsApp template message via Twilio.")
    logger.debug(f"  To: {formatted_recipient}")
    logger.debug(f"  From: {formatted_sender}")
    logger.debug(f"  Content SID: {content_sid}")
    logger.debug(f"  Content Variables: {content_variables_json}") # Log the JSON string

    try:
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            content_sid=content_sid,
            from_=formatted_sender,
            content_variables=content_variables_json,
            to=formatted_recipient
        )

        logger.info(f"Twilio message created successfully. SID: {message.sid}, Status: {message.status}")
        logger.debug(f"Twilio message body: {message.body}") # Log the body as well
        # You might want to check message.status here, though 'created' is typical for sync calls
        # Statuses can be: queued, sending, sent, failed, delivered, undelivered, receiving, received, accepted, scheduled, read, partially_delivered, canceled
        # For this initial send, success means Twilio accepted it (queued/sending).

        # Return both SID and the rendered body
        return {
            "message_sid": message.sid,
            "body": message.body
        }

    except TwilioRestException as e:
        logger.error(f"Twilio API error sending message: {e}")
        logger.error(f"  Status Code: {e.status}")
        logger.error(f"  Code: {e.code}") # Twilio specific error code (e.g., 63016 for failed template send)
        logger.error(f"  Message: {e.msg}")
        # Potentially map common e.code values to more specific log messages or actions
        return None
    except Exception as e:
        # Catch any other unexpected exceptions during client init or API call
        logger.exception(f"Unexpected error sending message via Twilio: {e}")
        return None 