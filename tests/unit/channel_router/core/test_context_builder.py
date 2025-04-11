# tests/unit/channel_router/core/test_context_builder.py

import pytest
import uuid

# Assuming the source code is now in src_dev/channel_router/app/...
from src_dev.channel_router.app.core.context_builder import (
    build_context_object,
    generate_conversation_data_dict,
    create_conversation_id
)

# --- Test Data Fixtures ---

@pytest.fixture
def sample_frontend_payload():
    """Provides a sample frontend payload dictionary."""
    return {
        "company_data": {
            "company_id": "comp-123",
            "project_id": "proj-abc"
        },
        "recipient_data": {
            "recipient_tel": "+447111222333",
            "recipient_email": "test@example.com",
            "comms_consent": True
        },
        "request_data": {
            "request_id": str(uuid.uuid4()),
            "channel_method": "whatsapp",
            "initial_request_timestamp": "2024-01-01T10:00:00Z"
        },
        "project_data": {"key": "value"}
    }

@pytest.fixture
def sample_company_data():
    """Provides a sample company data dictionary."""
    return {
        "company_id": "comp-123", # Match payload
        "project_id": "proj-abc", # Match payload
        "company_name": "Test Corp",
        "project_name": "Test Project",
        "allowed_channels": ["whatsapp", "sms", "email"],
        "project_status": "active",
        "channel_config": {
            "whatsapp": {
                "company_whatsapp_number": "+447999888777",
                "whatsapp_credentials_id": "sec-whatsapp"
            },
            "email": {
                "company_email": "company@example.org",
                "email_credentials_id": "sec-email"
            },
             "sms": {
                "company_sms_number": "+15551234567",
                "sms_credentials_id": "sec-sms"
            }
        },
        "ai_config": { "some_ai": "config" }
        # Add other fields as needed to reflect actual structure
    }

@pytest.fixture
def sample_router_version():
    """Provides a sample router version string."""
    return "router-dev-1.1.0"

# --- Test Cases for create_conversation_id ---

def test_create_conversation_id_whatsapp(sample_frontend_payload, sample_company_data):
    """Test conversation ID creation for WhatsApp."""
    frontend = sample_frontend_payload
    company = sample_company_data
    frontend["request_data"]["channel_method"] = "whatsapp"

    expected_id = f"comp-123#proj-abc#{frontend['request_data']['request_id']}#447999888777"
    conv_id = create_conversation_id(frontend, company)
    assert conv_id == expected_id

def test_create_conversation_id_sms(sample_frontend_payload, sample_company_data):
    """Test conversation ID creation for SMS."""
    frontend = sample_frontend_payload
    company = sample_company_data
    frontend["request_data"]["channel_method"] = "sms"

    expected_id = f"comp-123#proj-abc#{frontend['request_data']['request_id']}#15551234567"
    conv_id = create_conversation_id(frontend, company)
    assert conv_id == expected_id

def test_create_conversation_id_email(sample_frontend_payload, sample_company_data):
    """Test conversation ID creation for Email."""
    frontend = sample_frontend_payload
    company = sample_company_data
    frontend["request_data"]["channel_method"] = "email"

    expected_id = f"comp-123#proj-abc#{frontend['request_data']['request_id']}#company@example.org"
    conv_id = create_conversation_id(frontend, company)
    assert conv_id == expected_id

def test_create_conversation_id_missing_channel_config(sample_frontend_payload, sample_company_data):
    """Test conversation ID uses placeholder if channel config is missing."""
    frontend = sample_frontend_payload
    company = sample_company_data
    frontend["request_data"]["channel_method"] = "whatsapp"
    del company["channel_config"]["whatsapp"] # Remove whatsapp config

    expected_id = f"comp-123#proj-abc#{frontend['request_data']['request_id']}#unknown_whatsapp_number"
    conv_id = create_conversation_id(frontend, company)
    assert conv_id == expected_id

def test_create_conversation_id_missing_specific_contact(sample_frontend_payload, sample_company_data):
    """Test conversation ID uses placeholder if specific number/email is missing."""
    frontend = sample_frontend_payload
    company = sample_company_data
    frontend["request_data"]["channel_method"] = "email"
    del company["channel_config"]["email"]["company_email"] # Remove email address

    expected_id = f"comp-123#proj-abc#{frontend['request_data']['request_id']}#unknown_company_email"
    conv_id = create_conversation_id(frontend, company)
    assert conv_id == expected_id

def test_create_conversation_id_unknown_channel(sample_frontend_payload, sample_company_data):
    """Test conversation ID uses channel name for unknown channels."""
    frontend = sample_frontend_payload
    company = sample_company_data
    unknown_channel = "telegram"
    frontend["request_data"]["channel_method"] = unknown_channel

    expected_id = f"comp-123#proj-abc#{frontend['request_data']['request_id']}#{unknown_channel}"
    conv_id = create_conversation_id(frontend, company)
    assert conv_id == expected_id

# --- Test Cases for generate_conversation_data_dict ---

def test_generate_conversation_data_dict_structure(sample_frontend_payload, sample_company_data):
    """Test the structure of the generated conversation data dict."""
    conv_data = generate_conversation_data_dict(sample_frontend_payload, sample_company_data)

    assert isinstance(conv_data, dict)
    assert "conversation_id" in conv_data
    assert isinstance(conv_data["conversation_id"], str)
    assert conv_data["conversation_status"] == "initiated"
    # Verify conversation_id format based on create_conversation_id logic
    assert conv_data["conversation_id"].startswith("comp-123#proj-abc#")
    assert conv_data["conversation_id"].endswith("#447999888777") # Default channel is whatsapp

# --- Test Cases for build_context_object ---

def test_build_context_object_structure(sample_frontend_payload, sample_company_data, sample_router_version):
    """Test the overall structure of the built context object."""
    context = build_context_object(sample_frontend_payload, sample_company_data, sample_router_version)

    assert isinstance(context, dict)
    assert "metadata" in context
    assert "frontend_payload" in context
    assert "company_data_payload" in context
    assert "conversation_data" in context

    assert context["metadata"] == {"router_version": sample_router_version}
    assert context["frontend_payload"] == sample_frontend_payload
    assert context["company_data_payload"] == sample_company_data
    assert isinstance(context["conversation_data"], dict)
    assert "conversation_id" in context["conversation_data"]
    assert context["conversation_data"]["conversation_status"] == "initiated" 