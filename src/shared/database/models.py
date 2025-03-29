"""
Data models for DynamoDB tables in the AI Multi-Communications Engine.

This module provides classes that represent items in the DynamoDB tables,
with methods for validation and conversion between DynamoDB and Python.
"""
import re
import time
from enum import Enum
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, TypeVar, Type, Generic, Set, cast

T = TypeVar('T', bound='BaseModel')


class ChannelMethod(str, Enum):
    """
    Supported communication channels.
    """
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"


class ConversationStatus(str, Enum):
    """
    Status of a conversation.
    """
    PROCESSING = "processing"
    INITIAL_MESSAGE_SENT = "initial_message_sent"
    FAILED = "failed"


class BaseModel:
    """
    Base class for all data models with common functionality.
    """

    @classmethod
    def from_item(cls: Type[T], item: Dict[str, Any]) -> T:
        """
        Create a model instance from a DynamoDB item.
        
        Args:
            item: The DynamoDB item
            
        Returns:
            A model instance
        """
        return cls(**item)
    
    def to_item(self) -> Dict[str, Any]:
        """
        Convert the model to a DynamoDB item.
        
        Returns:
            A DynamoDB item
        """
        # Get all instance attributes that don't start with _
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, Enum):
                    result[key] = value.value
                elif isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, (dict, list)):
                    # Deep copy to avoid reference issues
                    result[key] = _deep_copy_for_dynamo(value)
                else:
                    result[key] = value
        return result
    
    def validate(self) -> List[str]:
        """
        Validate the model.
        
        Returns:
            A list of validation error messages, empty if valid
        """
        errors = []
        
        # Implement validation logic in subclasses
        
        return errors


