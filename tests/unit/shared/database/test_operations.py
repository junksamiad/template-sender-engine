"""
Tests for database operations.

This module provides unit tests for the DatabaseOperations class.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.shared.database.operations import DatabaseOperations
from src.shared.database.models import WaCompanyData, Conversation, ConversationStatus


@pytest.mark.unit
@pytest.mark.phase1
def test_init_database_operations():
    """Test initializing the DatabaseOperations class."""
    db_ops = DatabaseOperations(env_name="test")
    assert db_ops.env_name == "test"
    assert db_ops.wa_company_data_table == "wa_company_data-test"
    assert db_ops.conversations_table == "conversations-test"
    
    # Test with custom table names
    db_ops = DatabaseOperations(
        wa_company_data_table_name="custom-company-table",
        conversations_table_name="custom-conversations-table",
        env_name="prod"
    )
    assert db_ops.wa_company_data_table == "custom-company-table"
    assert db_ops.conversations_table == "custom-conversations-table"
    assert db_ops.env_name == "prod"


@pytest.mark.unit
@pytest.mark.phase1
def test_company_data_operations(mock_db_operations, sample_company_data):
    """Test company data CRUD operations."""
    # Create company data
    company_data = WaCompanyData(**sample_company_data)
    result = mock_db_operations.create_company_data(company_data)
    
    # Verify the result
    assert result.company_id == "test-company-1"
    assert result.project_id == "test-project-1"
    assert result.company_name == "Test Company"
    assert result.created_at is not None
    assert result.updated_at is not None
    
    # Get company data
    retrieved = mock_db_operations.get_company_data("test-company-1", "test-project-1")
    assert retrieved is not None
    assert retrieved.company_id == "test-company-1"
    assert retrieved.project_name == "Test Project"
    
    # Update company data
    retrieved.project_status = "inactive"
    updated = mock_db_operations.update_company_data(retrieved)
    assert updated.project_status == "inactive"
    
    # Verify update was saved
    retrieved_again = mock_db_operations.get_company_data("test-company-1", "test-project-1")
    assert retrieved_again.project_status == "inactive"
    
    # List company projects
    # Add another project for the same company
    second_project = sample_company_data.copy()
    second_project["project_id"] = "test-project-2"
    second_project["project_name"] = "Test Project 2"
    mock_db_operations.create_company_data(WaCompanyData(**second_project))
    
    projects = mock_db_operations.list_company_projects("test-company-1")
    assert len(projects) == 2
    assert any(p.project_id == "test-project-1" for p in projects)
    assert any(p.project_id == "test-project-2" for p in projects)
    
    # Delete company data
    result = mock_db_operations.delete_company_data("test-company-1", "test-project-1")
    assert result is True
    
    # Verify deletion
    retrieved = mock_db_operations.get_company_data("test-company-1", "test-project-1")
    assert retrieved is None
    
    # Try to delete non-existent data
    result = mock_db_operations.delete_company_data("non-existent", "project")
    assert result is False


@pytest.mark.unit
@pytest.mark.phase1
def test_conversation_operations(mock_db_operations, sample_conversation_data):
    """Test conversation CRUD operations."""
    # Update the sample data to include recipient_email and message_id (required by the GSIs)
    convo_data = sample_conversation_data.copy()
    convo_data["recipient_email"] = "test@example.com"
    convo_data["message_id"] = "msg-test-1"
    
    # Create conversation
    conversation = Conversation(**convo_data)
    result = mock_db_operations.create_conversation(conversation)
    
    # Verify the result
    assert result.conversation_id == "test-convo-1"
    assert result.company_id == "test-company-1"
    assert result.project_id == "test-project-1"
    assert result.channel_method == "whatsapp"
    assert result.created_at is not None
    assert result.updated_at is not None
    
    # Get conversation
    primary_key = {"recipient_tel": "+1234567890", "conversation_id": "test-convo-1"}
    retrieved = mock_db_operations.get_conversation(primary_key)
    assert retrieved is not None
    assert retrieved.conversation_id == "test-convo-1"
    assert retrieved.recipient_tel == "+1234567890"
    
    # Update conversation
    retrieved.conversation_status = ConversationStatus.INITIAL_MESSAGE_SENT
    updated = mock_db_operations.update_conversation(retrieved)
    assert updated.conversation_status == ConversationStatus.INITIAL_MESSAGE_SENT
    
    # Verify update was saved
    retrieved_again = mock_db_operations.get_conversation(primary_key)
    assert retrieved_again.conversation_status == ConversationStatus.INITIAL_MESSAGE_SENT
    
    # Update conversation status directly
    result = mock_db_operations.update_conversation_status(primary_key, ConversationStatus.FAILED)
    assert result is True
    
    # Verify status update
    retrieved = mock_db_operations.get_conversation(primary_key)
    assert retrieved.conversation_status == ConversationStatus.FAILED
    
    # Add message to conversation
    new_message = {
        "entry_id": "msg-2",
        "role": "user",
        "content": "Test message",
        "message_timestamp": datetime.now().isoformat(),
    }
    
    result = mock_db_operations.add_message_to_conversation(primary_key, new_message)
    assert result is True
    
    # Verify message was added
    retrieved = mock_db_operations.get_conversation(primary_key)
    assert len(retrieved.messages) == 2
    assert retrieved.messages[1].entry_id == "msg-2"
    assert retrieved.messages[1].role == "user"
    
    # Delete conversation
    result = mock_db_operations.delete_conversation(primary_key)
    assert result is True
    
    # Verify deletion
    retrieved = mock_db_operations.get_conversation(primary_key)
    assert retrieved is None
    
    # Try to delete non-existent conversation
    result = mock_db_operations.delete_conversation({"recipient_tel": "non-existent", "conversation_id": "non-existent"})
    assert result is False


@pytest.mark.unit
@pytest.mark.phase1
def test_conversation_queries(mock_db_operations, sample_conversation_data):
    """Test conversation query operations."""
    # Create multiple conversations for testing queries
    base_convo = sample_conversation_data.copy()
    base_convo["recipient_email"] = "test1@example.com"
    base_convo["message_id"] = "msg-test-1"
    
    # Conversation 1: WhatsApp, Company 1, Project 1
    mock_db_operations.create_conversation(Conversation(**base_convo))
    
    # Conversation 2: WhatsApp, Company 1, Project 2
    convo2 = base_convo.copy()
    convo2["conversation_id"] = "test-convo-2"
    convo2["project_id"] = "test-project-2"
    convo2["request_id"] = "test-request-2"
    convo2["recipient_tel"] = "+1234567891"
    convo2["recipient_email"] = "test2@example.com"
    convo2["message_id"] = "message-2"
    mock_db_operations.create_conversation(Conversation(**convo2))
    
    # Conversation 3: Email, Company 1, Project 1
    convo3 = base_convo.copy()
    convo3["conversation_id"] = "test-convo-3"
    convo3["channel_method"] = "email"
    convo3["recipient_email"] = "test3@example.com"
    convo3["recipient_tel"] = "+1234567892"  # Need to include a valid recipient_tel value
    convo3["request_id"] = "test-request-3"
    convo3["message_id"] = "msg-test-3"
    mock_db_operations.create_conversation(Conversation(**convo3))
    
    # Conversation 4: WhatsApp, Company 2, Project 1
    convo4 = base_convo.copy()
    convo4["conversation_id"] = "test-convo-4"
    convo4["company_id"] = "test-company-2"
    convo4["recipient_tel"] = "+1234567893"
    convo4["recipient_email"] = "test4@example.com"
    convo4["request_id"] = "test-request-4"
    convo4["message_id"] = "msg-test-4"
    mock_db_operations.create_conversation(Conversation(**convo4))
    
    # Test query by company and project
    results = mock_db_operations.query_conversations_by_company_project(
        "test-company-1", "test-project-1"
    )
    assert len(results) == 2  # Should return conversations 1 and 3
    assert any(c.conversation_id == "test-convo-1" for c in results)
    assert any(c.conversation_id == "test-convo-3" for c in results)
    
    # Test query by request ID
    results = mock_db_operations.query_conversations_by_request_id("test-request-2")
    assert len(results) == 1
    assert results[0].conversation_id == "test-convo-2"
    
    # Test query by channel
    results = mock_db_operations.query_conversations_by_channel("whatsapp")
    assert len(results) == 3  # Should return conversations 1, 2, and 4
    
    # Test query by email
    result = mock_db_operations.query_conversation_by_email("test3@example.com", "test-convo-3")
    assert result is not None
    assert result.conversation_id == "test-convo-3"
    
    # Test query by message ID
    result = mock_db_operations.query_conversation_by_message_id("message-2")
    assert result is not None
    assert result.conversation_id == "test-convo-2"
    
    # Test query by status
    # Update status of conversation 2
    mock_db_operations.update_conversation_status(
        {"recipient_tel": "+1234567891", "conversation_id": "test-convo-2"},
        ConversationStatus.FAILED
    )
    
    results = mock_db_operations.query_conversations_by_status(ConversationStatus.FAILED)
    assert len(results) == 1
    assert results[0].conversation_id == "test-convo-2"
    
    # Test query recent conversations
    # All conversations have the same creation time in the test
    results = mock_db_operations.query_recent_conversations(
        datetime.now().isoformat(),
        channel="whatsapp"
    )
    assert len(results) > 0


@pytest.mark.unit
@pytest.mark.phase1
def test_error_handling(mock_db_operations, sample_company_data):
    """Test error handling in database operations."""
    # Test validation error in create
    invalid_company = {"company_id": "", "project_id": "", "company_name": "", "project_name": ""}
    with pytest.raises(ValueError):
        mock_db_operations.create_company_data(WaCompanyData(**invalid_company))
    
    # Test update non-existent company
    non_existent = WaCompanyData(
        company_id="non-existent",
        project_id="non-existent",
        company_name="Non-existent Company",
        project_name="Non-existent Project"
    )
    with pytest.raises(ValueError):
        mock_db_operations.update_company_data(non_existent)
    
    # Test client error handling with mock
    with patch.object(mock_db_operations.dynamodb_client, 'get_item', side_effect=Exception("Test exception")):
        with pytest.raises(Exception):
            mock_db_operations.get_company_data("test-company", "test-project") 