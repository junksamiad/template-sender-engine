"""
Context Object Models for the AI Multi-Communications Engine.

This module defines the structure of the context object created by the Channel Router and
passed to the channel-specific queues for processing. The context object serves as a
comprehensive package containing all necessary information for downstream processing.
"""

from enum import Enum
from typing import Dict, List, Optional, TypedDict, Union, Any
from datetime import datetime
from dataclasses import dataclass, field


class ChannelMethod(str, Enum):
    """
    Supported communication channels.
    """
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"


@dataclass
class CompanyData:
    """Company and project identifiers from the frontend payload."""
    company_id: str
    project_id: str


@dataclass
class RecipientData:
    """Recipient information from the frontend payload."""
    recipient_first_name: str
    recipient_last_name: str
    recipient_tel: Optional[str] = None
    recipient_email: Optional[str] = None
    comms_consent: bool = True


@dataclass
class ProjectData:
    """Project-specific data that varies by use case."""
    job_title: Optional[str] = None
    job_description: Optional[str] = None
    application_deadline: Optional[str] = None
    # Additional fields can be added via **kwargs


@dataclass
class RequestData:
    """Request metadata from the frontend payload."""
    request_id: str
    channel_method: Union[str, ChannelMethod]
    initial_request_timestamp: Union[str, datetime]


@dataclass
class FrontendPayload:
    """The complete frontend payload as received from the frontend application."""
    company_data: CompanyData
    recipient_data: RecipientData
    request_data: RequestData
    project_data: Optional[ProjectData] = None
    custom_data: Optional[Dict[str, Any]] = None


@dataclass
class CompanyRep:
    """Company representative information."""
    company_rep_1: Optional[str] = None
    company_rep_2: Optional[str] = None
    company_rep_3: Optional[str] = None
    company_rep_4: Optional[str] = None
    company_rep_5: Optional[str] = None


@dataclass
class WaCompanyDataPayload:
    """Company and project information retrieved from the DynamoDB database."""
    company_name: str
    project_name: str
    project_status: str = "active"
    allowed_channels: List[str] = field(default_factory=list)
    company_rep: Optional[CompanyRep] = None


@dataclass
class ProjectRateLimits:
    """Rate limiting configuration for the company/project."""
    requests_per_minute: int
    requests_per_day: int
    concurrent_conversations: int
    max_message_length: int


@dataclass
class WhatsAppConfig:
    """WhatsApp channel configuration."""
    whatsapp_credentials_id: str
    company_whatsapp_number: str


@dataclass
class SMSConfig:
    """SMS channel configuration."""
    sms_credentials_id: str
    company_sms_number: str


@dataclass
class EmailConfig:
    """Email channel configuration."""
    email_credentials_id: str
    company_email: str


@dataclass
class ChannelConfig:
    """Channel-specific configuration based on the requested channel method."""
    whatsapp: Optional[WhatsAppConfig] = None
    sms: Optional[SMSConfig] = None
    email: Optional[EmailConfig] = None


@dataclass
class AIConfigContext:
    """AI service configuration for OpenAI."""
    assistant_id_template_sender: str
    assistant_id_replies: str
    ai_api_key_reference: str
    assistant_id_3: Optional[str] = None
    assistant_id_4: Optional[str] = None
    assistant_id_5: Optional[str] = None


@dataclass
class Message:
    """A message in a conversation."""
    entry_id: str
    message_timestamp: Union[str, datetime]
    role: str
    content: str
    ai_prompt_tokens: Optional[int] = None
    ai_completion_tokens: Optional[int] = None
    ai_total_tokens: Optional[int] = None
    processing_time_ms: Optional[int] = None


@dataclass
class ConversationData:
    """Conversation reference data for the conversation record created in DynamoDB."""
    conversation_id: str
    thread_id: Optional[str] = None
    content_variables: Optional[Dict[str, str]] = None
    message: Optional[Message] = None


@dataclass
class Metadata:
    """Metadata about the context object itself."""
    router_version: str
    created_at: Union[str, datetime] = field(default_factory=lambda: datetime.now().isoformat())
    correlation_id: Optional[str] = None
    router_processing_time_ms: Optional[int] = None


@dataclass
class ContextObject:
    """
    The complete context object that serves as a comprehensive package for downstream processing.
    
    This object contains:
    1. The original request payload from the frontend
    2. Company and project configuration from the DynamoDB database
    3. Channel-specific configuration and credentials
    4. AI service configuration and credentials
    5. Metadata for tracking and debugging
    6. Conversation reference data for downstream processing
    """
    frontend_payload: FrontendPayload
    wa_company_data_payload: WaCompanyDataPayload
    project_rate_limits: ProjectRateLimits
    channel_config: ChannelConfig
    ai_config: AIConfigContext
    conversation_data: ConversationData
    metadata: Metadata
    
    def get_channel_method(self) -> ChannelMethod:
        """Get the channel method from the frontend payload."""
        channel = self.frontend_payload.request_data.channel_method
        if isinstance(channel, str):
            return ChannelMethod(channel)
        return channel
    
    def get_active_channel_config(self) -> Union[WhatsAppConfig, SMSConfig, EmailConfig, None]:
        """Get the configuration for the active channel."""
        channel = self.get_channel_method()
        
        if channel == ChannelMethod.WHATSAPP:
            return self.channel_config.whatsapp
        elif channel == ChannelMethod.SMS:
            return self.channel_config.sms
        elif channel == ChannelMethod.EMAIL:
            return self.channel_config.email
        
        return None
    
    def get_credentials_reference(self) -> Optional[str]:
        """Get the credentials reference for the active channel."""
        channel_config = self.get_active_channel_config()
        
        if channel_config is None:
            return None
            
        channel = self.get_channel_method()
        
        if channel == ChannelMethod.WHATSAPP and isinstance(channel_config, WhatsAppConfig):
            return channel_config.whatsapp_credentials_id
        elif channel == ChannelMethod.SMS and isinstance(channel_config, SMSConfig):
            return channel_config.sms_credentials_id
        elif channel == ChannelMethod.EMAIL and isinstance(channel_config, EmailConfig):
            return channel_config.email_credentials_id
            
        return None 