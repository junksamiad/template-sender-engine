"""
Serialization utilities for the Context Object.

This module provides functions for serializing and deserializing Context Objects
to and from JSON for storage or transmission.
"""

import json
from typing import Dict, Any, Optional, Union, cast
from datetime import datetime
from dataclasses import asdict

from src.shared.context.models import (
    ContextObject,
    FrontendPayload,
    CompanyData,
    RecipientData,
    ProjectData,
    RequestData,
    WaCompanyDataPayload,
    ProjectRateLimits,
    ChannelConfig,
    WhatsAppConfig,
    SMSConfig,
    EmailConfig,
    AIConfigContext,
    ConversationData,
    Metadata,
    Message,
    CompanyRep,
    ChannelMethod
)


def _serialize_datetime(obj: Any) -> Any:
    """
    Convert datetime objects to ISO format strings.
    
    Args:
        obj: The object to serialize
        
    Returns:
        Serialized object with datetime converted to strings
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def serialize_context(context: ContextObject) -> str:
    """
    Serialize a ContextObject to a JSON string.
    
    Args:
        context: The ContextObject to serialize
        
    Returns:
        JSON string representation of the ContextObject
    """
    # Convert to dict using dataclasses.asdict
    context_dict = asdict(context)
    
    # Serialize to JSON with custom handling for datetime objects
    return json.dumps(context_dict, default=_serialize_datetime)


def _dict_to_company_data(data: Dict[str, Any]) -> CompanyData:
    """Convert dictionary to CompanyData object."""
    return CompanyData(
        company_id=data.get('company_id', ''),
        project_id=data.get('project_id', '')
    )


def _dict_to_recipient_data(data: Dict[str, Any]) -> RecipientData:
    """Convert dictionary to RecipientData object."""
    return RecipientData(
        recipient_first_name=data.get('recipient_first_name', ''),
        recipient_last_name=data.get('recipient_last_name', ''),
        recipient_tel=data.get('recipient_tel'),
        recipient_email=data.get('recipient_email'),
        comms_consent=data.get('comms_consent', True)
    )


def _dict_to_project_data(data: Optional[Dict[str, Any]]) -> Optional[ProjectData]:
    """Convert dictionary to ProjectData object."""
    if not data:
        return None
        
    return ProjectData(
        job_title=data.get('job_title'),
        job_description=data.get('job_description'),
        application_deadline=data.get('application_deadline')
    )


def _dict_to_request_data(data: Dict[str, Any]) -> RequestData:
    """Convert dictionary to RequestData object."""
    return RequestData(
        request_id=data.get('request_id', ''),
        channel_method=data.get('channel_method', ''),
        initial_request_timestamp=data.get('initial_request_timestamp', '')
    )


def _dict_to_frontend_payload(data: Dict[str, Any]) -> FrontendPayload:
    """Convert dictionary to FrontendPayload object."""
    return FrontendPayload(
        company_data=_dict_to_company_data(data.get('company_data', {})),
        recipient_data=_dict_to_recipient_data(data.get('recipient_data', {})),
        request_data=_dict_to_request_data(data.get('request_data', {})),
        project_data=_dict_to_project_data(data.get('project_data')),
        custom_data=data.get('custom_data')
    )


def _dict_to_company_rep(data: Optional[Dict[str, Any]]) -> Optional[CompanyRep]:
    """Convert dictionary to CompanyRep object."""
    if not data:
        return None
        
    return CompanyRep(
        company_rep_1=data.get('company_rep_1'),
        company_rep_2=data.get('company_rep_2'),
        company_rep_3=data.get('company_rep_3'),
        company_rep_4=data.get('company_rep_4'),
        company_rep_5=data.get('company_rep_5')
    )


def _dict_to_wa_company_data_payload(data: Dict[str, Any]) -> WaCompanyDataPayload:
    """Convert dictionary to WaCompanyDataPayload object."""
    return WaCompanyDataPayload(
        company_name=data.get('company_name', ''),
        project_name=data.get('project_name', ''),
        project_status=data.get('project_status', 'active'),
        allowed_channels=data.get('allowed_channels', []),
        company_rep=_dict_to_company_rep(data.get('company_rep'))
    )


def _dict_to_project_rate_limits(data: Dict[str, Any]) -> ProjectRateLimits:
    """Convert dictionary to ProjectRateLimits object."""
    return ProjectRateLimits(
        requests_per_minute=data.get('requests_per_minute', 0),
        requests_per_day=data.get('requests_per_day', 0),
        concurrent_conversations=data.get('concurrent_conversations', 0),
        max_message_length=data.get('max_message_length', 0)
    )


def _dict_to_whatsapp_config(data: Optional[Dict[str, Any]]) -> Optional[WhatsAppConfig]:
    """Convert dictionary to WhatsAppConfig object."""
    if not data:
        return None
        
    return WhatsAppConfig(
        whatsapp_credentials_id=data.get('whatsapp_credentials_id', ''),
        company_whatsapp_number=data.get('company_whatsapp_number', '')
    )


def _dict_to_sms_config(data: Optional[Dict[str, Any]]) -> Optional[SMSConfig]:
    """Convert dictionary to SMSConfig object."""
    if not data:
        return None
        
    return SMSConfig(
        sms_credentials_id=data.get('sms_credentials_id', ''),
        company_sms_number=data.get('company_sms_number', '')
    )


def _dict_to_email_config(data: Optional[Dict[str, Any]]) -> Optional[EmailConfig]:
    """Convert dictionary to EmailConfig object."""
    if not data:
        return None
        
    return EmailConfig(
        email_credentials_id=data.get('email_credentials_id', ''),
        company_email=data.get('company_email', '')
    )


def _dict_to_channel_config(data: Dict[str, Any]) -> ChannelConfig:
    """Convert dictionary to ChannelConfig object."""
    return ChannelConfig(
        whatsapp=_dict_to_whatsapp_config(data.get('whatsapp')),
        sms=_dict_to_sms_config(data.get('sms')),
        email=_dict_to_email_config(data.get('email'))
    )


def _dict_to_ai_config(data: Dict[str, Any]) -> AIConfigContext:
    """Convert dictionary to AIConfigContext object."""
    return AIConfigContext(
        assistant_id_template_sender=data.get('assistant_id_template_sender', ''),
        assistant_id_replies=data.get('assistant_id_replies', ''),
        ai_api_key_reference=data.get('ai_api_key_reference', ''),
        assistant_id_3=data.get('assistant_id_3'),
        assistant_id_4=data.get('assistant_id_4'),
        assistant_id_5=data.get('assistant_id_5')
    )


def _dict_to_message(data: Optional[Dict[str, Any]]) -> Optional[Message]:
    """Convert dictionary to Message object."""
    if not data:
        return None
        
    return Message(
        entry_id=data.get('entry_id', ''),
        message_timestamp=data.get('message_timestamp', ''),
        role=data.get('role', ''),
        content=data.get('content', ''),
        ai_prompt_tokens=data.get('ai_prompt_tokens'),
        ai_completion_tokens=data.get('ai_completion_tokens'),
        ai_total_tokens=data.get('ai_total_tokens'),
        processing_time_ms=data.get('processing_time_ms')
    )


def _dict_to_conversation_data(data: Dict[str, Any]) -> ConversationData:
    """Convert dictionary to ConversationData object."""
    return ConversationData(
        conversation_id=data.get('conversation_id', ''),
        thread_id=data.get('thread_id'),
        content_variables=data.get('content_variables'),
        message=_dict_to_message(data.get('message'))
    )


def _dict_to_metadata(data: Dict[str, Any]) -> Metadata:
    """Convert dictionary to Metadata object."""
    return Metadata(
        router_version=data.get('router_version', ''),
        created_at=data.get('created_at', datetime.now().isoformat()),
        correlation_id=data.get('correlation_id'),
        router_processing_time_ms=data.get('router_processing_time_ms')
    )


def deserialize_context(json_str: str) -> ContextObject:
    """
    Deserialize a JSON string to a ContextObject.
    
    Args:
        json_str: The JSON string to deserialize
        
    Returns:
        A ContextObject instance
        
    Raises:
        ValueError: If the JSON string is invalid or missing required fields
    """
    try:
        # Parse JSON string to dictionary
        data = json.loads(json_str)
        
        # Convert dictionary to ContextObject
        return ContextObject(
            frontend_payload=_dict_to_frontend_payload(data.get('frontend_payload', {})),
            wa_company_data_payload=_dict_to_wa_company_data_payload(data.get('wa_company_data_payload', {})),
            project_rate_limits=_dict_to_project_rate_limits(data.get('project_rate_limits', {})),
            channel_config=_dict_to_channel_config(data.get('channel_config', {})),
            ai_config=_dict_to_ai_config(data.get('ai_config', {})),
            conversation_data=_dict_to_conversation_data(data.get('conversation_data', {})),
            metadata=_dict_to_metadata(data.get('metadata', {}))
        )
    except Exception as e:
        raise ValueError(f"Failed to deserialize context object: {str(e)}") 