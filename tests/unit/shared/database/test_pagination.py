"""
Tests for the pagination helper.

This module provides unit tests for the PaginationHelper class.
"""
import pytest
from unittest.mock import patch, MagicMock

from src.shared.database.pagination import PaginationHelper
from src.shared.database.models import Conversation


@pytest.mark.unit
@pytest.mark.phase1
def test_init_pagination_helper():
    """Test initializing the PaginationHelper class."""
    # Test default initialization
    helper = PaginationHelper()
    assert helper.item_transformer is not None
    
    # Test with custom transformer
    def custom_transformer(item):
        return {"transformed": item}
        
    helper = PaginationHelper(item_transformer=custom_transformer)
    assert helper.item_transformer is custom_transformer
    
    # Test the transform function
    item = {"key": "value"}
    transformed = helper.item_transformer(item)
    assert transformed == {"transformed": item}


@pytest.mark.unit
@pytest.mark.phase1
def test_paginate_query():
    """Test paginating a query."""
    mock_client = MagicMock()
    
    # First query response with a LastEvaluatedKey
    first_response = {
        "Items": [
            {"id": "1", "name": "Item 1"},
            {"id": "2", "name": "Item 2"},
        ],
        "LastEvaluatedKey": {"id": "2"},
    }
    
    # Second query response with no LastEvaluatedKey (last page)
    second_response = {
        "Items": [
            {"id": "3", "name": "Item 3"},
            {"id": "4", "name": "Item 4"},
        ],
    }
    
    # Set up the mock to return the responses in sequence
    mock_client.query = MagicMock(side_effect=[first_response, second_response])
    
    # Create the pagination helper
    helper = PaginationHelper(dynamodb_client=mock_client)
    
    # Paginate through all items
    query_params = {
        "table_name": "test-table",
        "key_condition_expression": "id > :id",
        "expression_attribute_values": {":id": "0"},
    }
    
    all_items = list(helper.paginate_query(**query_params))
    
    # Verify the results
    assert len(all_items) == 4
    assert all_items[0]["id"] == "1"
    assert all_items[1]["id"] == "2"
    assert all_items[2]["id"] == "3"
    assert all_items[3]["id"] == "4"
    
    # Verify query was called twice with correct parameters
    assert mock_client.query.call_count == 2
    
    # First call should have original params
    args, kwargs = mock_client.query.call_args_list[0]
    assert kwargs["table_name"] == "test-table"
    assert kwargs["key_condition_expression"] == "id > :id"
    assert kwargs["expression_attribute_values"] == {":id": "0"}
    
    # Second call should include LastEvaluatedKey from first response
    args, kwargs = mock_client.query.call_args_list[1]
    assert kwargs["table_name"] == "test-table"
    assert kwargs["key_condition_expression"] == "id > :id"
    assert kwargs["expression_attribute_values"] == {":id": "0"}
    assert kwargs["exclusive_start_key"] == {"id": "2"}


@pytest.mark.unit
@pytest.mark.phase1
def test_paginate_scan():
    """Test paginating a scan."""
    mock_client = MagicMock()
    
    # First scan response with a LastEvaluatedKey
    first_response = {
        "Items": [
            {"id": "1", "name": "Item 1"},
            {"id": "2", "name": "Item 2"},
        ],
        "LastEvaluatedKey": {"id": "2"},
    }
    
    # Second scan response with no LastEvaluatedKey (last page)
    second_response = {
        "Items": [
            {"id": "3", "name": "Item 3"},
            {"id": "4", "name": "Item 4"},
        ],
    }
    
    # Set up the mock to return the responses in sequence
    mock_client.scan = MagicMock(side_effect=[first_response, second_response])
    
    # Create the pagination helper
    helper = PaginationHelper(dynamodb_client=mock_client)
    
    # Paginate through all items
    scan_params = {
        "table_name": "test-table",
        "filter_expression": "active = :active",
        "expression_attribute_values": {":active": True},
    }
    
    all_items = list(helper.paginate_scan(**scan_params))
    
    # Verify the results
    assert len(all_items) == 4
    assert all_items[0]["id"] == "1"
    assert all_items[1]["id"] == "2"
    assert all_items[2]["id"] == "3"
    assert all_items[3]["id"] == "4"
    
    # Verify scan was called twice with correct parameters
    assert mock_client.scan.call_count == 2
    
    # First call should have original params
    args, kwargs = mock_client.scan.call_args_list[0]
    assert kwargs["table_name"] == "test-table"
    assert kwargs["filter_expression"] == "active = :active"
    assert kwargs["expression_attribute_values"] == {":active": True}
    
    # Second call should include LastEvaluatedKey from first response
    args, kwargs = mock_client.scan.call_args_list[1]
    assert kwargs["table_name"] == "test-table"
    assert kwargs["filter_expression"] == "active = :active"
    assert kwargs["expression_attribute_values"] == {":active": True}
    assert kwargs["exclusive_start_key"] == {"id": "2"}


