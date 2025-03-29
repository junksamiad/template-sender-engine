"""
Fixtures for database unit tests.

This module provides pytest fixtures for testing database components.
"""
import os
import boto3
import pytest
from moto import mock_dynamodb

from src.shared.database.dynamo_client import DynamoDBClient
from src.shared.database.operations import DatabaseOperations


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def mock_dynamodb_client(aws_credentials):
    """Create a mock DynamoDB client."""
    with mock_dynamodb():
        client = DynamoDBClient(region_name="us-east-1")
        yield client


@pytest.fixture
def mock_dynamo_tables(mock_dynamodb_client):
    """Create mock DynamoDB tables."""
    # Create wa_company_data table
    mock_dynamodb_client.create_table(
        table_name="wa_company_data-test",
        key_schema=[
            {"AttributeName": "company_id", "KeyType": "HASH"},
            {"AttributeName": "project_id", "KeyType": "RANGE"},
        ],
        attribute_definitions=[
            {"AttributeName": "company_id", "AttributeType": "S"},
            {"AttributeName": "project_id", "AttributeType": "S"},
        ],
        provisioned_throughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    # Create conversations table
    mock_dynamodb_client.create_table(
        table_name="conversations-test",
        key_schema=[
            {"AttributeName": "recipient_tel", "KeyType": "HASH"},
            {"AttributeName": "conversation_id", "KeyType": "RANGE"},
        ],
        attribute_definitions=[
            {"AttributeName": "recipient_tel", "AttributeType": "S"},
            {"AttributeName": "conversation_id", "AttributeType": "S"},
            {"AttributeName": "company_id", "AttributeType": "S"},
            {"AttributeName": "project_id", "AttributeType": "S"},
            {"AttributeName": "request_id", "AttributeType": "S"},
            {"AttributeName": "channel_method", "AttributeType": "S"},
            {"AttributeName": "recipient_email", "AttributeType": "S"},
            {"AttributeName": "message_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        provisioned_throughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        global_secondary_indexes=[
            {
                "IndexName": "CompanyProjectIndex",
                "KeySchema": [
                    {"AttributeName": "company_id", "KeyType": "HASH"},
                    {"AttributeName": "project_id", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            },
            {
                "IndexName": "RequestIdIndex",
                "KeySchema": [
                    {"AttributeName": "request_id", "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            },
            {
                "IndexName": "ChannelIndex",
                "KeySchema": [
                    {"AttributeName": "channel_method", "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            },
            {
                "IndexName": "EmailIndex",
                "KeySchema": [
                    {"AttributeName": "recipient_email", "KeyType": "HASH"},
                    {"AttributeName": "conversation_id", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            },
            {
                "IndexName": "MessageIdIndex",
                "KeySchema": [
                    {"AttributeName": "message_id", "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            },
            {
                "IndexName": "RecentConversationsIndex",
                "KeySchema": [
                    {"AttributeName": "channel_method", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            },
        ],
    )

    yield {
        "wa_company_data": "wa_company_data-test",
        "conversations": "conversations-test",
    }


@pytest.fixture
def mock_db_operations(mock_dynamodb_client, mock_dynamo_tables):
    """Create a mock DatabaseOperations instance."""
    operations = DatabaseOperations(
        dynamodb_client=mock_dynamodb_client,
        wa_company_data_table_name=mock_dynamo_tables["wa_company_data"],
        conversations_table_name=mock_dynamo_tables["conversations"],
        env_name="test",
    )
    return operations


@pytest.fixture
def sample_company_data():
    """Create sample company data for tests."""
    return {
        "company_id": "test-company-1",
        "project_id": "test-project-1",
        "company_name": "Test Company",
        "project_name": "Test Project",
        "project_status": "active",
        "allowed_channels": ["whatsapp", "email"],
        "company_rep": {
            "company_rep_1": "John Doe",
            "company_rep_2": "Jane Smith",
        },
        "rate_limits": {
            "whatsapp": {
                "max_per_minute": 60,
                "max_per_hour": 1000,
            }
        },
        "channel_config": {
            "whatsapp": {
                "template_ids": ["template-1", "template-2"],
                "credentials_reference": "secret/whatsapp/test-company-1",
            }
        },
    }


@pytest.fixture
def sample_conversation_data():
    """Create sample conversation data for tests."""
    return {
        "conversation_id": "test-convo-1",
        "company_id": "test-company-1",
        "project_id": "test-project-1",
        "company_name": "Test Company",
        "project_name": "Test Project",
        "channel_method": "whatsapp",
        "request_id": "test-request-1",
        "router_version": "v1.0",
        "conversation_status": "processing",
        "recipient_tel": "+1234567890",
        "company_rep": {
            "company_rep_1": "John Doe",
        },
        "company_whatsapp_number": "+0987654321",
        "whatsapp_credentials_reference": "secret/whatsapp/test-company-1",
        "recipient_first_name": "Test",
        "recipient_last_name": "User",
        "comms_consent": True,
        "project_data": {
            "job_id": "job-123",
            "job_role": "Developer",
        },
        "ai_config": {
            "assistant_id_template_sender": "assistant-template-1",
            "assistant_id_replies": "assistant-replies-1",
            "ai_api_key_reference": "secret/openai/key",
        },
        "messages": [
            {
                "entry_id": "msg-1",
                "role": "system",
                "content": "System message",
                "message_timestamp": "2023-06-01T12:00:00Z",
            }
        ],
    } 