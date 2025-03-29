"""
Tests for query utilities.

This module provides unit tests for the QueryUtilities class.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.shared.database.query_utils import QueryUtilities
from src.shared.database.operations import DatabaseOperations
from src.shared.database.models import Conversation


@pytest.mark.unit
@pytest.mark.phase1
def test_init_query_utilities():
    """Test initializing the QueryUtilities class."""
    query_utils = QueryUtilities(env_name="test")
    assert query_utils.env_name == "test"
    assert isinstance(query_utils.db_ops, DatabaseOperations)
    
    # Test with custom DatabaseOperations
    mock_db_ops = MagicMock(spec=DatabaseOperations)
    query_utils = QueryUtilities(db_ops=mock_db_ops, env_name="prod")
    assert query_utils.env_name == "prod"
    assert query_utils.db_ops is mock_db_ops


@pytest.mark.unit
@pytest.mark.phase1
def test_find_company_projects_by_status():
    """Test finding company projects by status."""
    # Create a mock DatabaseOperations
    mock_db_ops = MagicMock(spec=DatabaseOperations)
    
    # Create mock company data
    mock_projects = [
        MagicMock(project_status="active", project_id="active-1"),
        MagicMock(project_status="active", project_id="active-2"),
        MagicMock(project_status="inactive", project_id="inactive-1"),
    ]
    mock_db_ops.list_company_projects.return_value = mock_projects
    
    # Create the query utils
    query_utils = QueryUtilities(db_ops=mock_db_ops)
    
    # Find active projects
    result = query_utils.find_company_projects_by_status("test-company", "active")
    
    # Verify the result
    assert len(result) == 2
    assert result[0].project_id == "active-1"
    assert result[1].project_id == "active-2"
    
    # Verify the db_ops call
    mock_db_ops.list_company_projects.assert_called_once_with("test-company")
    
    # Find inactive projects
    result = query_utils.find_company_projects_by_status("test-company", "inactive")
    assert len(result) == 1
    assert result[0].project_id == "inactive-1"


@pytest.mark.unit
@pytest.mark.phase1
def test_find_company_projects_by_channel():
    """Test finding company projects by channel."""
    # Create a mock DatabaseOperations
    mock_db_ops = MagicMock(spec=DatabaseOperations)
    
    # Create mock company data
    mock_projects = [
        MagicMock(allowed_channels=["whatsapp", "email"], project_id="project-1"),
        MagicMock(allowed_channels=["whatsapp"], project_id="project-2"),
        MagicMock(allowed_channels=["email"], project_id="project-3"),
    ]
    mock_db_ops.list_company_projects.return_value = mock_projects
    
    # Create the query utils
    query_utils = QueryUtilities(db_ops=mock_db_ops)
    
    # Find WhatsApp projects
    result = query_utils.find_company_projects_by_channel("test-company", "whatsapp")
    
    # Verify the result
    assert len(result) == 2
    assert result[0].project_id == "project-1"
    assert result[1].project_id == "project-2"
    
    # Find Email projects
    result = query_utils.find_company_projects_by_channel("test-company", "email")
    assert len(result) == 2
    assert result[0].project_id == "project-1"
    assert result[1].project_id == "project-3"


@pytest.mark.unit
@pytest.mark.phase1
def test_find_recipient_conversations():
    """Test finding conversations by recipient."""
    # Create a mock DatabaseOperations
    mock_db_ops = MagicMock(spec=DatabaseOperations)
    
    # Create a mock DynamoDB client
    mock_client = MagicMock()
    mock_db_ops.dynamodb_client = mock_client
    
    # Mock phone query response
    phone_response = {
        "Items": [
            {"conversation_id": "convo-1", "recipient_tel": "+1234567890"},
            {"conversation_id": "convo-2", "recipient_tel": "+1234567890"},
        ],
        "Count": 2,
    }
    
    # Mock email query response
    email_response = {
        "Items": [
            {"conversation_id": "convo-3", "recipient_email": "test@example.com"},
        ],
        "Count": 1,
    }
    
    # Set up mock responses
    mock_client.query = MagicMock(side_effect=[phone_response, email_response])
    
    # Create the query utils
    query_utils = QueryUtilities(db_ops=mock_db_ops, env_name="test")
    
    # Query by phone number
    result = query_utils.find_recipient_conversations("+1234567890")
    
    # Verify the query
    args, kwargs = mock_client.query.call_args
    assert kwargs["table_name"] == "conversations-test"
    assert kwargs["key_condition_expression"] == "recipient_tel = :recipient_id"
    assert kwargs["expression_attribute_values"] == {":recipient_id": "+1234567890"}
    assert "index_name" not in kwargs
    
    # Verify the result
    assert len(result) == 2
    assert all(isinstance(item, Conversation) for item in result)
    
    # Query by email
    result = query_utils.find_recipient_conversations("test@example.com", is_email=True)
    
    # Verify the query
    args, kwargs = mock_client.query.call_args
    assert kwargs["table_name"] == "conversations-test"
    assert kwargs["key_condition_expression"] == "recipient_email = :recipient_id"
    assert kwargs["expression_attribute_values"] == {":recipient_id": "test@example.com"}
    assert kwargs["index_name"] == "EmailIndex"
    
    # Verify the result
    assert len(result) == 1
    assert all(isinstance(item, Conversation) for item in result)


@pytest.mark.unit
@pytest.mark.phase1
def test_find_conversations_by_time_period():
    """Test finding conversations by time period."""
    # Create a mock DatabaseOperations
    mock_db_ops = MagicMock(spec=DatabaseOperations)
    
    # Create a mock DynamoDB client
    mock_client = MagicMock()
    mock_db_ops.dynamodb_client = mock_client
    
    # Mock scan response
    scan_response = {
        "Items": [
            {
                "conversation_id": "convo-1",
                "created_at": "2023-06-01T12:00:00Z",
                "channel_method": "whatsapp",
            },
            {
                "conversation_id": "convo-2",
                "created_at": "2023-06-01T13:00:00Z",
                "channel_method": "whatsapp",
            },
        ],
        "Count": 2,
    }
    
    # Set up mock response
    mock_client.scan = MagicMock(return_value=scan_response)
    
    # Create the query utils
    query_utils = QueryUtilities(db_ops=mock_db_ops, env_name="test")
    
    # Query by time period with channel
    start_time = "2023-06-01T00:00:00Z"
    end_time = "2023-06-01T23:59:59Z"
    result = query_utils.find_conversations_by_time_period(
        start_time=start_time,
        end_time=end_time,
        channel="whatsapp"
    )
    
    # Verify the scan
    args, kwargs = mock_client.scan.call_args
    assert kwargs["table_name"] == "conversations-test"
    assert "filter_expression" in kwargs
    assert kwargs["expression_attribute_values"] == {
        ":start_time": start_time,
        ":end_time": end_time,
        ":channel": "whatsapp",
    }
    
    # Verify the result
    assert len(result) == 2
    assert all(isinstance(item, Conversation) for item in result)


@pytest.mark.unit
@pytest.mark.phase1
def test_find_recent_conversations():
    """Test finding recent conversations."""
    # Create a mock DatabaseOperations
    mock_db_ops = MagicMock(spec=DatabaseOperations)
    
    # Create the query utils with a mocked recent conversations method
    query_utils = QueryUtilities(db_ops=mock_db_ops)
    
    with patch.object(query_utils, 'find_conversations_by_time_period') as mock_find:
        mock_find.return_value = [
            MagicMock(conversation_id="recent-1"),
            MagicMock(conversation_id="recent-2"),
        ]
        
        # Find recent conversations
        result = query_utils.find_recent_conversations(hours=12, channel="whatsapp")
        
        # Verify the result
        assert len(result) == 2
        assert result[0].conversation_id == "recent-1"
        assert result[1].conversation_id == "recent-2"
        
        # Verify the call to find_conversations_by_time_period
        args, kwargs = mock_find.call_args
        assert kwargs["channel"] == "whatsapp"
        assert kwargs["limit"] == 50  # Default limit


@pytest.mark.unit
@pytest.mark.phase1
def test_find_failed_conversations():
    """Test finding failed conversations."""
    # Create a mock DatabaseOperations
    mock_db_ops = MagicMock(spec=DatabaseOperations)
    
    # Create a mock DynamoDB client
    mock_client = MagicMock()
    mock_db_ops.dynamodb_client = mock_client
    
    # Mock scan response
    scan_response = {
        "Items": [
            {
                "conversation_id": "failed-1",
                "conversation_status": "failed",
                "created_at": "2023-06-01T12:00:00Z",
            },
        ],
        "Count": 1,
    }
    
    # Set up mock response
    mock_client.scan = MagicMock(return_value=scan_response)
    
    # Create the query utils
    query_utils = QueryUtilities(db_ops=mock_db_ops, env_name="test")
    
    # Find failed conversations
    result = query_utils.find_failed_conversations(hours=24)
    
    # Verify the scan
    args, kwargs = mock_client.scan.call_args
    assert kwargs["table_name"] == "conversations-test"
    assert "filter_expression" in kwargs
    assert "conversation_status = :status" in kwargs["filter_expression"]
    assert ":status" in kwargs["expression_attribute_values"]
    assert kwargs["expression_attribute_values"][":status"] == "failed"
    
    # Verify the result
    assert len(result) == 1
    assert result[0].conversation_id == "failed-1"


@pytest.mark.unit
@pytest.mark.phase1
def test_format_query_response():
    """Test formatting a query response."""
    # Create a mock response
    mock_response = {
        "Items": [
            {
                "conversation_id": "test-convo-1",
                "company_id": "test-company-1",
                "project_id": "test-project-1",
                "channel_method": "whatsapp",
                "request_id": "test-request-1",
                "router_version": "v1.0",
                "conversation_status": "processing",
                "recipient_tel": "+1234567890",
            },
            {
                "conversation_id": "test-convo-2",
                "company_id": "test-company-1",
                "project_id": "test-project-1",
                "channel_method": "whatsapp",
                "request_id": "test-request-2",
                "router_version": "v1.0",
                "conversation_status": "initial_message_sent",
                "recipient_tel": "+1234567891",
            },
        ],
        "Count": 2,
        "ScannedCount": 2,
    }
    
    query_utils = QueryUtilities()
    result = query_utils._format_query_response(mock_response)
    
    assert len(result) == 2
    assert all(isinstance(item, Conversation) for item in result)
    assert result[0].conversation_id == "test-convo-1"
    assert result[1].conversation_id == "test-convo-2"
    
    # Test with empty response
    empty_response = {"Items": [], "Count": 0, "ScannedCount": 0}
    result = query_utils._format_query_response(empty_response)
    assert len(result) == 0


@pytest.mark.unit
@pytest.mark.phase1
def test_query_by_index(mock_dynamo_tables):
    """Test querying by index."""
    query_utils = QueryUtilities(
        conversations_table_name=mock_dynamo_tables["conversations"]
    )
    
    # Mock the query method
    with patch.object(query_utils.dynamodb_client, 'query') as mock_query:
        mock_query.return_value = {
            "Items": [
                {
                    "conversation_id": "test-convo-1",
                    "company_id": "test-company-1",
                    "project_id": "test-project-1",
                    "channel_method": "whatsapp",
                    "request_id": "test-request-1",
                }
            ],
            "Count": 1,
            "ScannedCount": 1,
        }
        
        # Query by CompanyProjectIndex
        result = query_utils.query_by_company_project("test-company-1", "test-project-1")
        
        # Verify the query was called with correct parameters
        mock_query.assert_called_once()
        args, kwargs = mock_query.call_args
        assert kwargs["table_name"] == mock_dynamo_tables["conversations"]
        assert kwargs["key_condition_expression"] == "company_id = :company_id AND project_id = :project_id"
        assert kwargs["expression_attribute_values"] == {
            ":company_id": "test-company-1",
            ":project_id": "test-project-1",
        }
        assert kwargs["index_name"] == "CompanyProjectIndex"
        
        # Verify result
        assert len(result) == 1
        assert result[0].conversation_id == "test-convo-1"


@pytest.mark.unit
@pytest.mark.phase1
def test_query_by_request_id(mock_dynamo_tables):
    """Test querying by request ID."""
    query_utils = QueryUtilities(
        conversations_table_name=mock_dynamo_tables["conversations"]
    )
    
    # Mock the query method
    with patch.object(query_utils.dynamodb_client, 'query') as mock_query:
        mock_query.return_value = {
            "Items": [
                {
                    "conversation_id": "test-convo-1",
                    "company_id": "test-company-1",
                    "project_id": "test-project-1",
                    "channel_method": "whatsapp",
                    "request_id": "test-request-1",
                }
            ],
            "Count": 1,
            "ScannedCount": 1,
        }
        
        # Query by RequestIdIndex
        result = query_utils.query_by_request_id("test-request-1")
        
        # Verify the query was called with correct parameters
        mock_query.assert_called_once()
        args, kwargs = mock_query.call_args
        assert kwargs["table_name"] == mock_dynamo_tables["conversations"]
        assert kwargs["key_condition_expression"] == "request_id = :request_id"
        assert kwargs["expression_attribute_values"] == {
            ":request_id": "test-request-1",
        }
        assert kwargs["index_name"] == "RequestIdIndex"
        
        # Verify result
        assert len(result) == 1
        assert result[0].request_id == "test-request-1"


@pytest.mark.unit
@pytest.mark.phase1
def test_query_by_channel(mock_dynamo_tables):
    """Test querying by channel."""
    query_utils = QueryUtilities(
        conversations_table_name=mock_dynamo_tables["conversations"]
    )
    
    # Mock the query method
    with patch.object(query_utils.dynamodb_client, 'query') as mock_query:
        mock_query.return_value = {
            "Items": [
                {
                    "conversation_id": "test-convo-1",
                    "company_id": "test-company-1",
                    "project_id": "test-project-1",
                    "channel_method": "whatsapp",
                    "request_id": "test-request-1",
                }
            ],
            "Count": 1,
            "ScannedCount": 1,
        }
        
        # Query by ChannelIndex
        result = query_utils.query_by_channel("whatsapp")
        
        # Verify the query was called with correct parameters
        mock_query.assert_called_once()
        args, kwargs = mock_query.call_args
        assert kwargs["table_name"] == mock_dynamo_tables["conversations"]
        assert kwargs["key_condition_expression"] == "channel_method = :channel_method"
        assert kwargs["expression_attribute_values"] == {
            ":channel_method": "whatsapp",
        }
        assert kwargs["index_name"] == "ChannelIndex"
        
        # Verify result
        assert len(result) == 1
        assert result[0].channel_method == "whatsapp"


@pytest.mark.unit
@pytest.mark.phase1
def test_query_by_status(mock_dynamo_tables):
    """Test querying by conversation status."""
    query_utils = QueryUtilities(
        conversations_table_name=mock_dynamo_tables["conversations"]
    )
    
    # Mock the scan method (status query uses scan)
    with patch.object(query_utils.dynamodb_client, 'scan') as mock_scan:
        mock_scan.return_value = {
            "Items": [
                {
                    "conversation_id": "test-convo-1",
                    "company_id": "test-company-1",
                    "project_id": "test-project-1",
                    "channel_method": "whatsapp",
                    "request_id": "test-request-1",
                    "conversation_status": "initial_message_sent",
                }
            ],
            "Count": 1,
            "ScannedCount": 3,
        }
        
        # Query by status
        result = query_utils.query_by_status("initial_message_sent")
        
        # Verify the scan was called with correct parameters
        mock_scan.assert_called_once()
        args, kwargs = mock_scan.call_args
        assert kwargs["table_name"] == mock_dynamo_tables["conversations"]
        assert kwargs["filter_expression"] == "conversation_status = :status"
        assert kwargs["expression_attribute_values"] == {
            ":status": "initial_message_sent",
        }
        
        # Verify result
        assert len(result) == 1
        assert result[0].conversation_status == "initial_message_sent"


@pytest.mark.unit
@pytest.mark.phase1
def test_query_by_email(mock_dynamo_tables):
    """Test querying by email."""
    query_utils = QueryUtilities(
        conversations_table_name=mock_dynamo_tables["conversations"]
    )
    
    # Mock the query method
    with patch.object(query_utils.dynamodb_client, 'query') as mock_query:
        mock_query.return_value = {
            "Items": [
                {
                    "conversation_id": "test-convo-1",
                    "company_id": "test-company-1",
                    "project_id": "test-project-1",
                    "channel_method": "email",
                    "request_id": "test-request-1",
                    "recipient_email": "test@example.com",
                }
            ],
            "Count": 1,
            "ScannedCount": 1,
        }
        
        # Query by EmailIndex
        result = query_utils.query_by_email("test@example.com", "test-convo-1")
        
        # Verify the query was called with correct parameters
        mock_query.assert_called_once()
        args, kwargs = mock_query.call_args
        assert kwargs["table_name"] == mock_dynamo_tables["conversations"]
        assert kwargs["key_condition_expression"] == "recipient_email = :email AND conversation_id = :conversation_id"
        assert kwargs["expression_attribute_values"] == {
            ":email": "test@example.com",
            ":conversation_id": "test-convo-1",
        }
        assert kwargs["index_name"] == "EmailIndex"
        
        # Verify result
        assert len(result) == 1
        assert result[0].recipient_email == "test@example.com"
        
        # Test with no results (single item is expected)
        mock_query.return_value = {"Items": [], "Count": 0, "ScannedCount": 0}
        result = query_utils.query_by_email("non-existent@example.com", "test-convo-1")
        assert result is None


@pytest.mark.unit
@pytest.mark.phase1
def test_query_by_message_id(mock_dynamo_tables):
    """Test querying by message ID."""
    query_utils = QueryUtilities(
        conversations_table_name=mock_dynamo_tables["conversations"]
    )
    
    # Mock the query method
    with patch.object(query_utils.dynamodb_client, 'query') as mock_query:
        mock_query.return_value = {
            "Items": [
                {
                    "conversation_id": "test-convo-1",
                    "company_id": "test-company-1",
                    "project_id": "test-project-1",
                    "channel_method": "whatsapp",
                    "request_id": "test-request-1",
                    "message_id": "msg123",
                }
            ],
            "Count": 1,
            "ScannedCount": 1,
        }
        
        # Query by MessageIdIndex
        result = query_utils.query_by_message_id("msg123")
        
        # Verify the query was called with correct parameters
        mock_query.assert_called_once()
        args, kwargs = mock_query.call_args
        assert kwargs["table_name"] == mock_dynamo_tables["conversations"]
        assert kwargs["key_condition_expression"] == "message_id = :message_id"
        assert kwargs["expression_attribute_values"] == {
            ":message_id": "msg123",
        }
        assert kwargs["index_name"] == "MessageIdIndex"
        
        # Verify result
        assert result is not None
        assert result.message_id == "msg123"
        
        # Test with no results
        mock_query.return_value = {"Items": [], "Count": 0, "ScannedCount": 0}
        result = query_utils.query_by_message_id("non-existent")
        assert result is None


@pytest.mark.unit
@pytest.mark.phase1
def test_query_recent(mock_dynamo_tables):
    """Test querying recent conversations."""
    query_utils = QueryUtilities(
        conversations_table_name=mock_dynamo_tables["conversations"]
    )
    
    # Mock the query method
    with patch.object(query_utils.dynamodb_client, 'query') as mock_query:
        mock_query.return_value = {
            "Items": [
                {
                    "conversation_id": "test-convo-1",
                    "company_id": "test-company-1",
                    "project_id": "test-project-1",
                    "channel_method": "whatsapp",
                    "request_id": "test-request-1",
                    "created_at": datetime.now().isoformat(),
                }
            ],
            "Count": 1,
            "ScannedCount": 1,
        }
        
        # Query recent conversations
        timestamp = datetime.now().isoformat()
        result = query_utils.query_recent(timestamp, channel="whatsapp")
        
        # Verify the query was called with correct parameters
        mock_query.assert_called_once()
        args, kwargs = mock_query.call_args
        assert kwargs["table_name"] == mock_dynamo_tables["conversations"]
        assert kwargs["key_condition_expression"] == "channel_method = :channel AND created_at <= :timestamp"
        assert kwargs["expression_attribute_values"][":channel"] == "whatsapp"
        assert kwargs["expression_attribute_values"][":timestamp"] == timestamp
        assert kwargs["index_name"] == "RecentConversationsIndex"
        assert kwargs["scan_index_forward"] is False  # Descending order
        
        # Verify result
        assert len(result) == 1
        assert result[0].channel_method == "whatsapp" 