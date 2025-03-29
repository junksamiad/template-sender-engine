"""
Test data fixtures for database testing.

This module provides comprehensive test data fixtures for database testing.
"""
import uuid
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any


def generate_unique_id(prefix: str = "test") -> str:
    """Generate a unique ID for test data."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def generate_phone_number() -> str:
    """Generate a random phone number for testing."""
    return f"+1{random.randint(2000000000, 9999999999)}"


def generate_timestamp(days_ago: int = 0, hours_ago: int = 0) -> str:
    """Generate an ISO timestamp for a time in the past."""
    now = datetime.now(timezone.utc)
    timestamp = now - timedelta(days=days_ago, hours=hours_ago)
    return timestamp.isoformat()


def create_company_data_fixture(
    company_id: str = None,
    project_id: str = None,
    status: str = "active",
    channels: List[str] = None,
) -> Dict[str, Any]:
    """
    Create a company data fixture for testing.
    
    Args:
        company_id: Optional company ID (generated if None)
        project_id: Optional project ID (generated if None)
        status: Project status
        channels: List of allowed channels
        
    Returns:
        A dictionary representing company data
    """
    company_id = company_id or generate_unique_id("company")
    project_id = project_id or generate_unique_id("project")
    channels = channels or ["whatsapp", "email", "sms"]
    
    return {
        "company_id": company_id,
        "project_id": project_id,
        "company_name": f"Test Company {company_id}",
        "project_name": f"Test Project {project_id}",
        "project_status": status,
        "allowed_channels": channels,
        "company_rep": {
            "company_rep_1": "Test Rep 1",
            "company_rep_2": "Test Rep 2",
        },
        "rate_limits": {
            "whatsapp": {
                "max_per_minute": 60,
                "max_per_hour": 1000,
            },
            "email": {
                "max_per_minute": 30,
                "max_per_hour": 500,
            },
            "sms": {
                "max_per_minute": 20,
                "max_per_hour": 300,
            }
        },
        "channel_config": {
            "whatsapp": {
                "template_ids": ["template-1", "template-2", "template-3"],
                "credentials_reference": f"secret/whatsapp/{company_id}",
            },
            "email": {
                "template_ids": ["email-template-1", "email-template-2"],
                "credentials_reference": f"secret/email/{company_id}",
                "from_address": f"noreply@{company_id.lower()}.example.com",
            },
            "sms": {
                "template_ids": ["sms-template-1"],
                "credentials_reference": f"secret/sms/{company_id}",
                "from_number": generate_phone_number(),
            }
        },
        "created_at": generate_timestamp(days_ago=30),
        "updated_at": generate_timestamp(days_ago=1),
    }


def create_conversation_data_fixture(
    company_id: str = None,
    project_id: str = None,
    conversation_id: str = None,
    channel: str = "whatsapp",
    status: str = "processing",
    message_count: int = 3,
) -> Dict[str, Any]:
    """
    Create a conversation data fixture for testing.
    
    Args:
        company_id: Optional company ID (generated if None)
        project_id: Optional project ID (generated if None)
        conversation_id: Optional conversation ID (generated if None)
        channel: Channel method (whatsapp, email, or sms)
        status: Conversation status
        message_count: Number of messages to include
        
    Returns:
        A dictionary representing conversation data
    """
    company_id = company_id or generate_unique_id("company")
    project_id = project_id or generate_unique_id("project")
    conversation_id = conversation_id or generate_unique_id("convo")
    request_id = generate_unique_id("request")
    message_id = generate_unique_id("msg")
    
    # Common fields regardless of channel
    conversation = {
        "conversation_id": conversation_id,
        "company_id": company_id,
        "project_id": project_id,
        "company_name": f"Test Company {company_id}",
        "project_name": f"Test Project {project_id}",
        "channel_method": channel,
        "request_id": request_id,
        "router_version": "v1.0",
        "conversation_status": status,
        "company_rep": {
            "company_rep_1": "Test Rep 1",
        },
        "recipient_first_name": "Test",
        "recipient_last_name": "User",
        "comms_consent": True,
        "project_data": {
            "job_id": f"job-{generate_unique_id()}",
            "job_role": "Test Role",
        },
        "ai_config": {
            "assistant_id_template_sender": f"assistant-template-{generate_unique_id()}",
            "assistant_id_replies": f"assistant-replies-{generate_unique_id()}",
            "ai_api_key_reference": "secret/openai/key",
        },
        "message_id": message_id,
        "created_at": generate_timestamp(days_ago=2),
        "updated_at": generate_timestamp(hours_ago=6),
    }
    
    # Channel-specific fields
    if channel == "whatsapp":
        conversation["recipient_tel"] = generate_phone_number()
        conversation["company_whatsapp_number"] = generate_phone_number()
        conversation["whatsapp_credentials_reference"] = f"secret/whatsapp/{company_id}"
    elif channel == "email":
        conversation["recipient_email"] = f"test-{generate_unique_id()}@example.com"
        conversation["company_email"] = f"noreply@{company_id.lower()}.example.com"
        conversation["email_credentials_reference"] = f"secret/email/{company_id}"
        conversation["email_subject"] = "Test Email Subject"
    elif channel == "sms":
        conversation["recipient_tel"] = generate_phone_number()
        conversation["company_sms_number"] = generate_phone_number()
        conversation["sms_credentials_reference"] = f"secret/sms/{company_id}"
    
    # Generate messages
    messages = []
    
    # System message
    messages.append({
        "entry_id": f"msg-system-{generate_unique_id()}",
        "role": "system",
        "content": "System message for conversation initialization",
        "message_timestamp": generate_timestamp(days_ago=2),
    })
    
    # Alternating user and assistant messages
    for i in range(message_count):
        if i % 2 == 0:
            # User message
            messages.append({
                "entry_id": f"msg-user-{generate_unique_id()}",
                "role": "user",
                "content": f"User message {i+1}",
                "message_timestamp": generate_timestamp(days_ago=1, hours_ago=12-(i*2)),
            })
        else:
            # Assistant message
            messages.append({
                "entry_id": f"msg-assistant-{generate_unique_id()}",
                "role": "assistant",
                "content": f"Assistant response {i+1}",
                "message_timestamp": generate_timestamp(days_ago=1, hours_ago=12-(i*2)-1),
                "ai_prompt_tokens": random.randint(200, 500),
                "ai_completion_tokens": random.randint(100, 300),
            })
    
    conversation["messages"] = messages
    
    return conversation


def create_bulk_company_data(
    company_count: int = 5,
    projects_per_company: int = 3,
) -> List[Dict[str, Any]]:
    """
    Create bulk company data for performance testing.
    
    Args:
        company_count: Number of companies to create
        projects_per_company: Number of projects per company
        
    Returns:
        A list of company data dictionaries
    """
    result = []
    
    for c in range(company_count):
        company_id = f"bulk-company-{c}"
        
        for p in range(projects_per_company):
            project_id = f"bulk-project-{c}-{p}"
            result.append(create_company_data_fixture(company_id, project_id))
    
    return result


def create_bulk_conversation_data(
    company_count: int = 3,
    conversations_per_company: int = 10,
    channels: List[str] = None,
) -> List[Dict[str, Any]]:
    """
    Create bulk conversation data for performance testing.
    
    Args:
        company_count: Number of companies
        conversations_per_company: Number of conversations per company
        channels: List of channels to use (defaults to ["whatsapp", "email", "sms"])
        
    Returns:
        A list of conversation data dictionaries
    """
    result = []
    channels = channels or ["whatsapp", "email", "sms"]
    
    for c in range(company_count):
        company_id = f"bulk-company-{c}"
        project_id = f"bulk-project-{c}"
        
        for i in range(conversations_per_company):
            # Rotate through channels
            channel = channels[i % len(channels)]
            
            result.append(create_conversation_data_fixture(
                company_id=company_id,
                project_id=project_id,
                conversation_id=f"bulk-convo-{c}-{i}",
                channel=channel,
                message_count=random.randint(2, 5)
            ))
    
    return result 