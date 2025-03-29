"""
Integration tests for database edge cases.

This module provides integration tests for database edge cases and scenarios.
"""
import pytest
import time
import uuid
from datetime import datetime, timezone

from src.shared.database.models import WaCompanyData, Conversation, Message


@pytest.mark.integration
@pytest.mark.phase1
def test_large_item_handling(integration_db_operations):
    """Test handling of large items in DynamoDB."""
    # Create a company data item with a large number of templates
    company_id = f"large-company-{uuid.uuid4().hex[:8]}"
    project_id = f"large-project-{uuid.uuid4().hex[:8]}"
    
    # Generate a large number of templates
    templates = [f"template-{i}" for i in range(100)]
    
    company_data = {
        "company_id": company_id,
        "project_id": project_id,
        "company_name": "Large Template Company",
        "project_name": "Large Template Project",
        "project_status": "active",
        "allowed_channels": ["whatsapp", "email"],
        "channel_config": {
            "whatsapp": {
                "template_ids": templates,
                "credentials_reference": f"secret/whatsapp/{company_id}",
            }
        },
    }
    
    # Create the company data
    company = WaCompanyData(**company_data)
    result = integration_db_operations.create_company_data(company)
    
    # Verify it was saved correctly
    retrieved = integration_db_operations.get_company_data(company_id, project_id)
    assert retrieved is not None
    assert len(retrieved.channel_config.get("whatsapp", {}).get("template_ids", [])) == 100
    
    # Clean up
    integration_db_operations.delete_company_data(company_id, project_id)


