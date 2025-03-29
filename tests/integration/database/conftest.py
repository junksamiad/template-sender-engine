"""
Fixtures for database integration tests.

This module provides pytest fixtures for integration testing with a local DynamoDB instance.
"""
import os
import boto3
import pytest
import docker
import time
import logging
from datetime import datetime

from src.shared.database.dynamo_client import DynamoDBClient
from src.shared.database.operations import DatabaseOperations

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def docker_client():
    """Get a Docker client."""
    return docker.from_env()


@pytest.fixture(scope="session")
def local_dynamodb(docker_client):
    """
    Start a local DynamoDB container for integration testing.
    
    This fixture is session-scoped, so the container is started once
    for the entire test session.
    """
    try:
        # Pull the official DynamoDB local image
        docker_client.images.pull("amazon/dynamodb-local:latest")
        
        # Start the container
        container = docker_client.containers.run(
            "amazon/dynamodb-local:latest",
            ports={"8000/tcp": 8000},
            detach=True,
            remove=True,
        )
        
        logger.info("Started DynamoDB local container")
        
        # Wait for container to be ready
        time.sleep(2)
        
        # Set AWS credentials for local testing
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        
        yield container
        
        # Clean up the container
        container.stop()
        logger.info("Stopped DynamoDB local container")
        
    except Exception as e:
        logger.error(f"Failed to set up DynamoDB local: {str(e)}")
        raise


@pytest.fixture
def integration_dynamodb_client(local_dynamodb):
    """Create a DynamoDB client connected to the local DynamoDB container."""
    return DynamoDBClient(
        region_name="us-east-1",
        endpoint_url="http://localhost:8000",
        use_local=True
    )


@pytest.fixture
def integration_tables(integration_dynamodb_client):
    """
    Create test tables in the local DynamoDB instance.
    
    This fixture creates the tables and tears them down after each test.
    """
    # Create wa_company_data table
    integration_dynamodb_client.create_table(
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
    integration_dynamodb_client.create_table(
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

    # Wait for tables to be active
    time.sleep(1)
    
    table_names = {
        "wa_company_data": "wa_company_data-test",
        "conversations": "conversations-test",
    }
    
    yield table_names
    
    # Clean up tables
    for table_name in table_names.values():
        integration_dynamodb_client.delete_table(table_name)


@pytest.fixture
def integration_db_operations(integration_dynamodb_client, integration_tables):
    """Create a DatabaseOperations instance for integration testing."""
    return DatabaseOperations(
        dynamodb_client=integration_dynamodb_client,
        wa_company_data_table_name=integration_tables["wa_company_data"],
        conversations_table_name=integration_tables["conversations"],
        env_name="test",
    )


@pytest.fixture
def integration_sample_company_data():
    """Create sample company data for integration tests."""
    return {
        "company_id": "integration-company-1",
        "project_id": "integration-project-1",
        "company_name": "Integration Test Company",
        "project_name": "Integration Test Project",
        "project_status": "active",
        "allowed_channels": ["whatsapp", "email"],
        "company_rep": {
            "company_rep_1": "Integration Tester",
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
                "credentials_reference": "secret/whatsapp/integration-test",
            }
        },
    }


@pytest.fixture
def integration_sample_conversation_data():
    """Create sample conversation data for integration tests."""
    return {
        "conversation_id": "integration-convo-1",
        "company_id": "integration-company-1",
        "project_id": "integration-project-1",
        "company_name": "Integration Test Company",
        "project_name": "Integration Test Project",
        "channel_method": "whatsapp",
        "request_id": "integration-request-1",
        "router_version": "v1.0",
        "conversation_status": "processing",
        "recipient_tel": "+9876543210",
        "company_rep": {
            "company_rep_1": "Integration Tester",
        },
        "company_whatsapp_number": "+0123456789",
        "whatsapp_credentials_reference": "secret/whatsapp/integration-test",
        "recipient_first_name": "Integration",
        "recipient_last_name": "Test",
        "comms_consent": True,
        "project_data": {
            "job_id": "job-integration-123",
            "job_role": "Integration Tester",
        },
        "ai_config": {
            "assistant_id_template_sender": "assistant-integration-1",
            "assistant_id_replies": "assistant-integration-2",
            "ai_api_key_reference": "secret/openai/integration-key",
        },
        "messages": [
            {
                "entry_id": "int-msg-1",
                "role": "system",
                "content": "Integration test message",
                "message_timestamp": datetime.now().isoformat(),
            }
        ],
    } 