"""
Validation utilities for the Context Object.

This module provides functions for validating Context Objects to ensure they
contain all required fields and that the data is in the correct format.
"""

import re
from typing import List, Optional, Dict, Any, Union
import uuid
from datetime import datetime

from src.shared.context.models import (
    ContextObject,
    ChannelMethod,
    FrontendPayload,
    CompanyData,
    RecipientData,
    ProjectData,
    RequestData,
    WaCompanyDataPayload,
    ProjectRateLimits,
    ChannelConfig,
    AIConfigContext,
    ConversationData,
    Metadata
)
from src.shared.secrets.reference import SecretReference


def _is_valid_iso_date(date_str: str) -> bool:
    """
    Check if a string is a valid ISO format date.
    
    Args:
        date_str: The date string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError):
        return False


def _is_valid_uuid(uuid_str: str) -> bool:
    """
    Check if a string is a valid UUID.
    
    Args:
        uuid_str: The UUID string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        uuid_obj = uuid.UUID(uuid_str)
        return str(uuid_obj) == uuid_str
    except (ValueError, TypeError, AttributeError):
        return False


def _is_valid_phone_number(phone_number: str) -> bool:
    """
    Check if a string is a valid phone number in E.164 format.
    
    Args:
        phone_number: The phone number to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not phone_number or not isinstance(phone_number, str):
        return False
    
    # E.164 format: + followed by 1-15 digits
    return bool(re.match(r'^\+[1-9]\d{1,14}$', phone_number))


def _is_valid_email(email: str) -> bool:
    """
    Check if a string is a valid email address.
    
    Args:
        email: The email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # Simple email regex for basic validation
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def validate_company_data(company_data: CompanyData) -> List[str]:
    """
    Validate company data.
    
    Args:
        company_data: The CompanyData object to validate
        
    Returns:
        List of validation error messages, empty if valid
    """
    errors = []
    
    if not company_data.company_id:
        errors.append("company_id is required")
    
    if not company_data.project_id:
        errors.append("project_id is required")
    
    return errors


def validate_recipient_data(recipient_data: RecipientData) -> List[str]:
    """
    Validate recipient data.
    
    Args:
        recipient_data: The RecipientData object to validate
        
    Returns:
        List of validation error messages, empty if valid
    """
    errors = []
    
    if not recipient_data.recipient_first_name:
        errors.append("recipient_first_name is required")
    
    if not recipient_data.recipient_last_name:
        errors.append("recipient_last_name is required")
    
    # Check that at least one contact method is provided
    if not recipient_data.recipient_tel and not recipient_data.recipient_email:
        errors.append("At least one of recipient_tel or recipient_email must be provided")
    
    # Validate phone number format if provided
    if recipient_data.recipient_tel and not _is_valid_phone_number(recipient_data.recipient_tel):
        errors.append("recipient_tel must be in E.164 format (e.g., +447700900123)")
    
    # Validate email format if provided
    if recipient_data.recipient_email and not _is_valid_email(recipient_data.recipient_email):
        errors.append("recipient_email must be a valid email address")
    
    return errors


def validate_request_data(request_data: RequestData) -> List[str]:
    """
    Validate request data.
    
    Args:
        request_data: The RequestData object to validate
        
    Returns:
        List of validation error messages, empty if valid
    """
    errors = []
    
    if not request_data.request_id:
        errors.append("request_id is required")
    else:
        if not _is_valid_uuid(request_data.request_id):
            errors.append("request_id must be a valid UUID")
    
    # Validate channel method
    if not request_data.channel_method:
        errors.append("channel_method is required")
    else:
        try:
            if isinstance(request_data.channel_method, str):
                ChannelMethod(request_data.channel_method)
        except ValueError:
            errors.append(f"channel_method must be one of: {', '.join(c.value for c in ChannelMethod)}")
    
    # Validate timestamp
    if not request_data.initial_request_timestamp:
        errors.append("initial_request_timestamp is required")
    else:
        if isinstance(request_data.initial_request_timestamp, str):
            if not _is_valid_iso_date(request_data.initial_request_timestamp):
                errors.append("initial_request_timestamp must be a valid ISO date string")
    
    return errors