@pytest.mark.integration
@pytest.mark.phase1
def test_large_conversation_messages(integration_db_operations):
    """Test handling of conversations with many messages."""
    # Create a conversation with a large number of messages
    conversation_id = f"large-convo-{uuid.uuid4().hex[:8]}"
    recipient_tel = "+9876543210"
    
    # Create base conversation
    conversation_data = {
        "conversation_id": conversation_id,
        "company_id": "large-company",
        "project_id": "large-project",
        "company_name": "Large Message Company",
        "project_name": "Large Message Project",
        "channel_method": "whatsapp",
        "request_id": f"large-request-{uuid.uuid4().hex[:8]}",
        "conversation_status": "processing",
        "recipient_tel": recipient_tel,
        "messages": [
            {
                "entry_id": "initial-msg",
                "role": "system",
                "content": "Initial system message",
                "message_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }
    
    # Create the conversation
    conversation = Conversation(**conversation_data)
    result = integration_db_operations.create_conversation(conversation)
    
    # Add a large number of messages
    primary_key = {"recipient_tel": recipient_tel, "conversation_id": conversation_id}
    message_count = 50
    start_time = time.time()
    
    for i in range(message_count):
        message = {
            "entry_id": f"large-msg-{i}",
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"Message {i} with some content that has reasonable length to simulate real messages",
            "message_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        integration_db_operations.add_message_to_conversation(primary_key, message)
    
    add_time = time.time() - start_time
    print(f"\nTime to add {message_count} messages: {add_time:.4f} seconds")
    print(f"Average time per message: {add_time/message_count:.4f} seconds")
    
    # Now retrieve the conversation and check performance
    start_time = time.time()
    retrieved = integration_db_operations.get_conversation(primary_key)
    retrieve_time = time.time() - start_time
    
    assert retrieved is not None
    assert len(retrieved.messages) == message_count + 1  # Including the initial message
    
    print(f"Time to retrieve conversation with {len(retrieved.messages)} messages: {retrieve_time:.4f} seconds")
    
    # Clean up
    integration_db_operations.delete_conversation(primary_key)


@pytest.mark.integration
@pytest.mark.phase1
def test_concurrent_updates(integration_db_operations):
    """Test handling of concurrent updates to the same item."""
    # Create a conversation for testing concurrent updates
    conversation_id = f"concurrent-convo-{uuid.uuid4().hex[:8]}"
    recipient_tel = "+1234567890"
    
    conversation_data = {
        "conversation_id": conversation_id,
        "company_id": "concurrent-company",
        "project_id": "concurrent-project",
        "company_name": "Concurrent Test Company",
        "project_name": "Concurrent Test Project",
        "channel_method": "whatsapp",
        "request_id": f"concurrent-request-{uuid.uuid4().hex[:8]}",
        "conversation_status": "processing",
        "recipient_tel": recipient_tel,
        "messages": [
            {
                "entry_id": "initial-msg",
                "role": "system",
                "content": "Initial system message",
                "message_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }
    
    # Create the conversation
    conversation = Conversation(**conversation_data)
    result = integration_db_operations.create_conversation(conversation)
    
    # Update different aspects of the conversation concurrently
    primary_key = {"recipient_tel": recipient_tel, "conversation_id": conversation_id}
    
    # Update status
    integration_db_operations.update_conversation_status(primary_key, "completed")
    
    # Add a message
    message = {
        "entry_id": "concurrent-msg-1",
        "role": "user",
        "content": "Concurrent message 1",
        "message_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    integration_db_operations.add_message_to_conversation(primary_key, message)
    
    # Update metadata
    retrieved = integration_db_operations.get_conversation(primary_key)
    retrieved.recipient_first_name = "Updated"
    retrieved.recipient_last_name = "Name"
    integration_db_operations.update_conversation(retrieved)
    
    # Verify final state
    final = integration_db_operations.get_conversation(primary_key)
    assert final is not None
    assert final.conversation_status == "completed"
    assert len(final.messages) == 2  # Initial + new message
    assert final.recipient_first_name == "Updated"
    assert final.recipient_last_name == "Name"
    
    # Clean up
    integration_db_operations.delete_conversation(primary_key)


@pytest.mark.integration
@pytest.mark.phase1
def test_query_pagination(integration_db_operations):
    """Test pagination of query results."""
    # Create a set of conversations for the same company/project
    company_id = f"pagination-company-{uuid.uuid4().hex[:8]}"
    project_id = f"pagination-project-{uuid.uuid4().hex[:8]}"
    
    # Create 25 conversations (more than default page size)
    for i in range(25):
        conversation_data = {
            "conversation_id": f"pagination-convo-{i}",
            "company_id": company_id,
            "project_id": project_id,
            "company_name": "Pagination Test Company",
            "project_name": "Pagination Test Project",
            "channel_method": "whatsapp" if i % 2 == 0 else "email",
            "request_id": f"pagination-request-{i}",
            "conversation_status": "processing",
            "recipient_tel": f"+98765{i:05d}" if i % 2 == 0 else None,
            "recipient_email": f"pagination-{i}@example.com" if i % 2 == 1 else None,
            "messages": [
                {
                    "entry_id": "initial-msg",
                    "role": "system",
                    "content": f"Initial message for conversation {i}",
                    "message_timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        integration_db_operations.create_conversation(Conversation(**conversation_data))
    
    # Query with pagination - first page
    start_time = time.time()
    page1 = integration_db_operations.query_conversations_by_company_project(
        company_id, project_id, limit=10
    )
    page1_time = time.time() - start_time
    
    assert len(page1) == 10
    assert hasattr(page1, "pagination_token")
    assert page1.pagination_token is not None
    
    print(f"\nTime to query first page (10 items): {page1_time:.4f} seconds")
    
    # Get second page
    start_time = time.time()
    page2 = integration_db_operations.query_conversations_by_company_project(
        company_id, project_id, limit=10, last_evaluated_key=page1.pagination_token
    )
    page2_time = time.time() - start_time
    
    assert len(page2) == 10
    assert hasattr(page2, "pagination_token")
    assert page2.pagination_token is not None
    
    print(f"Time to query second page (10 items): {page2_time:.4f} seconds")
    
    # Get third (final) page
    start_time = time.time()
    page3 = integration_db_operations.query_conversations_by_company_project(
        company_id, project_id, limit=10, last_evaluated_key=page2.pagination_token
    )
    page3_time = time.time() - start_time
    
    assert len(page3) == 5  # Only 5 items left
    assert not hasattr(page3, "pagination_token") or page3.pagination_token is None
    
    print(f"Time to query third page (5 items): {page3_time:.4f} seconds")
    
    # Get all items without pagination
    start_time = time.time()
    all_items = integration_db_operations.query_conversations_by_company_project(
        company_id, project_id
    )
    all_time = time.time() - start_time
    
    assert len(all_items) == 25
    
    print(f"Time to query all 25 items at once: {all_time:.4f} seconds")
    
    # Clean up - delete all conversations
    for i in range(25):
        if i % 2 == 0:  # WhatsApp
            integration_db_operations.delete_conversation({
                "recipient_tel": f"+98765{i:05d}",
                "conversation_id": f"pagination-convo-{i}"
            })
        else:  # Email
            # For email, we need to get the conversation first to get recipient_tel
            result = integration_db_operations.query_conversation_by_email(
                f"pagination-{i}@example.com", f"pagination-convo-{i}"
            )
            if result:
                integration_db_operations.delete_conversation({
                    "recipient_tel": result.recipient_tel or "null",
                    "conversation_id": f"pagination-convo-{i}"
                })


@pytest.mark.integration
@pytest.mark.phase1
def test_channel_specific_queries(integration_db_operations):
    """Test channel-specific query patterns."""
    from src.shared.database.query_utils import build_channel_status_condition
    
    # Create test data with different channels and statuses
    company_id = f"channel-company-{uuid.uuid4().hex[:8]}"
    
    channels = ["whatsapp", "email", "sms"]
    statuses = ["processing", "completed", "failed"]
    
    # Create 9 conversations (3 channels x 3 statuses)
    for c_idx, channel in enumerate(channels):
        for s_idx, status in enumerate(statuses):
            conversation_data = {
                "conversation_id": f"channel-convo-{channel}-{status}",
                "company_id": company_id,
                "project_id": "channel-project",
                "company_name": "Channel Test Company",
                "project_name": "Channel Test Project",
                "channel_method": channel,
                "conversation_status": status,
                "request_id": f"channel-request-{channel}-{status}",
            }
            
            # Channel-specific fields
            if channel == "whatsapp" or channel == "sms":
                zeros = "0" * 8
                conversation_data["recipient_tel"] = f"+{c_idx}{s_idx}{zeros}"
            elif channel == "email":
                conversation_data["recipient_email"] = f"channel-{status}@example.com"
                conversation_data["recipient_tel"] = "null"  # Required for the key
            
            integration_db_operations.create_conversation(Conversation(**conversation_data))
    
    # Test queries by channel
    for channel in channels:
        results = integration_db_operations.query_conversations_by_channel(channel)
        assert len(results) == 3  # 3 statuses per channel
        
    # Test queries by status
    for status in statuses:
        # Use the database client directly to query using the built condition
        condition = build_channel_status_condition("conversation_status", status)
        
        response = integration_db_operations.dynamodb_client.query(
            table_name=integration_db_operations.conversations_table,
            index_name="ChannelIndex",
            key_condition_expression="channel_method = :channel",
            filter_expression=condition.expression,
            expression_attribute_values={
                **{":channel": "whatsapp"},
                **condition.values
            }
        )
        
        # Should find 1 item per status for whatsapp
        items = response.get("Items", [])
        assert len(items) == 1
    
    # Test combined queries (channel + status)
    for channel in channels:
        for status in statuses:
            # Use the database client directly to query using the built condition
            condition = build_channel_status_condition("conversation_status", status)
            
            response = integration_db_operations.dynamodb_client.query(
                table_name=integration_db_operations.conversations_table,
                index_name="ChannelIndex",
                key_condition_expression="channel_method = :channel",
                filter_expression=condition.expression,
                expression_attribute_values={
                    **{":channel": channel},
                    **condition.values
                }
            )
            
            # Should find 1 item per channel+status combination
            items = response.get("Items", [])
            assert len(items) == 1
    
    # Clean up
    for channel in channels:
        for status in statuses:
            if channel == "whatsapp" or channel == "sms":
                c_idx = channels.index(channel)
                s_idx = statuses.index(status)
                zeros = "0" * 8
                tel = f"+{c_idx}{s_idx}{zeros}"
                
                integration_db_operations.delete_conversation({
                    "recipient_tel": tel,
                    "conversation_id": f"channel-convo-{channel}-{status}"
                })
            elif channel == "email":
                # For email, we need to delete via email query
                result = integration_db_operations.query_conversation_by_email(
                    f"channel-{status}@example.com", 
                    f"channel-convo-{channel}-{status}"
                )
                if result:
                    integration_db_operations.delete_conversation({
                        "recipient_tel": result.recipient_tel or "null",
                        "conversation_id": f"channel-convo-{channel}-{status}"
                    }) 