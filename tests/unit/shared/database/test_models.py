"""
Tests for database models.

This module provides unit tests for the database model classes.
"""
import pytest
from datetime import datetime, timezone

from src.shared.database.models import (
    WaCompanyData,
    Conversation,
    Message,
    ChannelMethod,
    ConversationStatus,
    AIConfig,
    CompanyRep,
    BaseModel,
)


class TestModel(BaseModel):
    """Simple test model extending BaseModel for testing purposes."""
    
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name
        
    def validate(self):
        errors = []
        if not self.id:
            errors.append("id cannot be empty")
        if not self.name:
            errors.append("name cannot be empty")
        return errors


@pytest.mark.unit
@pytest.mark.phase1
def test_base_model():
    """Test BaseModel functionality."""
    # Test initialization and to_item
    model = TestModel(id="test-id", name="Test Name")
    
    item = model.to_item()
    assert item["id"] == "test-id"
    assert item["name"] == "Test Name"
    
    # Test from_item
    new_model = TestModel.from_item(item)
    assert new_model.id == "test-id"
    assert new_model.name == "Test Name"
    
    # Test validation
    errors = model.validate()
    assert len(errors) == 0
    
    invalid_model = TestModel(id="", name="")
    errors = invalid_model.validate()
    assert len(errors) == 2
    assert "id cannot be empty" in errors
    assert "name cannot be empty" in errors


@pytest.mark.unit
@pytest.mark.phase1
def test_channel_method_enum():
    """Test ChannelMethod enum."""
    assert ChannelMethod.WHATSAPP.value == "whatsapp"
    assert ChannelMethod.SMS.value == "sms"
    assert ChannelMethod.EMAIL.value == "email"
    
    # Test conversion from string
    assert ChannelMethod("whatsapp") == ChannelMethod.WHATSAPP
    assert ChannelMethod("sms") == ChannelMethod.SMS
    assert ChannelMethod("email") == ChannelMethod.EMAIL


@pytest.mark.unit
@pytest.mark.phase1
def test_conversation_status_enum():
    """Test ConversationStatus enum."""
    assert ConversationStatus.PROCESSING.value == "processing"
    assert ConversationStatus.INITIAL_MESSAGE_SENT.value == "initial_message_sent"
    assert ConversationStatus.FAILED.value == "failed"
    
    # Test conversion from string
    assert ConversationStatus("processing") == ConversationStatus.PROCESSING
    assert ConversationStatus("initial_message_sent") == ConversationStatus.INITIAL_MESSAGE_SENT
    assert ConversationStatus("failed") == ConversationStatus.FAILED


@pytest.mark.unit
@pytest.mark.phase1
def test_ai_config():
    """Test AIConfig functionality."""
    # Test initialization
    ai_config = AIConfig(
        assistant_id_template_sender="assistant-1",
        assistant_id_replies="assistant-2",
        ai_api_key_reference="secret/openai/key",
        assistant_id_3="assistant-3",
    )
    
    assert ai_config.assistant_id_template_sender == "assistant-1"
    assert ai_config.assistant_id_replies == "assistant-2"
    assert ai_config.ai_api_key_reference == "secret/openai/key"
    assert ai_config.assistant_id_3 == "assistant-3"
    assert ai_config.assistant_id_4 is None
    
    # Test to_dict
    ai_dict = ai_config.to_dict()
    assert ai_dict["assistant_id_template_sender"] == "assistant-1"
    assert ai_dict["assistant_id_replies"] == "assistant-2"
    assert ai_dict["ai_api_key_reference"] == "secret/openai/key"
    assert ai_dict["assistant_id_3"] == "assistant-3"
    assert "assistant_id_4" not in ai_dict
    
    # Test from_dict
    new_ai_config = AIConfig.from_dict(ai_dict)
    assert new_ai_config.assistant_id_template_sender == "assistant-1"
    assert new_ai_config.assistant_id_replies == "assistant-2"
    assert new_ai_config.ai_api_key_reference == "secret/openai/key"
    assert new_ai_config.assistant_id_3 == "assistant-3"
    assert new_ai_config.assistant_id_4 is None


@pytest.mark.unit
@pytest.mark.phase1
def test_company_rep():
    """Test CompanyRep functionality."""
    # Test initialization
    company_rep = CompanyRep(
        company_rep_1="John Doe",
        company_rep_2="Jane Smith",
    )
    
    assert company_rep.company_rep_1 == "John Doe"
    assert company_rep.company_rep_2 == "Jane Smith"
    assert company_rep.company_rep_3 is None
    
    # Test to_dict
    rep_dict = company_rep.to_dict()
    assert rep_dict["company_rep_1"] == "John Doe"
    assert rep_dict["company_rep_2"] == "Jane Smith"
    assert "company_rep_3" not in rep_dict
    
    # Test from_dict
    new_company_rep = CompanyRep.from_dict(rep_dict)
    assert new_company_rep.company_rep_1 == "John Doe"
    assert new_company_rep.company_rep_2 == "Jane Smith"
    assert new_company_rep.company_rep_3 is None
    
    # Test with empty dict
    empty_rep = CompanyRep.from_dict({})
    assert empty_rep.company_rep_1 is None
    assert empty_rep.company_rep_2 is None