def validate_frontend_payload(frontend_payload: FrontendPayload) -> List[str]:
    """
    Validate frontend payload.
    
    Args:
        frontend_payload: The FrontendPayload object to validate
        
    Returns:
        List of validation error messages, empty if valid
    """
    errors = []
    
    # Validate company data
    company_errors = validate_company_data(frontend_payload.company_data)
    if company_errors:
        errors.extend([f"company_data.{error}" for error in company_errors])
    
    # Validate recipient data
    recipient_errors = validate_recipient_data(frontend_payload.recipient_data)
    if recipient_errors:
        errors.extend([f"recipient_data.{error}" for error in recipient_errors])
    
    # Validate request data
    request_errors = validate_request_data(frontend_payload.request_data)
    if request_errors:
        errors.extend([f"request_data.{error}" for error in request_errors])
    
    return errors


def validate_wa_company_data_payload(payload: WaCompanyDataPayload) -> List[str]:
    """
    Validate WA company data payload.
    
    Args:
        payload: The WaCompanyDataPayload object to validate
        
    Returns:
        List of validation error messages, empty if valid
    """
    errors = []
    
    if not payload.company_name:
        errors.append("company_name is required")
    
    if not payload.project_name:
        errors.append("project_name is required")
    
    if not payload.project_status:
        errors.append("project_status is required")
    
    # Validate allowed channels
    if not payload.allowed_channels:
        errors.append("allowed_channels is required (at least one channel must be allowed)")
    else:
        for channel in payload.allowed_channels:
            try:
                ChannelMethod(channel)
            except ValueError:
                errors.append(f"allowed_channels contains invalid channel: {channel}")
    
    return errors


def validate_project_rate_limits(rate_limits: ProjectRateLimits) -> List[str]:
    """
    Validate project rate limits.
    
    Args:
        rate_limits: The ProjectRateLimits object to validate
        
    Returns:
        List of validation error messages, empty if valid
    """
    errors = []
    
    if rate_limits.requests_per_minute <= 0:
        errors.append("requests_per_minute must be greater than 0")
    
    if rate_limits.requests_per_day <= 0:
        errors.append("requests_per_day must be greater than 0")
    
    if rate_limits.concurrent_conversations <= 0:
        errors.append("concurrent_conversations must be greater than 0")
    
    if rate_limits.max_message_length <= 0:
        errors.append("max_message_length must be greater than 0")
    
    return errors


def validate_channel_config(channel_config: ChannelConfig, channel_method: ChannelMethod) -> List[str]:
    """
    Validate channel configuration.
    
    Args:
        channel_config: The ChannelConfig object to validate
        channel_method: The active channel method
        
    Returns:
        List of validation error messages, empty if valid
    """
    errors = []
    
    # Channel-specific validations
    if channel_method == ChannelMethod.WHATSAPP:
        if not channel_config.whatsapp:
            errors.append("whatsapp configuration is required for WhatsApp channel")
        else:
            if not channel_config.whatsapp.whatsapp_credentials_id:
                errors.append("whatsapp.whatsapp_credentials_id is required")
            elif not SecretReference.is_valid_reference(channel_config.whatsapp.whatsapp_credentials_id):
                errors.append("whatsapp.whatsapp_credentials_id must be a valid secret reference")
                
            if not channel_config.whatsapp.company_whatsapp_number:
                errors.append("whatsapp.company_whatsapp_number is required")
            elif not _is_valid_phone_number(channel_config.whatsapp.company_whatsapp_number):
                errors.append("whatsapp.company_whatsapp_number must be in E.164 format")
    
    elif channel_method == ChannelMethod.SMS:
        if not channel_config.sms:
            errors.append("sms configuration is required for SMS channel")
        else:
            if not channel_config.sms.sms_credentials_id:
                errors.append("sms.sms_credentials_id is required")
            elif not SecretReference.is_valid_reference(channel_config.sms.sms_credentials_id):
                errors.append("sms.sms_credentials_id must be a valid secret reference")
                
            if not channel_config.sms.company_sms_number:
                errors.append("sms.company_sms_number is required")
            elif not _is_valid_phone_number(channel_config.sms.company_sms_number):
                errors.append("sms.company_sms_number must be in E.164 format")
    
    elif channel_method == ChannelMethod.EMAIL:
        if not channel_config.email:
            errors.append("email configuration is required for Email channel")
        else:
            if not channel_config.email.email_credentials_id:
                errors.append("email.email_credentials_id is required")
            elif not SecretReference.is_valid_reference(channel_config.email.email_credentials_id):
                errors.append("email.email_credentials_id must be a valid secret reference")
                
            if not channel_config.email.company_email:
                errors.append("email.company_email is required")
            elif not _is_valid_email(channel_config.email.company_email):
                errors.append("email.company_email must be a valid email address")
    
    return errors


