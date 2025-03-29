"""
Integration tests for DynamoDB database operations.

This module provides integration tests using a local DynamoDB instance.
"""
import pytest
from datetime import datetime

from src.shared.database.models import WaCompanyData, Conversation, Message


@pytest.mark.integration
@pytest.mark.phase1
def test_company_data_integration(integration_db_operations, integration_sample_company_data):
    """Test company data operations with a real DynamoDB instance."""
    # Create company data
    company_data = WaCompanyData(**integration_sample_company_data)
    result = integration_db_operations.create_company_data(company_data)
    
    # Verify the result
    assert result.company_id == "integration-company-1"
    assert result.project_id == "integration-project-1"
    assert result.company_name == "Integration Test Company"
    assert result.created_at is not None
    assert result.updated_at is not None
    
    # Get company data
    retrieved = integration_db_operations.get_company_data(
        "integration-company-1", "integration-project-1"
    )
    assert retrieved is not None
    assert retrieved.company_id == "integration-company-1"
    assert retrieved.project_name == "Integration Test Project"
    
    # Update company data
    retrieved.project_status = "inactive"
    updated = integration_db_operations.update_company_data(retrieved)
    assert updated.project_status == "inactive"
    
    # Verify update was saved
    retrieved_again = integration_db_operations.get_company_data(
        "integration-company-1", "integration-project-1"
    )
    assert retrieved_again.project_status == "inactive"
    
    # List company projects
    # Add another project for the same company
    second_project = integration_sample_company_data.copy()
    second_project["project_id"] = "integration-project-2"
    second_project["project_name"] = "Integration Test Project 2"
    integration_db_operations.create_company_data(WaCompanyData(**second_project))
    
    projects = integration_db_operations.list_company_projects("integration-company-1")
    assert len(projects) == 2
    assert any(p.project_id == "integration-project-1" for p in projects)
    assert any(p.project_id == "integration-project-2" for p in projects)
    
    # Delete company data
    result = integration_db_operations.delete_company_data(
        "integration-company-1", "integration-project-1"
    )
    assert result is True
    
    # Verify deletion
    retrieved = integration_db_operations.get_company_data(
        "integration-company-1", "integration-project-1"
    )
    assert retrieved is None


@pytest.mark.integration
@pytest.mark.phase1
def test_conversation_integration(integration_db_operations, integration_sample_conversation_data):
    """Test conversation operations with a real DynamoDB instance."""
    # Create conversation
    conversation = Conversation(**integration_sample_conversation_data)
    result = integration_db_operations.create_conversation(conversation)
    
    # Verify the result
    assert result.conversation_id == "integration-convo-1"
    assert result.company_id == "integration-company-1"
    assert result.channel_method == "whatsapp"
    assert result.created_at is not None
    assert result.updated_at is not None
    
    # Get conversation
    primary_key = {
        "recipient_tel": "+9876543210", 
        "conversation_id": "integration-convo-1"
    }
    retrieved = integration_db_operations.get_conversation(primary_key)
    assert retrieved is not None
    assert retrieved.conversation_id == "integration-convo-1"
    assert retrieved.recipient_tel == "+9876543210"
    
    # Update conversation status
    result = integration_db_operations.update_conversation_status(
        primary_key, "initial_message_sent"
    )
    assert result is True
    
    # Verify status update
    retrieved = integration_db_operations.get_conversation(primary_key)
    assert retrieved.conversation_status == "initial_message_sent"
    
    # Add message to conversation
    new_message = {
        "entry_id": "int-msg-2",
        "role": "user",
        "content": "Integration test message from user",
        "message_timestamp": datetime.now().isoformat(),
    }
    
    result = integration_db_operations.add_message_to_conversation(primary_key, new_message)
    assert result is True
    
    # Verify message was added
    retrieved = integration_db_operations.get_conversation(primary_key)
    assert len(retrieved.messages) == 2
    assert retrieved.messages[1].entry_id == "int-msg-2"
    assert retrieved.messages[1].role == "user"


@pytest.mark.integration
@pytest.mark.phase1
def test_conversation_queries_integration(integration_db_operations, integration_sample_conversation_data):
    """Test conversation query operations with a real DynamoDB instance."""
    # Create multiple conversations for testing queries
    base_convo = integration_sample_conversation_data.copy()
    
    # Make sure we start with a clean state (in case a previous test failed)
    try:
        integration_db_operations.delete_conversation({
            "recipient_tel": "+9876543210", 
            "conversation_id": "integration-convo-1"
        })
    except Exception:
        pass  # Ignore errors if the conversation doesn't exist
    
    # Conversation 1: WhatsApp, Company 1, Project 1
    integration_db_operations.create_conversation(Conversation(**base_convo))
    
    # Conversation 2: WhatsApp, Company 1, Project 2
    convo2 = base_convo.copy()
    convo2["conversation_id"] = "integration-convo-2"
    convo2["project_id"] = "integration-project-2"
    convo2["request_id"] = "integration-request-2"
    convo2["recipient_tel"] = "+9876543211"
    convo2["message_id"] = "message-integration-2"
    integration_db_operations.create_conversation(Conversation(**convo2))
    
    # Conversation 3: Email, Company 1, Project 1
    convo3 = base_convo.copy()
    convo3["conversation_id"] = "integration-convo-3"
    convo3["channel_method"] = "email"
    convo3["recipient_email"] = "integration@example.com"
    convo3["recipient_tel"] = None
    convo3["request_id"] = "integration-request-3"
    integration_db_operations.create_conversation(Conversation(**convo3))
    
    # Test query by company and project
    results = integration_db_operations.query_conversations_by_company_project(
        "integration-company-1", "integration-project-1"
    )
    assert len(results) == 2  # Should return conversations 1 and 3
    assert any(c.conversation_id == "integration-convo-1" for c in results)
    assert any(c.conversation_id == "integration-convo-3" for c in results)
    
    # Test query by request ID
    results = integration_db_operations.query_conversations_by_request_id("integration-request-2")
    assert len(results) == 1
    assert results[0].conversation_id == "integration-convo-2"
    
    # Test query by channel
    results = integration_db_operations.query_conversations_by_channel("whatsapp")
    assert len(results) == 2  # Should return conversations 1 and 2
    
    # Test query by email
    result = integration_db_operations.query_conversation_by_email(
        "integration@example.com", "integration-convo-3"
    )
    assert result is not None
    assert result.conversation_id == "integration-convo-3"
    
    # Test query by message ID
    result = integration_db_operations.query_conversation_by_message_id("message-integration-2")
    assert result is not None
    assert result.conversation_id == "integration-convo-2"
    
    # Clean up
    integration_db_operations.delete_conversation({
        "recipient_tel": "+9876543210", 
        "conversation_id": "integration-convo-1"
    })
    integration_db_operations.delete_conversation({
        "recipient_tel": "+9876543211", 
        "conversation_id": "integration-convo-2"
    })
    # Email conversation has no recipient_tel, so it needs the email index
    result = integration_db_operations.query_conversation_by_email(
        "integration@example.com", "integration-convo-3"
    )
    if result:
        integration_db_operations.delete_conversation({
            "recipient_tel": result.recipient_tel or "null", 
            "conversation_id": "integration-convo-3"
        }) 