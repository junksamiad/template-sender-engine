"""
Context Object Builder for the Channel Router.

This module creates a minimal context object that combines the frontend payload
and company data for downstream processing, avoiding any assumptions about data structure.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

# Initialize logger
logger = logging.getLogger()

def build_context_object(
    frontend_payload_dict: Dict[str, Any], 
    company_data_dict: Dict[str, Any],
    router_version: str
) -> Dict[str, Any]:
    """
    Create a context object from the frontend payload and company data.
    
    This function combines the frontend payload and company data into a single
    context object with minimal transformation, adding only necessary metadata
    and conversation tracking information.
    
    Args:
        frontend_payload_dict: The validated frontend payload
        company_data_dict: Company configuration from DynamoDB
        router_version: Version string from environment variable
        
    Returns:
        A context object dictionary
    """
    logger.info("Building context object")
    
    # Generate the conversation data dictionary
    conversation_data_dict = generate_conversation_data_dict(frontend_payload_dict, company_data_dict)
    
    # Create minimal context object
    context_object = {
        'frontend_payload': frontend_payload_dict,
        'company_data_payload': company_data_dict,
        'conversation_data': conversation_data_dict,
        'metadata': {
            'router_version': router_version
        }
    }
    
    logger.debug(f"Context object created with conversation_id: {conversation_data_dict['conversation_id']}")
    return context_object

def generate_conversation_data_dict(
    frontend_payload_dict: Dict[str, Any],
    company_data_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a simple conversation data dictionary with just the essential tracking fields.
    
    Args:
        frontend_payload_dict: The complete frontend payload
        company_data_dict: Company configuration from DynamoDB
        
    Returns:
        A minimal conversation data dictionary with conversation_id and status
    """
    # Generate conversation ID
    conversation_id = create_conversation_id(frontend_payload_dict, company_data_dict)
    
    # Create a simple conversation data dictionary with just the essentials
    conversation_data_dict = {
        'conversation_id': conversation_id,
        'conversation_status': 'initiated'  # Initial status
    }
    
    logger.info(f"Generated conversation data with ID: {conversation_id}")
    return conversation_data_dict

def create_conversation_id(
    frontend_payload_dict: Dict[str, Any],
    company_data_dict: Dict[str, Any]
) -> str:
    """
    Create a unique conversation ID based on the channel type.
    
    Format: company_id#project_id#request_id#channel_specific_component
    
    Args:
        frontend_payload_dict: The complete frontend payload
        company_data_dict: Company configuration from DynamoDB
        
    Returns:
        A formatted conversation ID string
    """
    # Extract required information from the frontend payload
    channel_method = frontend_payload_dict.get('request_data', {}).get('channel_method', '').lower()
    company_id = frontend_payload_dict.get('company_data', {}).get('company_id', '')
    project_id = frontend_payload_dict.get('company_data', {}).get('project_id', '')
    request_id = frontend_payload_dict.get('request_data', {}).get('request_id', '')
    
    # Get channel configuration from company data
    channel_config = company_data_dict.get('channel_config', {})
    
    # Base conversation ID components
    base_components = [company_id, project_id, request_id]
    
    # Channel-specific component
    if channel_method == 'whatsapp':
        # For WhatsApp, use the company WhatsApp number
        company_number_raw = channel_config.get('whatsapp', {}).get('company_whatsapp_number', '')
        if not company_number_raw:
            logger.warning(f"WhatsApp number not found in config for {company_id}/{project_id}")
            company_number = "unknown_whatsapp_number"
        else:
            # Remove leading '+' if present for the conversation ID
            company_number = company_number_raw.lstrip('+')
        base_components.append(company_number)
        
    elif channel_method == 'sms':
        # For SMS, use the company SMS number
        company_number_raw = channel_config.get('sms', {}).get('company_sms_number', '')
        if not company_number_raw:
            logger.warning(f"SMS number not found in config for {company_id}/{project_id}")
            company_number = "unknown_sms_number"
        else:
            # Remove leading '+' if present for the conversation ID
            company_number = company_number_raw.lstrip('+')
        base_components.append(company_number)
        
    elif channel_method == 'email':
        # For email, use the company email address
        company_email = channel_config.get('email', {}).get('company_email', '')
        if not company_email:
            logger.warning(f"Company email not found in config for {company_id}/{project_id}")
            # Use a generic placeholder consistent with other channels
            company_email = "unknown_company_email"
        base_components.append(company_email)
    
    else:
        # For any other channel, just use the channel name
        logger.warning(f"Unknown channel method: {channel_method}")
        base_components.append(channel_method)
    
    # Join all components with '#'
    conversation_id = "#".join(base_components)
    logger.debug(f"Created conversation ID: {conversation_id}")
    
    return conversation_id