def validate_ai_config(ai_config: AIConfigContext) -> List[str]:
    """
    Validate AI configuration.
    
    Args:
        ai_config: The AIConfigContext object to validate
        
    Returns:
        List of validation error messages, empty if valid
    """
    errors = []
    
    if not ai_config.assistant_id_template_sender:
        errors.append("assistant_id_template_sender is required")
    
    if not ai_config.assistant_id_replies:
        errors.append("assistant_id_replies is required")
    
    if not ai_config.ai_api_key_reference:
        errors.append("ai_api_key_reference is required")
    elif not SecretReference.is_valid_reference(ai_config.ai_api_key_reference):
        errors.append("ai_api_key_reference must be a valid secret reference")
    
    return errors


def validate_conversation_data(conversation_data: ConversationData) -> List[str]:
    """
    Validate conversation data.
    
    Args:
        conversation_data: The ConversationData object to validate
        
    Returns:
        List of validation error messages, empty if valid
    """
    errors = []
    
    if not conversation_data.conversation_id:
        errors.append("conversation_id is required")
    
    return errors


def validate_metadata(metadata: Metadata) -> List[str]:
    """
    Validate metadata.
    
    Args:
        metadata: The Metadata object to validate
        
    Returns:
        List of validation error messages, empty if valid
    """
    errors = []
    
    if not metadata.router_version:
        errors.append("router_version is required")
    
    # Validate created_at timestamp
    if metadata.created_at:
        if isinstance(metadata.created_at, str) and not _is_valid_iso_date(metadata.created_at):
            errors.append("created_at must be a valid ISO date string")
    
    # Validate correlation_id if present
    if metadata.correlation_id:
        if not _is_valid_uuid(metadata.correlation_id):
            errors.append("correlation_id must be a valid UUID")
    
    return errors


def validate_context(context: ContextObject) -> List[str]:
    """
    Validate the entire context object.
    
    Args:
        context: The ContextObject to validate
        
    Returns:
        List of validation error messages, empty if valid
    """
    errors = []
    
    # Get the active channel method
    try:
        channel_method = context.get_channel_method()
    except ValueError as e:
        errors.append(f"Invalid channel_method: {str(e)}")
        # Default to WhatsApp for further validation if channel method is invalid
        channel_method = ChannelMethod.WHATSAPP
    
    # Validate frontend payload
    frontend_errors = validate_frontend_payload(context.frontend_payload)
    if frontend_errors:
        errors.extend(frontend_errors)
    
    # Validate WA company data payload
    wa_company_errors = validate_wa_company_data_payload(context.wa_company_data_payload)
    if wa_company_errors:
        errors.extend([f"wa_company_data_payload.{error}" for error in wa_company_errors])
    
    # Validate project rate limits
    rate_limit_errors = validate_project_rate_limits(context.project_rate_limits)
    if rate_limit_errors:
        errors.extend([f"project_rate_limits.{error}" for error in rate_limit_errors])
    
    # Validate channel config
    channel_config_errors = validate_channel_config(context.channel_config, channel_method)
    if channel_config_errors:
        errors.extend([f"channel_config.{error}" for error in channel_config_errors])
    
    # Validate AI config
    ai_config_errors = validate_ai_config(context.ai_config)
    if ai_config_errors:
        errors.extend([f"ai_config.{error}" for error in ai_config_errors])
    
    # Validate conversation data
    conversation_errors = validate_conversation_data(context.conversation_data)
    if conversation_errors:
        errors.extend([f"conversation_data.{error}" for error in conversation_errors])
    
    # Validate metadata
    metadata_errors = validate_metadata(context.metadata)
    if metadata_errors:
        errors.extend([f"metadata.{error}" for error in metadata_errors])
    
    return errors 