"""
Additional error handling tests for database operations.

This module contains specific tests for error handling edge cases.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.shared.database.models import WaCompanyData, Conversation, Message
from src.shared.database.operations import DatabaseOperations


@pytest.mark.unit
@pytest.mark.phase1
def test_conversation_error_handling(mock_db_operations, sample_conversation_data):
    """Test error handling in conversation operations."""
    # Test validation error with invalid fields
    invalid_conversation = sample_conversation_data.copy()
    invalid_conversation["channel_method"] = "invalid_channel"
    invalid_conversation["conversation_status"] = "invalid_status"
    
    # Mock validate to return errors
    with patch('src.shared.database.models.Conversation.validate', return_value=["Invalid channel", "Invalid status"]):
        with pytest.raises(ValueError):
            mock_db_operations.create_conversation(Conversation(**invalid_conversation))
    
    # Test update non-existent conversation for WhatsApp
    non_existent = Conversation(**sample_conversation_data)
    non_existent.conversation_id = "non-existent"
    
    # Mock the get_item to return None (not found)
    with patch.object(mock_db_operations.dynamodb_client, 'get_item', return_value=None):
        with pytest.raises(ValueError):
            mock_db_operations.update_conversation(non_existent)
    
    # Test update non-existent conversation for Email
    non_existent_email = sample_conversation_data.copy()
    non_existent_email["channel_method"] = "email"
    non_existent_email["recipient_email"] = "nonexistent@example.com"
    non_existent_email["recipient_tel"] = "null"  # Use string "null" to avoid DynamoDB issues
    
    # Create a conversation with email channel
    email_convo = Conversation(**non_existent_email)
    
    # Mock the query_conversation_by_email to return None
    with patch.object(mock_db_operations, 'query_conversation_by_email', return_value=None):
        with pytest.raises(ValueError):
            mock_db_operations.update_conversation(email_convo)


@pytest.mark.unit
@pytest.mark.phase1
def test_add_message_error_handling(mock_db_operations, sample_conversation_data):
    """Test error handling when adding messages to conversations."""
    # For unit tests, we'll patch methods to simulate errors rather than actually creating items
    # Test adding a message to non-existent conversation
    non_existent_key = {
        "recipient_tel": "+9999999999",
        "conversation_id": "non-existent"
    }
    
    message = {
        "entry_id": "test-msg-1",
        "role": "user",
        "content": "Test message",
        "message_timestamp": datetime.now().isoformat()
    }
    
    # First we need to understand how the actual method handles missing conversations
    # Looking at the code, it returns False rather than raising ValueError
    # Let's test that behavior
    with patch.object(mock_db_operations.dynamodb_client, 'get_item', return_value=None):
        result = mock_db_operations.add_message_to_conversation(non_existent_key, message)
        assert result is False
    
    # Test adding invalid message with bad validation
    # Create a mock conversation
    mock_convo = {
        "conversation_id": "test-convo",
        "recipient_tel": "+1234567890",
        "messages": []
    }
    
    invalid_message = {
        "entry_id": "test-msg-2",
        "role": "invalid_role",
        "content": "Test message",
        "message_timestamp": datetime.now().isoformat()
    }
    
    # The Message class doesn't have a validate method, but we need to test error handling
    # when processing an invalid message. Let's simulate a failure when adding the message.
    with patch.object(mock_db_operations.dynamodb_client, 'get_item', return_value=mock_convo):
        # Simulate an error from DynamoDB update operation that would happen inside add_message_to_conversation
        with patch.object(mock_db_operations.dynamodb_client, 'update_item', side_effect=Exception("Invalid message")):
            with pytest.raises(Exception):
                mock_db_operations.add_message_to_conversation(
                    {"recipient_tel": "+1234567890", "conversation_id": "test-convo"},
                    invalid_message
                )


@pytest.mark.unit
@pytest.mark.phase1
def test_query_error_handling(mock_db_operations):
    """Test error handling in query operations."""
    # Test query with exceptions
    with patch.object(mock_db_operations.dynamodb_client, 'query', side_effect=Exception("Test exception")):
        with pytest.raises(Exception):
            mock_db_operations.query_conversations_by_company_project("test-company", "test-project")
        
        with pytest.raises(Exception):
            mock_db_operations.query_conversations_by_request_id("test-request")
        
        with pytest.raises(Exception):
            mock_db_operations.query_conversations_by_channel("whatsapp")
        
        with pytest.raises(Exception):
            mock_db_operations.query_conversation_by_email("test@example.com", "test-convo")
        
        with pytest.raises(Exception):
            mock_db_operations.query_conversation_by_message_id("test-message")


@pytest.mark.unit
@pytest.mark.phase1
def test_pagination_error_handling(mock_db_operations):
    """Test error handling in pagination operations."""
    # Looking at the implementation, DatabaseOperations.query_conversations_by_company_project
    # doesn't accept a pagination token parameter, so we can't test that directly
    
    # Instead, test that we get an error if the query response is malformed
    # Create a mock conversation with all required fields
    mock_conversation = {
        "conversation_id": "test-convo-1",
        "company_id": "test-company-1",
        "project_id": "test-project-1",
        "company_name": "Test Company",
        "project_name": "Test Project",
        "channel_method": "whatsapp",
        "request_id": "test-request-1",
        "router_version": "v1.0",
        "recipient_tel": "+1234567890",
        "messages": []
    }
    
    # Mock query to return a valid item
    with patch.object(mock_db_operations.dynamodb_client, 'query', 
                     return_value={"Items": [mock_conversation]}):
        # This should work fine
        result = mock_db_operations.query_conversations_by_company_project(
            "test-company-1", 
            "test-project-1",
            limit=1
        )
        assert len(result) == 1
        assert result[0].conversation_id == "test-convo-1"
    
    # Test with missing items in response
    with patch.object(mock_db_operations.dynamodb_client, 'query', 
                     return_value={}):  # Missing Items key
        result = mock_db_operations.query_conversations_by_company_project(
            "test-company-1", 
            "test-project-1"
        )
        # Should handle gracefully and return empty list
        assert len(result) == 0
    
    # Test with query returning invalid item (missing required fields)
    invalid_item = {"some_field": "some_value"}  # Missing required fields
    with patch.object(mock_db_operations.dynamodb_client, 'query', 
                     return_value={"Items": [invalid_item]}):
        with pytest.raises(TypeError):  # Should raise TypeError for missing required fields
            mock_db_operations.query_conversations_by_company_project(
                "test-company-1", 
                "test-project-1"
            ) 