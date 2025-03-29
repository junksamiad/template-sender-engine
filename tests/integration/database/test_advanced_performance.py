"""
Advanced performance tests for database operations.

This module provides comprehensive performance tests for database operations
under various load scenarios.
"""
import pytest
import time
import uuid
import random
from datetime import datetime, timezone
from typing import List, Dict, Any

from src.shared.database.models import WaCompanyData, Conversation, Message
from tests.fixtures.db_test_fixtures import (
    create_bulk_company_data,
    create_bulk_conversation_data,
)


def create_test_company_batch(count: int) -> List[Dict[str, Any]]:
    """Create a batch of test company data entries."""
    result = []
    company_id = f"perf-company-{uuid.uuid4().hex[:8]}"
    
    for i in range(count):
        result.append({
            "company_id": company_id,
            "project_id": f"perf-project-{i}",
            "company_name": f"Performance Test Company {company_id}",
            "project_name": f"Performance Test Project {i}",
            "project_status": "active",
            "allowed_channels": ["whatsapp", "email", "sms"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    
    return result


@pytest.mark.integration
@pytest.mark.phase1
@pytest.mark.slow
def test_performance_read_write_ratio(integration_db_operations):
    """Test performance of read/write operations under different ratios."""
    # Create test data setup
    company_id = f"ratio-company-{uuid.uuid4().hex[:8]}"
    project_id = f"ratio-project-{uuid.uuid4().hex[:8]}"
    conversation_count = 20
    
    # Create base company data
    company_data = {
        "company_id": company_id,
        "project_id": project_id,
        "company_name": f"Ratio Test Company {company_id}",
        "project_name": f"Ratio Test Project {project_id}",
        "project_status": "active",
        "allowed_channels": ["whatsapp", "email", "sms"],
    }
    integration_db_operations.create_company_data(WaCompanyData(**company_data))
    
    # Create base conversations
    conversations = []
    for i in range(conversation_count):
        conversation_data = {
            "conversation_id": f"ratio-convo-{i}",
            "company_id": company_id,
            "project_id": project_id,
            "company_name": f"Ratio Test Company {company_id}",
            "project_name": f"Ratio Test Project {project_id}",
            "channel_method": "whatsapp",
            "request_id": f"ratio-request-{i}",
            "conversation_status": "processing",
            "recipient_tel": f"+1{i:010d}",
            "messages": [
                {
                    "entry_id": "initial-msg",
                    "role": "system",
                    "content": "Initial system message",
                    "message_timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        conversation = Conversation(**conversation_data)
        integration_db_operations.create_conversation(conversation)
        conversations.append(conversation)
    
    print("\n=== READ/WRITE RATIO PERFORMANCE TEST ===")
    
    # Test high write ratio (70% writes, 30% reads)
    total_ops = 100
    write_ratio = 0.7
    write_count = int(total_ops * write_ratio)
    read_count = total_ops - write_count
    
    start_time = time.time()
    
    # Perform operations
    for i in range(total_ops):
        if i < write_count:
            # Write operation - add message to random conversation
            convo_idx = random.randint(0, conversation_count - 1)
            convo = conversations[convo_idx]
            primary_key = {"recipient_tel": convo.recipient_tel, "conversation_id": convo.conversation_id}
            
            message = {
                "entry_id": f"ratio-high-write-msg-{i}",
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"High write ratio message {i}",
                "message_timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            integration_db_operations.add_message_to_conversation(primary_key, message)
        else:
            # Read operation - get random conversation
            convo_idx = random.randint(0, conversation_count - 1)
            convo = conversations[convo_idx]
            primary_key = {"recipient_tel": convo.recipient_tel, "conversation_id": convo.conversation_id}
            
            integration_db_operations.get_conversation(primary_key)
    
    high_write_time = time.time() - start_time
    print(f"High write ratio ({write_ratio:.0%} writes): {high_write_time:.4f} seconds")
    print(f"Average time per operation: {high_write_time/total_ops:.4f} seconds")
    
    # Test balanced ratio (50% writes, 50% reads)
    write_ratio = 0.5
    write_count = int(total_ops * write_ratio)
    read_count = total_ops - write_count
    
    start_time = time.time()
    
    # Perform operations
    for i in range(total_ops):
        if i < write_count:
            # Write operation - add message to random conversation
            convo_idx = random.randint(0, conversation_count - 1)
            convo = conversations[convo_idx]
            primary_key = {"recipient_tel": convo.recipient_tel, "conversation_id": convo.conversation_id}
            
            message = {
                "entry_id": f"ratio-balanced-msg-{i}",
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Balanced ratio message {i}",
                "message_timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            integration_db_operations.add_message_to_conversation(primary_key, message)
        else:
            # Read operation - get random conversation
            convo_idx = random.randint(0, conversation_count - 1)
            convo = conversations[convo_idx]
            primary_key = {"recipient_tel": convo.recipient_tel, "conversation_id": convo.conversation_id}
            
            integration_db_operations.get_conversation(primary_key)
    
    balanced_time = time.time() - start_time
    print(f"Balanced ratio ({write_ratio:.0%} writes): {balanced_time:.4f} seconds")
    print(f"Average time per operation: {balanced_time/total_ops:.4f} seconds")
    
    # Test high read ratio (30% writes, 70% reads)
    write_ratio = 0.3
    write_count = int(total_ops * write_ratio)
    read_count = total_ops - write_count
    
    start_time = time.time()
    
    # Perform operations
    for i in range(total_ops):
        if i < write_count:
            # Write operation - add message to random conversation
            convo_idx = random.randint(0, conversation_count - 1)
            convo = conversations[convo_idx]
            primary_key = {"recipient_tel": convo.recipient_tel, "conversation_id": convo.conversation_id}
            
            message = {
                "entry_id": f"ratio-high-read-msg-{i}",
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"High read ratio message {i}",
                "message_timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            integration_db_operations.add_message_to_conversation(primary_key, message)
        else:
            # Read operation - get random conversation
            convo_idx = random.randint(0, conversation_count - 1)
            convo = conversations[convo_idx]
            primary_key = {"recipient_tel": convo.recipient_tel, "conversation_id": convo.conversation_id}
            
            integration_db_operations.get_conversation(primary_key)
    
    high_read_time = time.time() - start_time
    print(f"High read ratio ({1-write_ratio:.0%} reads): {high_read_time:.4f} seconds")
    print(f"Average time per operation: {high_read_time/total_ops:.4f} seconds")
    
    # Clean up
    for convo in conversations:
        integration_db_operations.delete_conversation({
            "recipient_tel": convo.recipient_tel,
            "conversation_id": convo.conversation_id
        })
    
    integration_db_operations.delete_company_data(company_id, project_id)


@pytest.mark.integration
@pytest.mark.phase1
@pytest.mark.slow
def test_batch_operations_performance(integration_db_operations):
    """Test performance of batch operations with DynamoDB."""
    print("\n=== BATCH OPERATIONS PERFORMANCE TEST ===")
    
    # Test batch write performance with increasing batch sizes
    batch_sizes = [5, 10, 25, 50]
    
    for batch_size in batch_sizes:
        # Create test data batch
        test_data = create_test_company_batch(batch_size)
        start_time = time.time()
        
        # Create items one by one (no batching)
        for item in test_data:
            integration_db_operations.create_company_data(WaCompanyData(**item))
        
        single_time = time.time() - start_time
        print(f"Individual writes ({batch_size} items): {single_time:.4f} seconds")
        print(f"Average time per item: {single_time/batch_size:.4f} seconds")
        
        # Clean up
        company_id = test_data[0]["company_id"]
        for item in test_data:
            integration_db_operations.delete_company_data(company_id, item["project_id"])


@pytest.mark.integration
@pytest.mark.phase1
@pytest.mark.slow
def test_query_filter_performance(integration_db_operations):
    """Test performance of queries with different filter complexities."""
    print("\n=== QUERY FILTER PERFORMANCE TEST ===")
    
    # Create bulk test data
    company_id = f"filter-company-{uuid.uuid4().hex[:8]}"
    project_id = f"filter-project-{uuid.uuid4().hex[:8]}"
    conversation_count = 50
    
    # Create conversations with varying statuses and timestamps
    statuses = ["initiated", "processing", "completed", "failed"]
    
    for i in range(conversation_count):
        conversation_data = {
            "conversation_id": f"filter-convo-{i}",
            "company_id": company_id,
            "project_id": project_id,
            "company_name": f"Filter Test Company",
            "project_name": f"Filter Test Project",
            "channel_method": "whatsapp",
            "request_id": f"filter-request-{i}",
            "conversation_status": statuses[i % len(statuses)],
            "recipient_tel": f"+1{i:010d}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "messages": [
                {
                    "entry_id": "initial-msg",
                    "role": "system",
                    "content": "Initial system message",
                    "message_timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        integration_db_operations.create_conversation(Conversation(**conversation_data))
    
    # Test simple query (no filters)
    start_time = time.time()
    results = integration_db_operations.query_conversations_by_company_project(company_id, project_id)
    simple_time = time.time() - start_time
    
    assert len(results) == conversation_count
    print(f"Simple query (no filters): {simple_time:.4f} seconds")
    
    # Test query with status filter
    from src.shared.database.query_utils import build_channel_status_condition
    
    for status in statuses:
        # Use the database client directly to query with filter
        condition = build_channel_status_condition("conversation_status", status)
        
        start_time = time.time()
        response = integration_db_operations.dynamodb_client.query(
            table_name=integration_db_operations.conversations_table,
            index_name="CompanyProjectIndex",
            key_condition_expression="company_id = :company_id AND project_id = :project_id",
            filter_expression=condition.expression,
            expression_attribute_values={
                ":company_id": company_id,
                ":project_id": project_id,
                **condition.values
            }
        )
        filter_time = time.time() - start_time
        
        items = response.get("Items", [])
        print(f"Filtered query (status={status}): {filter_time:.4f} seconds, {len(items)} results")
    
    # Clean up
    all_conversations = integration_db_operations.query_conversations_by_company_project(company_id, project_id)
    for convo in all_conversations:
        integration_db_operations.delete_conversation({
            "recipient_tel": convo.recipient_tel,
            "conversation_id": convo.conversation_id
        })


@pytest.mark.integration
@pytest.mark.phase1
@pytest.mark.slow
def test_cross_channel_performance(integration_db_operations):
    """Test performance across different communication channels."""
    print("\n=== CROSS-CHANNEL PERFORMANCE TEST ===")
    
    # Create bulk conversation data for different channels
    channels = ["whatsapp", "email", "sms"]
    company_count = 2
    conversations_per_company = 10
    
    # Create test data
    bulk_data = create_bulk_conversation_data(
        company_count=company_count,
        conversations_per_company=conversations_per_company,
        channels=channels
    )
    
    # Insert test data
    for data in bulk_data:
        integration_db_operations.create_conversation(Conversation(**data))
    
    # Test query performance by channel
    for channel in channels:
        start_time = time.time()
        results = integration_db_operations.query_conversations_by_channel(channel)
        channel_time = time.time() - start_time
        
        expected_count = (company_count * conversations_per_company) // len(channels)
        assert len(results) >= expected_count
        
        print(f"Channel query ({channel}): {channel_time:.4f} seconds, {len(results)} results")
    
    # Clean up - this is more complex as we need to handle different channels
    for data in bulk_data:
        try:
            if data["channel_method"] in ["whatsapp", "sms"]:
                integration_db_operations.delete_conversation({
                    "recipient_tel": data["recipient_tel"],
                    "conversation_id": data["conversation_id"]
                })
            elif data["channel_method"] == "email":
                result = integration_db_operations.query_conversation_by_email(
                    data["recipient_email"],
                    data["conversation_id"]
                )
                if result:
                    integration_db_operations.delete_conversation({
                        "recipient_tel": result.recipient_tel or "null",
                        "conversation_id": data["conversation_id"]
                    })
        except Exception as e:
            print(f"Error cleaning up conversation {data['conversation_id']}: {str(e)}")
            # Continue with other deletions 