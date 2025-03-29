"""
Unit tests for the Context Object implementation.
"""

import json
import uuid
from datetime import datetime
import pytest

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
    EmailConfig,
    AIConfigContext,
    ConversationData,
    Metadata,
    CompanyRep,
    ChannelMethod
)
from src.shared.context.serialization import (
    serialize_context,
    deserialize_context
)
from src.shared.context.validation import validate_context


def create_sample_context() -> ContextObject:
    """Create a sample context object for testing."""
    return ContextObject(
        frontend_payload=FrontendPayload(
            company_data=CompanyData(
                company_id="cucumber-recruitment",
                project_id="cv-analysis"
            ),
            recipient_data=RecipientData(
                recipient_first_name="John",
                recipient_last_name="Doe",
                recipient_tel="+447700900123",
                recipient_email="john.doe@example.com",
                comms_consent=True
            ),
            request_data=RequestData(
                request_id=str(uuid.uuid4()),
                channel_method=ChannelMethod.WHATSAPP,
                initial_request_timestamp=datetime.now().isoformat()
            ),
            project_data=ProjectData(
                job_title="Software Engineer",
                job_description="We are looking for a skilled software engineer...",
                application_deadline="2023-07-30T23:59:59Z"
            )
        ),
        wa_company_data_payload=WaCompanyDataPayload(
            company_name="Cucumber Recruitment Ltd",
            project_name="CV Analysis Bot",
            project_status="active",
            allowed_channels=["whatsapp", "email"],
            company_rep=CompanyRep(
                company_rep_1="Carol",
                company_rep_2="Mark"
            )
        ),
        project_rate_limits=ProjectRateLimits(
            requests_per_minute=100,
            requests_per_day=10000,
            concurrent_conversations=50,
            max_message_length=4096
        ),
        channel_config=ChannelConfig(
            whatsapp=WhatsAppConfig(
                whatsapp_credentials_id="whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio",
                company_whatsapp_number="+14155238886"
            )
        ),
        ai_config=AIConfigContext(
            assistant_id_template_sender="asst_Ds59ylP35Pn84pasJQVglC2Q",
            assistant_id_replies="asst_Ds59ylP35Pn84pesJQVglC2Q",
            ai_api_key_reference="ai-api-key/global/global/global"
        ),
        conversation_data=ConversationData(
            conversation_id="cucumber-recruitment#cv-analysis#550e8400-e29b-41d4-a716-446655440000#14155238886"
        ),
        metadata=Metadata(
            router_version="1.0.0",
            created_at=datetime.now().isoformat()
        )
    )


class TestContextObject:
    """Test cases for the Context Object implementation."""

    def test_context_object_creation(self):
        """Test that a context object can be created with all required fields."""
        context = create_sample_context()
        assert context is not None
        assert context.frontend_payload is not None
        assert context.frontend_payload.company_data.company_id == "cucumber-recruitment"
        assert context.frontend_payload.recipient_data.recipient_first_name == "John"
        assert context.frontend_payload.request_data.channel_method == ChannelMethod.WHATSAPP
        assert context.wa_company_data_payload.company_name == "Cucumber Recruitment Ltd"
        assert context.project_rate_limits.requests_per_minute == 100
        assert context.channel_config.whatsapp is not None
        assert context.channel_config.whatsapp.company_whatsapp_number == "+14155238886"
        assert context.ai_config.assistant_id_template_sender == "asst_Ds59ylP35Pn84pasJQVglC2Q"
        assert context.conversation_data.conversation_id == "cucumber-recruitment#cv-analysis#550e8400-e29b-41d4-a716-446655440000#14155238886"
        assert context.metadata.router_version == "1.0.0"

    def test_serialization_deserialization(self):
        """Test that a context object can be serialized and deserialized."""
        context = create_sample_context()
        
        # Serialize
        json_str = serialize_context(context)
        assert json_str is not None
        assert isinstance(json_str, str)
        
        # Verify JSON structure
        json_data = json.loads(json_str)
        assert json_data["frontend_payload"]["company_data"]["company_id"] == "cucumber-recruitment"
        
        # Deserialize
        deserialized_context = deserialize_context(json_str)
        assert deserialized_context is not None
        assert deserialized_context.frontend_payload.company_data.company_id == context.frontend_payload.company_data.company_id
        assert deserialized_context.channel_config.whatsapp.company_whatsapp_number == context.channel_config.whatsapp.company_whatsapp_number

    def test_get_channel_method(self):
        """Test that the channel method can be retrieved correctly."""
        context = create_sample_context()
        channel_method = context.get_channel_method()
        assert channel_method == ChannelMethod.WHATSAPP
        
        # Test with string channel method
        context.frontend_payload.request_data.channel_method = "email"
        channel_method = context.get_channel_method()
        assert channel_method == ChannelMethod.EMAIL

    def test_get_active_channel_config(self):
        """Test that the active channel config can be retrieved correctly."""
        context = create_sample_context()
        
        # Test WhatsApp
        channel_config = context.get_active_channel_config()
        assert channel_config is not None
        assert channel_config == context.channel_config.whatsapp
        
        # Test Email
        context.frontend_payload.request_data.channel_method = ChannelMethod.EMAIL
        context.channel_config.email = EmailConfig(
            email_credentials_id="email-credentials/cucumber-recruitment/cv-analysis/sendgrid",
            company_email="jobs@cucumber-recruitment.com"
        )
        channel_config = context.get_active_channel_config()
        assert channel_config is not None
        assert channel_config == context.channel_config.email
        
    def test_get_credentials_reference(self):
        """Test that the credentials reference can be retrieved correctly."""
        context = create_sample_context()
        
        # Test WhatsApp
        reference = context.get_credentials_reference()
        assert reference == "whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio"
        
        # Test Email
        context.frontend_payload.request_data.channel_method = ChannelMethod.EMAIL
        context.channel_config.email = EmailConfig(
            email_credentials_id="email-credentials/cucumber-recruitment/cv-analysis/sendgrid",
            company_email="jobs@cucumber-recruitment.com"
        )
        reference = context.get_credentials_reference()
        assert reference == "email-credentials/cucumber-recruitment/cv-analysis/sendgrid"

    def test_validation_valid_context(self):
        """Test validation with a valid context object."""
        context = create_sample_context()
        errors = validate_context(context)
        assert not errors, f"Validation errors found: {errors}"

    def test_validation_invalid_context(self):
        """Test validation with an invalid context object."""
        # Create a context with missing required fields
        context = create_sample_context()
        context.frontend_payload.company_data.company_id = ""  # Required field
        
        errors = validate_context(context)
        assert errors
        assert any("company_id is required" in error for error in errors)
        
        # Test with invalid phone number
        context = create_sample_context()
        context.channel_config.whatsapp.company_whatsapp_number = "invalid-number"
        
        errors = validate_context(context)
        assert errors
        assert any("E.164 format" in error for error in errors) 