@pytest.mark.unit
@pytest.mark.phase1
def test_paginate_with_transformer():
    """Test pagination with a custom transformer."""
    mock_client = MagicMock()
    
    # Query response with items that include all required fields for Conversation
    response = {
        "Items": [
            {
                "conversation_id": "test-convo-1",
                "company_id": "test-company-1",
                "project_id": "test-project-1",
                "company_name": "Test Company",
                "project_name": "Test Project",
                "channel_method": "whatsapp",
                "request_id": "test-request-1",
                "router_version": "v1.0",
                "recipient_tel": "+1234567890",
                "recipient_email": "test@example.com",
                "message_id": "msg-123",
            },
        ],
    }
    
    # Set up the mock
    mock_client.query = MagicMock(return_value=response)
    
    # Create a transformer that converts DynamoDB items to Conversation objects
    def conversation_transformer(item):
        return Conversation(**item)
    
    # Create the pagination helper with the transformer
    helper = PaginationHelper(
        dynamodb_client=mock_client,
        item_transformer=conversation_transformer
    )
    
    # Paginate through items
    query_params = {
        "table_name": "conversations-test",
        "key_condition_expression": "company_id = :company_id",
        "expression_attribute_values": {":company_id": "test-company-1"},
    }
    
    all_items = list(helper.paginate_query(**query_params))
    
    # Verify the results
    assert len(all_items) == 1
    assert isinstance(all_items[0], Conversation)
    assert all_items[0].conversation_id == "test-convo-1"
    assert all_items[0].company_id == "test-company-1"


@pytest.mark.unit
@pytest.mark.phase1
def test_paginate_with_limit():
    """Test pagination with a limit."""
    mock_client = MagicMock()
    
    # Query responses
    first_response = {
        "Items": [
            {"id": "1", "name": "Item 1"},
            {"id": "2", "name": "Item 2"},
        ],
        "LastEvaluatedKey": {"id": "2"},
    }
    
    second_response = {
        "Items": [
            {"id": "3", "name": "Item 3"},
        ],
    }
    
    # Set up the mock
    mock_client.query = MagicMock(side_effect=[first_response, second_response])
    
    # Create the pagination helper
    helper = PaginationHelper(dynamodb_client=mock_client)
    
    # Paginate with a limit
    query_params = {
        "table_name": "test-table",
        "key_condition_expression": "id > :id",
        "expression_attribute_values": {":id": "0"},
    }
    
    # Get only 3 items (across the two pages)
    all_items = list(helper.paginate_query(max_items=3, **query_params))
    
    # Verify the results
    assert len(all_items) == 3
    assert all_items[0]["id"] == "1"
    assert all_items[1]["id"] == "2"
    assert all_items[2]["id"] == "3"
    
    # Verify query was called twice
    assert mock_client.query.call_count == 2


@pytest.mark.unit
@pytest.mark.phase1
def test_paginate_empty_response():
    """Test pagination with an empty response."""
    mock_client = MagicMock()
    
    # Empty response
    empty_response = {
        "Items": [],
    }
    
    # Set up the mock
    mock_client.query = MagicMock(return_value=empty_response)
    
    # Create the pagination helper
    helper = PaginationHelper(dynamodb_client=mock_client)
    
    # Paginate
    query_params = {
        "table_name": "test-table",
        "key_condition_expression": "id > :id",
        "expression_attribute_values": {":id": "999"},  # No matching items
    }
    
    all_items = list(helper.paginate_query(**query_params))
    
    # Verify the results
    assert len(all_items) == 0
    
    # Verify query was called once
    assert mock_client.query.call_count == 1


@pytest.mark.unit
@pytest.mark.phase1
def test_get_page():
    """Test get_page method for manual pagination."""
    mock_client = MagicMock()
    
    # First page response
    first_response = {
        "Items": [
            {"id": "1", "name": "Item 1"},
            {"id": "2", "name": "Item 2"},
        ],
        "LastEvaluatedKey": {"id": "2"},
    }
    
    # Second page response
    second_response = {
        "Items": [
            {"id": "3", "name": "Item 3"},
            {"id": "4", "name": "Item 4"},
        ],
    }
    
    # Set up the mock
    mock_client.query = MagicMock(side_effect=[first_response, second_response])
    
    # Create the pagination helper
    helper = PaginationHelper(dynamodb_client=mock_client)
    
    # Query parameters
    query_params = {
        "table_name": "test-table",
        "key_condition_expression": "id > :id",
        "expression_attribute_values": {":id": "0"},
    }
    
    # Fetch the first page
    first_page = helper.get_page(
        is_scan=False,
        **query_params
    )
    
    # Verify first page results
    assert first_page["count"] == 2
    assert first_page["items"][0]["id"] == "1"
    assert first_page["items"][1]["id"] == "2"
    assert first_page["next_page_key"] == {"id": "2"}
    assert first_page["has_more"] is True
    
    # Fetch the second page
    second_page = helper.get_page(
        is_scan=False,
        exclusive_start_key=first_page["next_page_key"],
        **query_params
    )
    
    # Verify second page results
    assert second_page["count"] == 2
    assert second_page["items"][0]["id"] == "3"
    assert second_page["items"][1]["id"] == "4"
    assert second_page["next_page_key"] is None
    assert second_page["has_more"] is False 