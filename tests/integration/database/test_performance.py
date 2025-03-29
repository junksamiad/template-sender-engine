"""
Performance tests for database operations.

This module provides performance benchmarks for database operations.
"""
import pytest
import time
import uuid
from datetime import datetime

from src.shared.database.models import WaCompanyData, Conversation


@pytest.mark.integration
@pytest.mark.phase1
@pytest.mark.slow
def test_bulk_writes_performance(integration_db_operations, integration_sample_company_data):
    """Test performance of bulk write operations."""
    # Generate a unique company ID for this test
    company_id = f"perf-company-{uuid.uuid4().hex[:8]}"
    
    # Create test data
    start_time = time.time()
    num_projects = 10
    
    for i in range(num_projects):
        project_data = integration_sample_company_data.copy()
        project_data["company_id"] = company_id
        project_data["project_id"] = f"perf-project-{i}"
        project_data["project_name"] = f"Performance Test Project {i}"
        
        integration_db_operations.create_company_data(WaCompanyData(**project_data))
    
    write_time = time.time() - start_time
    print(f"\nBulk write performance ({num_projects} projects): {write_time:.4f} seconds")
    print(f"Average time per write: {write_time/num_projects:.4f} seconds")
    
    # Read all projects
    start_time = time.time()
    projects = integration_db_operations.list_company_projects(company_id)
    read_time = time.time() - start_time
    
    assert len(projects) == num_projects
    print(f"Bulk read performance ({num_projects} projects): {read_time:.4f} seconds")
    
    # Clean up
    for i in range(num_projects):
        integration_db_operations.delete_company_data(company_id, f"perf-project-{i}")


@pytest.mark.integration
@pytest.mark.phase1
@pytest.mark.slow
def test_query_performance(integration_db_operations, integration_sample_conversation_data):
    """Test performance of query operations."""
    # Generate unique IDs for this test
    company_id = f"perf-company-{uuid.uuid4().hex[:8]}"
    num_conversations = 20
    conversations = []
    
    # Create test conversations
    start_time = time.time()
    
    for i in range(num_conversations):
        convo_data = integration_sample_conversation_data.copy()
        convo_data["company_id"] = company_id
        convo_data["project_id"] = "perf-project"
        convo_data["conversation_id"] = f"perf-convo-{i}"
        convo_data["recipient_tel"] = f"+1234567{i:03d}"
        convo_data["request_id"] = f"perf-request-{i}"
        convo_data["channel_method"] = "whatsapp" if i % 2 == 0 else "email"
        
        if convo_data["channel_method"] == "email":
            convo_data["recipient_email"] = f"perf-test-{i}@example.com"
        
        conversation = Conversation(**convo_data)
        integration_db_operations.create_conversation(conversation)
        conversations.append(conversation)
    
    write_time = time.time() - start_time
    print(f"\nBulk conversation write ({num_conversations} items): {write_time:.4f} seconds")
    print(f"Average time per conversation write: {write_time/num_conversations:.4f} seconds")
    
    # Test query by company/project performance
    start_time = time.time()
    results = integration_db_operations.query_conversations_by_company_project(
        company_id, "perf-project"
    )
    query_time = time.time() - start_time
    
    assert len(results) == num_conversations
    print(f"Company/project query performance ({num_conversations} results): {query_time:.4f} seconds")
    
    # Test query by channel performance
    start_time = time.time()
    results = integration_db_operations.query_conversations_by_channel("whatsapp")
    channel_query_time = time.time() - start_time
    
    assert len(results) >= num_conversations / 2  # At least half should be WhatsApp
    print(f"Channel query performance: {channel_query_time:.4f} seconds")
    
    # Test query by status performance
    start_time = time.time()
    results = integration_db_operations.query_conversations_by_status("processing")
    status_query_time = time.time() - start_time
    
    print(f"Status query performance: {status_query_time:.4f} seconds")
    
    # Clean up
    for conversation in conversations:
        if conversation.channel_method == "whatsapp":
            integration_db_operations.delete_conversation({
                "recipient_tel": conversation.recipient_tel,
                "conversation_id": conversation.conversation_id
            })


@pytest.mark.integration
@pytest.mark.phase1
@pytest.mark.slow
def test_message_append_performance(integration_db_operations, integration_sample_conversation_data):
    """Test performance of appending messages to a conversation."""
    # Create a conversation for testing
    convo_data = integration_sample_conversation_data.copy()
    convo_data["company_id"] = f"msg-perf-company-{uuid.uuid4().hex[:8]}"
    convo_data["conversation_id"] = f"msg-perf-convo-{uuid.uuid4().hex[:8]}"
    convo_data["recipient_tel"] = "+9999999999"
    
    conversation = Conversation(**convo_data)
    integration_db_operations.create_conversation(conversation)
    
    # Test adding messages
    num_messages = 20
    primary_key = {
        "recipient_tel": "+9999999999", 
        "conversation_id": convo_data["conversation_id"]
    }
    
    start_time = time.time()
    
    for i in range(num_messages):
        message = {
            "entry_id": f"perf-msg-{i}",
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"Performance test message {i}",
            "message_timestamp": datetime.now().isoformat(),
            "ai_prompt_tokens": 10,
            "ai_completion_tokens": 20,
        }
        
        integration_db_operations.add_message_to_conversation(primary_key, message)
    
    append_time = time.time() - start_time
    print(f"\nMessage append performance ({num_messages} messages): {append_time:.4f} seconds")
    print(f"Average time per message append: {append_time/num_messages:.4f} seconds")
    
    # Verify all messages were added
    retrieved = integration_db_operations.get_conversation(primary_key)
    assert len(retrieved.messages) == num_messages + 1  # +1 for the initial message
    
    # Test read performance with a large conversation
    start_time = time.time()
    retrieved = integration_db_operations.get_conversation(primary_key)
    read_time = time.time() - start_time
    
    print(f"Large conversation read performance ({len(retrieved.messages)} messages): {read_time:.4f} seconds")
    
    # Clean up
    integration_db_operations.delete_conversation(primary_key) 