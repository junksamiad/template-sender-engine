import pytest
import boto3
import os
from moto import mock_dynamodb
from unittest.mock import patch
import datetime
from botocore.exceptions import ClientError
from typing import TYPE_CHECKING

# Import boto3 types for type hinting if available
if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

# Module to test
# from src_dev.channel_processor.whatsapp.app.services import dynamodb_service
from channel_processor.whatsapp.app.services import dynamodb_service
# Reload the module to re-initialize client/table with mocked env vars/moto
from importlib import reload

# --- Constants ---
DUMMY_TABLE_NAME = "test-conversations-table"
DUMMY_VERSION = "processor-1.2.3"

# --- Fixtures ---

@pytest.fixture(scope="function", autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["CONVERSATIONS_TABLE"] = DUMMY_TABLE_NAME
    os.environ["VERSION"] = DUMMY_VERSION

@pytest.fixture(scope="function")
def dynamodb_table(aws_credentials):
    """Creates a mock DynamoDB table for the tests."""
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName=DUMMY_TABLE_NAME,
            KeySchema=[
                {'AttributeName': 'primary_channel', 'KeyType': 'HASH'}, # Partition key
                {'AttributeName': 'conversation_id', 'KeyType': 'RANGE'}  # Sort key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'primary_channel', 'AttributeType': 'S'},
                {'AttributeName': 'conversation_id', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        # Reload the service module AFTER the table is created and env vars are set
        reload(dynamodb_service)
        table = dynamodb_service.conversations_table
        assert table is not None
        assert table.name == DUMMY_TABLE_NAME
        yield table

@pytest.fixture
def valid_context_object():
    """Provides a valid context object for testing create_initial_conversation_record."""
    # Based on context_utils tests, but simplified for DB interaction
    return {
        'metadata': {'router_version': 'router-0.1.0'},
        'conversation_data': {'conversation_id': 'conv_test_123'},
        'frontend_payload': {
            'request_data': {
                'request_id': 'req_abc_456',
                'channel_method': 'whatsapp',
                'initial_request_timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
            },
            'recipient_data': {
                'recipient_tel': '+15551234567',
                'recipient_first_name': 'Testy',
                'recipient_last_name': 'McTestface',
                'comms_consent': True,
                'recipient_email': 'testy@example.com' # Also provide email
            },
            'project_data': {'custom_field': 'custom_value'}
        },
        'company_data_payload': {
            'company_id': 'comp_xyz_789',
            'project_id': 'proj_pdq_101',
            'company_name': 'Test Inc.',
            'project_name': 'Initial Send Test',
            'allowed_channels': ['whatsapp', 'email'],
            'project_status': 'active',
            'auto_queue_initial_message': True,
            'auto_queue_initial_message_from_number': '+15559876543',
            'auto_queue_reply_message': False,
            'company_rep': {'name': 'Rep Name', 'email': 'rep@test.com'},
            'channel_config': {
                'whatsapp': {
                    'whatsapp_credentials_id': 'cred_whatsapp_abc'
                }
            },
            'ai_config': {
                'openai_config': {
                    'whatsapp': {
                        'api_key_reference': 'secret_openai_key',
                        'assistant_id_template_sender': 'asst_sender_123'
                    }
                }
            }
        }
    }

# --- Tests for create_initial_conversation_record ---

def test_create_initial_success(dynamodb_table, valid_context_object):
    """Test successful creation of a new conversation record."""
    success = dynamodb_service.create_initial_conversation_record(valid_context_object)
    assert success

    # Verify item in DB
    item = dynamodb_table.get_item(
        Key={
            'primary_channel': valid_context_object['frontend_payload']['recipient_data']['recipient_tel'],
            'conversation_id': valid_context_object['conversation_data']['conversation_id']
        }
    ).get('Item')

    assert item is not None
    assert item['company_id'] == valid_context_object['company_data_payload']['company_id']
    assert item['project_id'] == valid_context_object['company_data_payload']['project_id']
    assert item['request_id'] == valid_context_object['frontend_payload']['request_data']['request_id']
    assert item['channel_method'] == 'whatsapp'
    assert item['recipient_tel'] == valid_context_object['frontend_payload']['recipient_data']['recipient_tel']
    assert item['recipient_email'] == valid_context_object['frontend_payload']['recipient_data']['recipient_email'] # Check other channel id stored
    assert item['conversation_status'] == 'processing'
    assert item['messages'] == []
    assert item['task_complete'] == 0
    assert item['comms_consent'] is True
    assert item['processor_version'] == DUMMY_VERSION.replace("processor-", "")
    assert item['router_version'] == valid_context_object['metadata']['router_version']
    assert 'created_at' in item
    assert 'updated_at' in item
    assert item['created_at'] == item['updated_at']
    assert item['project_data'] == valid_context_object['frontend_payload']['project_data']
    assert item['ai_config'] == valid_context_object['company_data_payload']['ai_config']['openai_config']['whatsapp']
    assert item['channel_config'] == valid_context_object['company_data_payload']['channel_config']['whatsapp']
    # Spot check a few None values were omitted (moto behavior)
    assert item['thread_id'] is None # Check value is None instead

def test_create_initial_idempotency(dynamodb_table, valid_context_object):
    """Test that calling create twice succeeds and doesn't overwrite (idempotency)."""
    # First call - should create
    success1 = dynamodb_service.create_initial_conversation_record(valid_context_object)
    assert success1
    item1 = dynamodb_table.get_item(
        Key={
            'primary_channel': valid_context_object['frontend_payload']['recipient_data']['recipient_tel'],
            'conversation_id': valid_context_object['conversation_data']['conversation_id']
        }
    ).get('Item')
    assert item1['conversation_status'] == 'processing' # Initial status

    # Modify context slightly (as if a retry happened with slightly diff data)
    # We expect the original record to remain untouched.
    modified_context = valid_context_object.copy()
    modified_context['metadata'] = {'router_version': 'router-0.2.0'} # Change metadata

    # Second call - should hit ConditionalCheckFailedException but return True
    success2 = dynamodb_service.create_initial_conversation_record(modified_context)
    assert success2

    # Verify item hasn't changed
    item2 = dynamodb_table.get_item(
        Key={
            'primary_channel': valid_context_object['frontend_payload']['recipient_data']['recipient_tel'],
            'conversation_id': valid_context_object['conversation_data']['conversation_id']
        }
    ).get('Item')
    assert item2['router_version'] == 'router-0.1.0' # Original metadata
    assert item2['created_at'] == item1['created_at'] # Timestamp unchanged

def test_create_initial_missing_key(dynamodb_table, valid_context_object, caplog):
    """Test failure when a required key is missing from context."""
    invalid_context = valid_context_object.copy()
    del invalid_context['conversation_data'] # Remove a required key

    success = dynamodb_service.create_initial_conversation_record(invalid_context)
    assert not success
    assert "Missing expected key in context_object: 'conversation_data'" in caplog.text

def test_create_initial_email_channel(dynamodb_table, valid_context_object):
    """Test successful creation when channel_method is email."""
    email_context = valid_context_object.copy()
    email_context['frontend_payload']['request_data']['channel_method'] = 'email'
    # Assume email config exists in the mock data
    email_context['company_data_payload']['channel_config']['email'] = {'email_credentials_id': 'cred_email_xyz'}
    email_context['company_data_payload']['ai_config']['openai_config']['email'] = {'api_key_reference': 'secret_email_key', 'assistant_id_template_sender': 'asst_email_456'}

    success = dynamodb_service.create_initial_conversation_record(email_context)
    assert success

    item = dynamodb_table.get_item(
        Key={
            'primary_channel': email_context['frontend_payload']['recipient_data']['recipient_email'], # PK is email now
            'conversation_id': email_context['conversation_data']['conversation_id']
        }
    ).get('Item')
    assert item is not None
    assert item['channel_method'] == 'email'
    assert item['primary_channel'] == email_context['frontend_payload']['recipient_data']['recipient_email']
    assert item['recipient_tel'] == email_context['frontend_payload']['recipient_data']['recipient_tel'] # Tel still stored
    assert item['ai_config'] == email_context['company_data_payload']['ai_config']['openai_config']['email']
    assert item['channel_config'] == email_context['company_data_payload']['channel_config']['email']

def test_create_initial_unsupported_channel(dynamodb_table, valid_context_object, caplog):
    """Test failure with an unsupported channel_method."""
    invalid_context = valid_context_object.copy()
    invalid_context['frontend_payload']['request_data']['channel_method'] = 'fax'

    success = dynamodb_service.create_initial_conversation_record(invalid_context)
    assert not success
    assert "Unsupported channel_method 'fax' found." in caplog.text

def test_create_initial_missing_primary_identifier(dynamodb_table, valid_context_object, caplog):
    """Test failure if primary identifier (tel for whatsapp) is missing."""
    invalid_context = valid_context_object.copy()
    del invalid_context['frontend_payload']['recipient_data']['recipient_tel']

    success = dynamodb_service.create_initial_conversation_record(invalid_context)
    assert not success
    assert "Missing recipient_tel in context_object for whatsapp channel" in caplog.text

def test_create_initial_no_table(valid_context_object, caplog):
    """Test failure if the table is not initialized (env var missing)."""
    with patch.dict(os.environ, {"CONVERSATIONS_TABLE": ""}, clear=True):
        reload(dynamodb_service) # Reload to pick up empty env var
        assert dynamodb_service.conversations_table is None
        success = dynamodb_service.create_initial_conversation_record(valid_context_object)
        assert not success
        assert "DynamoDB conversations table is not initialized" in caplog.text
    # Restore env var for other tests via aws_credentials fixture reloading
    reload(dynamodb_service)

# --- Tests for update_conversation_after_send ---

@pytest.fixture
def existing_record_params(valid_context_object):
    """Parameters from the valid context needed to identify the record."""
    return {
        "primary_channel": valid_context_object['frontend_payload']['recipient_data']['recipient_tel'],
        "conversation_id": valid_context_object['conversation_data']['conversation_id']
    }

@pytest.fixture
def update_args(existing_record_params):
    """Provides default arguments for the update function."""
    now_iso = datetime.datetime.utcnow().isoformat() + 'Z'
    return {
        "primary_channel_pk": existing_record_params['primary_channel'],
        "conversation_id_sk": existing_record_params['conversation_id'],
        "new_status": "initial_message_sent",
        "updated_at_ts": now_iso,
        "thread_id": "thread_openai_789",
        "processing_time_ms": 5500,
        "message_to_append": {
            "role": "assistant",
            "content": "This is the sent message",
            "timestamp": now_iso,
            "msg_id": "twilio_msg_abc"
        }
    }

def test_update_after_send_success(dynamodb_table, valid_context_object, update_args):
    """Test successful update of an existing record."""
    # 1. Create the initial record first
    create_success = dynamodb_service.create_initial_conversation_record(valid_context_object)
    assert create_success

    # 2. Perform the update
    update_success = dynamodb_service.update_conversation_after_send(**update_args)
    assert update_success

    # 3. Verify the updated item in DB
    item = dynamodb_table.get_item(
        Key={
            'primary_channel': update_args["primary_channel_pk"],
            'conversation_id': update_args["conversation_id_sk"]
        }
    ).get('Item')

    assert item is not None
    assert item['conversation_status'] == update_args["new_status"]
    assert item['updated_at'] == update_args["updated_at_ts"]
    assert item['thread_id'] == update_args["thread_id"]
    assert item['initial_processing_time_ms'] == update_args["processing_time_ms"]
    assert len(item['messages']) == 1
    assert item['messages'][0] == update_args["message_to_append"]
    # Check created_at is still the original time
    assert item['created_at'] != item['updated_at']

def test_update_after_send_minimal_args(dynamodb_table, valid_context_object, existing_record_params, update_args):
    """Test successful update when optional args (thread_id, proc_time) are None."""
    create_success = dynamodb_service.create_initial_conversation_record(valid_context_object)
    assert create_success

    minimal_update_args = update_args.copy()
    minimal_update_args["thread_id"] = None
    minimal_update_args["processing_time_ms"] = None

    update_success = dynamodb_service.update_conversation_after_send(**minimal_update_args)
    assert update_success

    item = dynamodb_table.get_item(
        Key={
            'primary_channel': existing_record_params["primary_channel"],
            'conversation_id': existing_record_params["conversation_id"]
        }
    ).get('Item')
    assert item['conversation_status'] == minimal_update_args["new_status"]
    assert item['updated_at'] == minimal_update_args["updated_at_ts"]
    assert len(item['messages']) == 1
    assert item['messages'][0] == minimal_update_args["message_to_append"]
    assert item['thread_id'] is None # Should not be set if None
    assert 'initial_processing_time_ms' not in item # Should not be set if None

def test_update_after_send_append_message(dynamodb_table, valid_context_object, existing_record_params, update_args):
    """Test that messages are correctly appended."""
    create_success = dynamodb_service.create_initial_conversation_record(valid_context_object)
    assert create_success

    # First update
    update1_success = dynamodb_service.update_conversation_after_send(**update_args)
    assert update1_success

    # Second update (simulate another message)
    update_args2 = update_args.copy()
    update_args2["new_status"] = "user_replied"
    update_args2["updated_at_ts"] = datetime.datetime.utcnow().isoformat() + 'Z'
    update_args2["message_to_append"] = {
        "role": "user",
        "content": "This is the user reply",
        "timestamp": update_args2["updated_at_ts"],
        "msg_id": "user_msg_456"
    }
    update_args2["thread_id"] = None # Don't update thread id again perhaps
    update_args2["processing_time_ms"] = None

    update2_success = dynamodb_service.update_conversation_after_send(**update_args2)
    assert update2_success

    item = dynamodb_table.get_item(
        Key={
            'primary_channel': existing_record_params["primary_channel"],
            'conversation_id': existing_record_params["conversation_id"]
        }
    ).get('Item')

    assert item['conversation_status'] == update_args2["new_status"]
    assert item['updated_at'] == update_args2["updated_at_ts"]
    assert len(item['messages']) == 2
    assert item['messages'][0] == update_args["message_to_append"]
    assert item['messages'][1] == update_args2["message_to_append"]
    assert item['thread_id'] == update_args["thread_id"]
    assert item['initial_processing_time_ms'] == update_args["processing_time_ms"]

def test_update_after_send_no_table(update_args, caplog):
    """Test update failure if the table is not initialized."""
    with patch.dict(os.environ, {"CONVERSATIONS_TABLE": ""}, clear=True):
        reload(dynamodb_service)
        assert dynamodb_service.conversations_table is None
        success = dynamodb_service.update_conversation_after_send(**update_args)
        assert not success
        assert "DynamoDB conversations table is not initialized" in caplog.text
    reload(dynamodb_service)

def test_update_after_send_client_error(dynamodb_table, valid_context_object, update_args, caplog):
    """Test update failure on a DynamoDB ClientError."""
    create_success = dynamodb_service.create_initial_conversation_record(valid_context_object)
    assert create_success

    # Mock the update_item call to raise an error
    with patch.object(dynamodb_service.conversations_table, 'update_item') as mock_update:
        error_response = {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Table not found'}}
        mock_update.side_effect = ClientError(error_response, 'UpdateItem')

        success = dynamodb_service.update_conversation_after_send(**update_args)
        assert not success
        assert "DynamoDB ClientError updating record" in caplog.text
        assert "Table not found" in caplog.text
        mock_update.assert_called_once() 