@pytest.mark.unit
@pytest.mark.phase1
def test_message():
    """Test Message functionality."""
    # Test initialization with string timestamp
    message = Message(
        entry_id="msg-1",
        role="user",
        content="Hello world",
        message_timestamp="2023-06-01T12:00:00Z",
        ai_prompt_tokens=10,
        ai_completion_tokens=20,
    )
    
    assert message.entry_id == "msg-1"
    assert message.role == "user"
    assert message.content == "Hello world"
    assert isinstance(message.message_timestamp, datetime)
    assert message.message_timestamp.isoformat() == "2023-06-01T12:00:00+00:00"
    assert message.ai_prompt_tokens == 10
    assert message.ai_completion_tokens == 20
    assert message.ai_total_tokens == 30  # Should be calculated
    
    # Test initialization with datetime timestamp
    now = datetime.now(timezone.utc)
    message2 = Message(
        entry_id="msg-2",
        role="assistant",
        content="Response",
        message_timestamp=now,
    )
    
    assert message2.entry_id == "msg-2"
    assert message2.message_timestamp == now
    
    # Test to_dict
    msg_dict = message.to_dict()
    assert msg_dict["entry_id"] == "msg-1"
    assert msg_dict["role"] == "user"
    assert msg_dict["content"] == "Hello world"
    assert msg_dict["message_timestamp"] == "2023-06-01T12:00:00+00:00"
    assert msg_dict["ai_prompt_tokens"] == 10
    assert msg_dict["ai_completion_tokens"] == 20
    assert msg_dict["ai_total_tokens"] == 30
    
    # Test from_dict
    new_message = Message.from_dict(msg_dict)
    assert new_message.entry_id == "msg-1"
    assert new_message.role == "user"
    assert new_message.content == "Hello world"
    assert isinstance(new_message.message_timestamp, datetime)
    assert new_message.ai_prompt_tokens == 10
    assert new_message.ai_completion_tokens == 20
    assert new_message.ai_total_tokens == 30


@pytest.mark.unit
@pytest.mark.phase1
def test_wa_company_data(sample_company_data):
    """Test WaCompanyData functionality."""
    # Test initialization from dict
    company = WaCompanyData(**sample_company_data)
    
    assert company.company_id == "test-company-1"
    assert company.project_id == "test-project-1"
    assert company.company_name == "Test Company"
    assert company.project_name == "Test Project"
    assert company.project_status == "active"
    assert "whatsapp" in company.allowed_channels
    assert "email" in company.allowed_channels
    assert company.company_rep.company_rep_1 == "John Doe"
    assert company.company_rep.company_rep_2 == "Jane Smith"
    assert company.rate_limits["whatsapp"]["max_per_minute"] == 60
    assert company.channel_config["whatsapp"]["template_ids"] == ["template-1", "template-2"]
    assert isinstance(company.created_at, datetime)
    assert isinstance(company.updated_at, datetime)
    
    # Test to_item
    item = company.to_item()
    assert item["company_id"] == "test-company-1"
    assert item["project_id"] == "test-project-1"
    assert item["company_name"] == "Test Company"
    assert item["company_rep"]["company_rep_1"] == "John Doe"
    assert "created_at" in item
    assert "updated_at" in item
    
    # Test validation
    errors = company.validate()
    assert len(errors) == 0
    
    # Test invalid company (missing required fields)
    invalid_company = WaCompanyData(
        company_id="",
        project_id="",
        company_name="",
        project_name="",
    )
    
    errors = invalid_company.validate()
    assert len(errors) > 0
    assert any("company_id" in err for err in errors)
    assert any("project_id" in err for err in errors)
    assert any("company_name" in err for err in errors)
    assert any("project_name" in err for err in errors)


@pytest.mark.unit
@pytest.mark.phase1
def test_conversation(sample_conversation_data):
    """Test Conversation functionality."""
    # Test initialization from dict
    conversation = Conversation(**sample_conversation_data)
    
    assert conversation.conversation_id == "test-convo-1"
    assert conversation.company_id == "test-company-1"
    assert conversation.project_id == "test-project-1"
    assert conversation.channel_method == ChannelMethod.WHATSAPP
    assert conversation.conversation_status == ConversationStatus.PROCESSING
    assert conversation.recipient_tel == "+1234567890"
    assert conversation.company_rep.company_rep_1 == "John Doe"
    assert conversation.project_data["job_id"] == "job-123"
    assert conversation.ai_config.assistant_id_template_sender == "assistant-template-1"
    assert len(conversation.messages) == 1
    assert conversation.messages[0].role == "system"
    assert conversation.messages[0].content == "System message"
    assert isinstance(conversation.created_at, datetime)
    assert isinstance(conversation.updated_at, datetime)
    assert conversation.ttl is None
    
    # Test to_item
    item = conversation.to_item()
    assert item["conversation_id"] == "test-convo-1"
    assert item["company_id"] == "test-company-1"
    assert item["channel_method"] == "whatsapp"
    assert item["conversation_status"] == "processing"
    assert item["messages"][0]["role"] == "system"
    
    # Test validation
    errors = conversation.validate()
    assert len(errors) == 0
    
    # Test set_ttl
    conversation.set_ttl(days=30)
    assert conversation.ttl is not None
    
    # Test add_message
    new_message = {
        "entry_id": "msg-2",
        "role": "user",
        "content": "Hello",
        "message_timestamp": "2023-06-01T12:30:00Z",
    }
    
    conversation.add_message(new_message)
    assert len(conversation.messages) == 2
    assert conversation.messages[1].entry_id == "msg-2"
    assert conversation.messages[1].role == "user" 