class AIConfig:
    """
    AI configuration for a conversation.
    """
    
    def __init__(
        self,
        assistant_id_template_sender: str,
        assistant_id_replies: str,
        ai_api_key_reference: str,
        assistant_id_3: Optional[str] = None,
        assistant_id_4: Optional[str] = None,
        assistant_id_5: Optional[str] = None,
    ):
        """
        Initialize an AI configuration.
        
        Args:
            assistant_id_template_sender: The OpenAI assistant ID for sending templates
            assistant_id_replies: The OpenAI assistant ID for handling replies
            ai_api_key_reference: Reference to the AI API key in Secrets Manager
            assistant_id_3: Optional 3rd assistant ID
            assistant_id_4: Optional 4th assistant ID
            assistant_id_5: Optional 5th assistant ID
        """
        self.assistant_id_template_sender = assistant_id_template_sender
        self.assistant_id_replies = assistant_id_replies
        self.ai_api_key_reference = ai_api_key_reference
        self.assistant_id_3 = assistant_id_3
        self.assistant_id_4 = assistant_id_4
        self.assistant_id_5 = assistant_id_5
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIConfig':
        """
        Create an AIConfig from a dictionary.
        
        Args:
            data: The dictionary
            
        Returns:
            An AIConfig instance
        """
        return cls(
            assistant_id_template_sender=data.get('assistant_id_template_sender', ''),
            assistant_id_replies=data.get('assistant_id_replies', ''),
            ai_api_key_reference=data.get('ai_api_key_reference', ''),
            assistant_id_3=data.get('assistant_id_3'),
            assistant_id_4=data.get('assistant_id_4'),
            assistant_id_5=data.get('assistant_id_5'),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the AIConfig to a dictionary.
        
        Returns:
            A dictionary
        """
        result = {
            'assistant_id_template_sender': self.assistant_id_template_sender,
            'assistant_id_replies': self.assistant_id_replies,
            'ai_api_key_reference': self.ai_api_key_reference,
        }
        
        if self.assistant_id_3:
            result['assistant_id_3'] = self.assistant_id_3
            
        if self.assistant_id_4:
            result['assistant_id_4'] = self.assistant_id_4
            
        if self.assistant_id_5:
            result['assistant_id_5'] = self.assistant_id_5
            
        return result


class CompanyRep:
    """
    Company representative information.
    """
    
    def __init__(
        self,
        company_rep_1: Optional[str] = None,
        company_rep_2: Optional[str] = None,
        company_rep_3: Optional[str] = None,
        company_rep_4: Optional[str] = None,
        company_rep_5: Optional[str] = None,
    ):
        """
        Initialize company representative information.
        
        Args:
            company_rep_1: First company representative
            company_rep_2: Second company representative
            company_rep_3: Third company representative
            company_rep_4: Fourth company representative
            company_rep_5: Fifth company representative
        """
        self.company_rep_1 = company_rep_1
        self.company_rep_2 = company_rep_2
        self.company_rep_3 = company_rep_3
        self.company_rep_4 = company_rep_4
        self.company_rep_5 = company_rep_5
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompanyRep':
        """
        Create a CompanyRep from a dictionary.
        
        Args:
            data: The dictionary
            
        Returns:
            A CompanyRep instance
        """
        if not data:
            return cls()
            
        return cls(
            company_rep_1=data.get('company_rep_1'),
            company_rep_2=data.get('company_rep_2'),
            company_rep_3=data.get('company_rep_3'),
            company_rep_4=data.get('company_rep_4'),
            company_rep_5=data.get('company_rep_5'),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the CompanyRep to a dictionary.
        
        Returns:
            A dictionary
        """
        result = {}
        
        if self.company_rep_1:
            result['company_rep_1'] = self.company_rep_1
            
        if self.company_rep_2:
            result['company_rep_2'] = self.company_rep_2
            
        if self.company_rep_3:
            result['company_rep_3'] = self.company_rep_3
            
        if self.company_rep_4:
            result['company_rep_4'] = self.company_rep_4
            
        if self.company_rep_5:
            result['company_rep_5'] = self.company_rep_5
            
        return result


class Message:
    """
    A message in a conversation.
    """
    
    def __init__(
        self,
        entry_id: str,
        role: str,
        content: str,
        message_timestamp: Union[str, datetime],
        ai_prompt_tokens: Optional[int] = None,
        ai_completion_tokens: Optional[int] = None,
        ai_total_tokens: Optional[int] = None,
        processing_time_ms: Optional[int] = None,
    ):
        """
        Initialize a message.
        
        Args:
            entry_id: Unique identifier for the message
            role: The role of the message sender ("user" or "assistant")
            content: The message content
            message_timestamp: When the message was sent or received
            ai_prompt_tokens: Number of prompt tokens used
            ai_completion_tokens: Number of completion tokens used
            ai_total_tokens: Total number of tokens used
            processing_time_ms: Processing time in milliseconds
        """
        self.entry_id = entry_id
        self.role = role
        self.content = content
        
        # Handle message timestamp
        if isinstance(message_timestamp, str):
            # Parse ISO format string to datetime
            try:
                self.message_timestamp = datetime.fromisoformat(message_timestamp.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                self.message_timestamp = datetime.now(timezone.utc)
        elif isinstance(message_timestamp, datetime):
            self.message_timestamp = message_timestamp
        else:
            self.message_timestamp = datetime.now(timezone.utc)
            
        self.ai_prompt_tokens = ai_prompt_tokens
        self.ai_completion_tokens = ai_completion_tokens
        
        # Calculate total tokens if not provided
        if ai_total_tokens is None and ai_prompt_tokens is not None and ai_completion_tokens is not None:
            self.ai_total_tokens = ai_prompt_tokens + ai_completion_tokens
        else:
            self.ai_total_tokens = ai_total_tokens
            
        self.processing_time_ms = processing_time_ms
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """
        Create a Message from a dictionary.
        
        Args:
            data: The dictionary
            
        Returns:
            A Message instance
        """
        return cls(
            entry_id=data.get('entry_id', ''),
            role=data.get('role', ''),
            content=data.get('content', ''),
            message_timestamp=data.get('message_timestamp', datetime.now(timezone.utc)),
            ai_prompt_tokens=data.get('ai_prompt_tokens'),
            ai_completion_tokens=data.get('ai_completion_tokens'),
            ai_total_tokens=data.get('ai_total_tokens'),
            processing_time_ms=data.get('processing_time_ms'),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Message to a dictionary.
        
        Returns:
            A dictionary
        """
        result = {
            'entry_id': self.entry_id,
            'role': self.role,
            'content': self.content,
            'message_timestamp': self.message_timestamp.isoformat(),
        }
        
        if self.ai_prompt_tokens is not None:
            result['ai_prompt_tokens'] = self.ai_prompt_tokens
            
        if self.ai_completion_tokens is not None:
            result['ai_completion_tokens'] = self.ai_completion_tokens
            
        if self.ai_total_tokens is not None:
            result['ai_total_tokens'] = self.ai_total_tokens
            
        if self.processing_time_ms is not None:
            result['processing_time_ms'] = self.processing_time_ms
            
        return result


class WaCompanyData(BaseModel):
    """
    Model for the wa_company_data table.
    """
    
    def __init__(
        self,
        company_id: str,
        project_id: str,
        company_name: str,
        project_name: str,
        project_status: str = "active",
        allowed_channels: Optional[List[str]] = None,
        company_rep: Optional[Union[Dict[str, Any], CompanyRep]] = None,
        rate_limits: Optional[Dict[str, Any]] = None,
        channel_config: Optional[Dict[str, Any]] = None,
        created_at: Optional[Union[str, datetime]] = None,
        updated_at: Optional[Union[str, datetime]] = None,
        **kwargs: Any
    ):
        """
        Initialize a wa_company_data item.
        
        Args:
            company_id: Company identifier
            project_id: Project identifier
            company_name: Human-readable company name
            project_name: Human-readable project name
            project_status: Status of the project
            allowed_channels: List of allowed communication channels
            company_rep: Company representatives information
            rate_limits: Rate limits for the project
            channel_config: Channel-specific configuration
            created_at: When the item was created
            updated_at: When the item was last updated
            **kwargs: Additional attributes
        """
        self.company_id = company_id
        self.project_id = project_id
        self.company_name = company_name
        self.project_name = project_name
        self.project_status = project_status
        self.allowed_channels = allowed_channels or ["whatsapp"]
        
        if company_rep is None:
            self.company_rep = CompanyRep()
        elif isinstance(company_rep, dict):
            self.company_rep = CompanyRep.from_dict(company_rep)
        else:
            self.company_rep = company_rep
            
        self.rate_limits = rate_limits or {
            "requests_per_minute": 60,
            "requests_per_day": 5000,
            "concurrent_conversations": 100,
            "max_message_length": 4000
        }
        
        self.channel_config = channel_config or {}
        
        # Set timestamps
        now = datetime.now(timezone.utc)
        
        # Handle created_at timestamp
        if created_at is None:
            self.created_at = now
        elif isinstance(created_at, str):
            # Parse ISO format string to datetime
            try:
                self.created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                self.created_at = now
        else:
            self.created_at = created_at
            
        # Handle updated_at timestamp
        if updated_at is None:
            self.updated_at = now
        elif isinstance(updated_at, str):
            # Parse ISO format string to datetime
            try:
                self.updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                self.updated_at = now
        else:
            self.updated_at = updated_at
            
        # Add any additional attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_item(self) -> Dict[str, Any]:
        """
        Convert the model to a DynamoDB item.
        
        Returns:
            A DynamoDB item
        """
        result = super().to_item()
        
        # Convert complex types
        result['company_rep'] = self.company_rep.to_dict()
        
        return result
    
    def validate(self) -> List[str]:
        """
        Validate the wa_company_data item.
        
        Returns:
            A list of validation error messages, empty if valid
        """
        errors = super().validate()
        
        # Validate required fields
        required_fields = [
            'company_id', 'project_id', 'company_name', 'project_name',
        ]
        
        for field in required_fields:
            value = getattr(self, field, None)
            if not value:
                errors.append(f"Field '{field}' is required")
        
        # Validate project_status
        valid_statuses = ["active", "inactive", "pending", "archived"]
        if self.project_status not in valid_statuses:
            errors.append(f"Invalid project_status: {self.project_status}. Must be one of {valid_statuses}")
        
        # Validate allowed_channels
        valid_channels = [cm.value for cm in ChannelMethod]
        for channel in self.allowed_channels:
            if channel not in valid_channels:
                errors.append(f"Invalid channel: {channel}. Must be one of {valid_channels}")
        
        # Validate channel_config
        for channel in self.channel_config:
            if channel not in valid_channels:
                errors.append(f"Invalid channel in channel_config: {channel}. Must be one of {valid_channels}")
        
        return errors


class Conversation(BaseModel):
    """
    Model for the conversations table.
    """
    
    def __init__(
        self,
        conversation_id: str,
        company_id: str,
        project_id: str,
        company_name: str,
        project_name: str,
        channel_method: Union[str, ChannelMethod],
        request_id: str,
        router_version: str,
        conversation_status: Union[str, ConversationStatus] = ConversationStatus.PROCESSING,
        recipient_tel: Optional[str] = None,
        recipient_email: Optional[str] = None,
        company_rep: Optional[Union[Dict[str, Any], CompanyRep]] = None,
        company_whatsapp_number: Optional[str] = None,
        company_sms_number: Optional[str] = None,
        company_email: Optional[str] = None,
        message_id: Optional[str] = None,
        whatsapp_credentials_reference: Optional[str] = None,
        sms_credentials_reference: Optional[str] = None,
        email_credentials_reference: Optional[str] = None,
        recipient_first_name: Optional[str] = None,
        recipient_last_name: Optional[str] = None,
        thread_id: Optional[str] = None,
        messages: Optional[List[Union[Dict[str, Any], Message]]] = None,
        processing_time_ms: Optional[int] = None,
        task_complete: bool = False,
        comms_consent: bool = False,
        project_data: Optional[Dict[str, Any]] = None,
        ai_config: Optional[Union[Dict[str, Any], AIConfig]] = None,
        ttl: Optional[int] = None,
        created_at: Optional[Union[str, datetime]] = None,
        updated_at: Optional[Union[str, datetime]] = None,
        **kwargs: Any
    ):
        """
        Initialize a conversation item.
        
        Args:
            conversation_id: Unique conversation identifier
            company_id: Company identifier
            project_id: Project identifier
            company_name: Human-readable company name
            project_name: Human-readable project name
            channel_method: Communication channel
            request_id: Request identifier
            router_version: Router version
            conversation_status: Status of the conversation
            recipient_tel: Recipient telephone number
            recipient_email: Recipient email address
            company_rep: Company representatives information
            company_whatsapp_number: Company WhatsApp number
            company_sms_number: Company SMS number
            company_email: Company email address
            message_id: External message identifier
            whatsapp_credentials_reference: Reference to WhatsApp credentials
            sms_credentials_reference: Reference to SMS credentials
            email_credentials_reference: Reference to email credentials
            recipient_first_name: Recipient's first name
            recipient_last_name: Recipient's last name
            thread_id: External thread identifier
            messages: List of messages in the conversation
            processing_time_ms: Processing time in milliseconds
            task_complete: Whether the task is complete
            comms_consent: Whether consent has been given for communications
            project_data: Project-specific data
            ai_config: AI configuration
            ttl: Time to live (expiration) for the item
            created_at: When the item was created
            updated_at: When the item was last updated
            **kwargs: Additional attributes
        """
        self.conversation_id = conversation_id
        self.company_id = company_id
        self.project_id = project_id
        self.company_name = company_name
        self.project_name = project_name
        
        # Handle channel_method
        if isinstance(channel_method, str):
            try:
                self.channel_method = ChannelMethod(channel_method)
            except ValueError:
                self.channel_method = ChannelMethod.WHATSAPP
        else:
            self.channel_method = channel_method
            
        self.request_id = request_id
        self.router_version = router_version
        
        # Handle conversation_status
        if isinstance(conversation_status, str):
            try:
                self.conversation_status = ConversationStatus(conversation_status)
            except ValueError:
                self.conversation_status = ConversationStatus.PROCESSING
        else:
            self.conversation_status = conversation_status
            
        self.recipient_tel = recipient_tel
        self.recipient_email = recipient_email
        
        # Handle company_rep
        if company_rep is None:
            self.company_rep = CompanyRep()
        elif isinstance(company_rep, dict):
            self.company_rep = CompanyRep.from_dict(company_rep)
        else:
            self.company_rep = company_rep
            
        self.company_whatsapp_number = company_whatsapp_number
        self.company_sms_number = company_sms_number
        self.company_email = company_email
        self.message_id = message_id
        self.whatsapp_credentials_reference = whatsapp_credentials_reference
        self.sms_credentials_reference = sms_credentials_reference
        self.email_credentials_reference = email_credentials_reference
        self.recipient_first_name = recipient_first_name
        self.recipient_last_name = recipient_last_name
        self.thread_id = thread_id
        self.processing_time_ms = processing_time_ms
        self.task_complete = task_complete
        self.comms_consent = comms_consent
        self.project_data = project_data or {}
        
        # Handle AI configuration
        if ai_config is None:
            self.ai_config = None
        elif isinstance(ai_config, dict):
            self.ai_config = AIConfig.from_dict(ai_config)
        else:
            self.ai_config = ai_config
            
        self.ttl = ttl
        
        # Handle messages
        self.messages = []
        if messages:
            for message in messages:
                if isinstance(message, dict):
                    self.messages.append(Message.from_dict(message))
                else:
                    self.messages.append(message)
        
        # Set timestamps
        now = datetime.now(timezone.utc)
        
        # Handle created_at timestamp
        if created_at is None:
            self.created_at = now
        elif isinstance(created_at, str):
            # Parse ISO format string to datetime
            try:
                self.created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                self.created_at = now
        else:
            self.created_at = created_at
            
        # Handle updated_at timestamp
        if updated_at is None:
            self.updated_at = now
        elif isinstance(updated_at, str):
            # Parse ISO format string to datetime
            try:
                self.updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                self.updated_at = now
        else:
            self.updated_at = updated_at
            
        # Add any additional attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_item(self) -> Dict[str, Any]:
        """
        Convert the model to a DynamoDB item.
        
        Returns:
            A DynamoDB item
        """
        result = super().to_item()
        
        # Convert complex types
        result['company_rep'] = self.company_rep.to_dict()
        
        if self.ai_config:
            result['ai_config'] = self.ai_config.to_dict()
            
        # Convert messages
        if self.messages:
            result['messages'] = [message.to_dict() for message in self.messages]
            
        return result
    
    def validate(self) -> List[str]:
        """
        Validate the conversation item.
        
        Returns:
            A list of validation error messages, empty if valid
        """
        errors = super().validate()
        
        # Validate required fields
        required_fields = [
            'conversation_id', 'company_id', 'project_id', 'request_id',
        ]
        
        for field in required_fields:
            value = getattr(self, field, None)
            if not value:
                errors.append(f"Field '{field}' is required")
        
        # Validate channel-specific fields
        if self.channel_method == ChannelMethod.WHATSAPP and not self.recipient_tel:
            errors.append("recipient_tel is required for WhatsApp channel")
            
        if self.channel_method == ChannelMethod.EMAIL and not self.recipient_email:
            errors.append("recipient_email is required for Email channel")
            
        if self.channel_method == ChannelMethod.SMS and not self.recipient_tel:
            errors.append("recipient_tel is required for SMS channel")
        
        return errors
    
    def add_message(self, message: Union[Dict[str, Any], Message]) -> None:
        """
        Add a message to the conversation.
        
        Args:
            message: The message to add
        """
        if isinstance(message, dict):
            message_obj = Message.from_dict(message)
        else:
            message_obj = message
            
        self.messages.append(message_obj)
        self.updated_at = datetime.now(timezone.utc)
    
    def set_ttl(self, days: int = 90) -> None:
        """
        Set the TTL (time to live) for the conversation.
        
        Args:
            days: Number of days until expiration
        """
        # Calculate TTL as epoch timestamp
        ttl_datetime = datetime.now(timezone.utc).timestamp() + (days * 24 * 60 * 60)
        self.ttl = int(ttl_datetime)


def _deep_copy_for_dynamo(obj: Any) -> Any:
    """
    Deep copy an object for DynamoDB, handling special types.
    
    Args:
        obj: The object to copy
        
    Returns:
        A deep copy of the object suitable for DynamoDB
    """
    if isinstance(obj, dict):
        return {k: _deep_copy_for_dynamo(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_deep_copy_for_dynamo(v) for v in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, Enum):
        return obj.value
    else:
        return obj 