"""
Tests for the DynamoDB client utility.

This module provides unit tests for the DynamoDBClient class using moto for mocking.
"""
import pytest
from botocore.exceptions import ClientError

from src.shared.database.dynamo_client import DynamoDBClient


@pytest.mark.unit
@pytest.mark.phase1
def test_dynamo_client_initialization():
    """Test that DynamoDBClient initializes correctly."""
    # Override the region from environment variables
    client = DynamoDBClient(region_name="us-east-1")
    assert client.region_name == "us-east-1"
    assert client.endpoint_url is None
    
    # Test with custom region
    client = DynamoDBClient(region_name="us-west-2")
    assert client.region_name == "us-west-2"
    
    # Test with local endpoint
    client = DynamoDBClient(use_local=True)
    assert client.endpoint_url == "http://localhost:8000"
    
    # Test with custom endpoint
    client = DynamoDBClient(endpoint_url="http://custom:8000")
    assert client.endpoint_url == "http://custom:8000"


@pytest.mark.unit
@pytest.mark.phase1
def test_put_and_get_item(mock_dynamodb_client, mock_dynamo_tables):
    """Test putting and getting an item from DynamoDB."""
    table_name = mock_dynamo_tables["wa_company_data"]
    
    # Put an item
    item = {
        "company_id": "test-company",
        "project_id": "test-project",
        "company_name": "Test Company",
        "project_name": "Test Project",
    }
    response = mock_dynamodb_client.put_item(table_name, item)
    assert "ResponseMetadata" in response
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    # Get the item
    key = {"company_id": "test-company", "project_id": "test-project"}
    result = mock_dynamodb_client.get_item(table_name, key)
    
    assert result == item


@pytest.mark.unit
@pytest.mark.phase1
def test_update_item(mock_dynamodb_client, mock_dynamo_tables):
    """Test updating an item in DynamoDB."""
    table_name = mock_dynamo_tables["wa_company_data"]
    
    # Put an item
    item = {
        "company_id": "test-company",
        "project_id": "test-project",
        "company_name": "Test Company",
        "project_name": "Test Project",
        "project_status": "active",
    }
    mock_dynamodb_client.put_item(table_name, item)
    
    # Update the item
    key = {"company_id": "test-company", "project_id": "test-project"}
    update_expression = "SET project_status = :status"
    expression_attribute_values = {":status": "inactive"}
    
    response = mock_dynamodb_client.update_item(
        table_name,
        key,
        update_expression,
        expression_attribute_values
    )
    
    # Verify the update
    assert response["Attributes"]["project_status"] == "inactive"
    
    # Get the item and check it was updated
    result = mock_dynamodb_client.get_item(table_name, key)
    assert result["project_status"] == "inactive"


@pytest.mark.unit
@pytest.mark.phase1
def test_delete_item(mock_dynamodb_client, mock_dynamo_tables):
    """Test deleting an item from DynamoDB."""
    table_name = mock_dynamo_tables["wa_company_data"]
    
    # Put an item
    item = {
        "company_id": "test-company",
        "project_id": "test-project",
        "company_name": "Test Company",
        "project_name": "Test Project",
    }
    mock_dynamodb_client.put_item(table_name, item)
    
    # Delete the item
    key = {"company_id": "test-company", "project_id": "test-project"}
    response = mock_dynamodb_client.delete_item(table_name, key)
    assert "ResponseMetadata" in response
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    
    # Verify it's gone
    result = mock_dynamodb_client.get_item(table_name, key)
    assert result == {}


@pytest.mark.unit
@pytest.mark.phase1
def test_query(mock_dynamodb_client, mock_dynamo_tables):
    """Test querying items from DynamoDB."""
    table_name = mock_dynamo_tables["wa_company_data"]
    
    # Put some items
    for i in range(3):
        item = {
            "company_id": "test-company",
            "project_id": f"test-project-{i}",
            "project_name": f"Test Project {i}",
            "company_name": "Test Company",
        }
        mock_dynamodb_client.put_item(table_name, item)
    
    # Query the items
    key_condition_expression = "company_id = :company_id"
    expression_attribute_values = {":company_id": "test-company"}
    
    response = mock_dynamodb_client.query(
        table_name,
        key_condition_expression,
        expression_attribute_values
    )
    
    # Verify the results
    assert "Items" in response
    assert len(response["Items"]) == 3
    
    # Test with limit
    response = mock_dynamodb_client.query(
        table_name,
        key_condition_expression,
        expression_attribute_values,
        limit=2
    )
    
    assert len(response["Items"]) == 2


@pytest.mark.unit
@pytest.mark.phase1
def test_scan(mock_dynamodb_client, mock_dynamo_tables):
    """Test scanning items from DynamoDB."""
    table_name = mock_dynamo_tables["wa_company_data"]
    
    # Put some items
    for i in range(3):
        item = {
            "company_id": f"test-company-{i}",
            "project_id": "test-project",
            "project_name": "Test Project",
            "company_name": f"Test Company {i}",
            "active": i % 2 == 0,  # Even numbers are active
        }
        mock_dynamodb_client.put_item(table_name, item)
    
    # Scan all items
    response = mock_dynamodb_client.scan(table_name)
    assert "Items" in response
    assert len(response["Items"]) == 3
    
    # Scan with filter
    filter_expression = "active = :active"
    expression_attribute_values = {":active": True}
    
    response = mock_dynamodb_client.scan(
        table_name,
        filter_expression,
        expression_attribute_values
    )
    
    assert len(response["Items"]) == 2  # Companies 0 and 2 are active


@pytest.mark.unit
@pytest.mark.phase1
def test_batch_operations(mock_dynamodb_client, mock_dynamo_tables):
    """Test batch operations in DynamoDB."""
    table_name = mock_dynamo_tables["wa_company_data"]
    
    # Create items to batch write
    items = []
    for i in range(5):
        item = {
            "company_id": f"batch-company-{i}",
            "project_id": "batch-project",
            "project_name": "Batch Project",
            "company_name": f"Batch Company {i}",
        }
        items.append(item)
    
    # Batch write items
    batch_items = {table_name: items}
    response = mock_dynamodb_client.batch_write_items(batch_items)
    assert response == {}  # Empty response means all items were processed
    
    # Batch get items
    keys = []
    for i in range(5):
        key = {
            "company_id": f"batch-company-{i}",
            "project_id": "batch-project",
        }
        keys.append(key)
    
    batch_keys = {table_name: keys}
    response = mock_dynamodb_client.batch_get_items(batch_keys)
    
    assert table_name in response
    assert len(response[table_name]) == 5


@pytest.mark.unit
@pytest.mark.phase1
def test_table_operations(mock_dynamo_tables):
    """Test table operations in DynamoDB."""
    # Use aws_credentials and mock_dynamodb from conftest directly
    # Create a fresh client that will use these fixtures
    client = DynamoDBClient(region_name="us-east-1")
    
    # List tables - the tables should exist from the mock_dynamo_tables fixture
    tables = client.list_tables()
    assert "wa_company_data-test" in tables
    assert "conversations-test" in tables
    
    # Describe table
    table_description = client.describe_table("wa_company_data-test")
    assert table_description["TableName"] == "wa_company_data-test"
    assert len(table_description["KeySchema"]) == 2
    
    # Test error handling for non-existent table
    with pytest.raises(ClientError):
        client.get_table("non-existent-table").table_status 