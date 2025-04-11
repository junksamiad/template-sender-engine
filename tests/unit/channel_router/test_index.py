# tests/unit/channel_router/test_index.py

import pytest
from unittest.mock import patch, MagicMock, ANY
import json
import os
import sys

# Add src_dev parent directory to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import the handler function
from src_dev.channel_router.app import index
# Import specific error codes if needed for assertions
from src_dev.channel_router.app.services import dynamodb_service

# --- Test Fixtures ---

@pytest.fixture
def mock_dependencies(mocker):
    """Mocks all external dependencies for the index handler."""
    # Patch the functions/modules as they are named *within* index.py
    mock_parser_func = mocker.patch('src_dev.channel_router.app.index.parse_request_body')
    mock_validator_func = mocker.patch('src_dev.channel_router.app.index.validate_initiate_request')
    mock_db_service_module = mocker.patch('src_dev.channel_router.app.index.dynamodb_service')
    mock_context_builder_func = mocker.patch('src_dev.channel_router.app.index.build_context_object')
    mock_sqs_service_module = mocker.patch('src_dev.channel_router.app.index.sqs_service')
    mock_resp_success_func = mocker.patch('src_dev.channel_router.app.index.create_success_response')
    mock_resp_error_func = mocker.patch('src_dev.channel_router.app.index.create_error_response')

    # --- Mock os.environ using patch.dict ---
    mocker.patch.dict(os.environ, {
        'COMPANY_DATA_TABLE': 'mock-company-table',
        'WHATSAPP_QUEUE_URL': 'mock_whatsapp_url',
        'EMAIL_QUEUE_URL': 'mock_email_url',
        'SMS_QUEUE_URL': 'mock_sms_url',
        'VERSION': 'test-version-1.0',
        'LOG_LEVEL': 'INFO' # Add log level just in case
    })
    # --- End os.environ mock ---

    mock_resp_error_func.return_value = {'statusCode': 500, 'body': 'Default Error'}

    return {
        'parse_request_body': mock_parser_func,
        'validate_initiate_request': mock_validator_func,
        'get_company_config': mock_db_service_module.get_company_config,
        'build_context_object': mock_context_builder_func,
        'send_message_to_queue': mock_sqs_service_module.send_message_to_queue,
        'create_success_response': mock_resp_success_func,
        'create_error_response': mock_resp_error_func,
    }

@pytest.fixture
def sample_apigw_event():
    """Provides a basic API Gateway proxy event."""
    return { 'httpMethod': 'POST', 'path': '/initiate-conversation', 'headers': {'Content-Type': 'application/json'}, 'body': '{"data": "mocked_out"}', 'isBase64Encoded': False, 'requestContext': {'requestId': 'apigw-req-id'} }

@pytest.fixture
def base_mock_payload():
    """Provides a payload structure often returned by the mocked parser."""
    return { 'company_data': {'company_id': 'c1', 'project_id': 'p1'}, 'recipient_data': {}, 'request_data': {'channel_method': 'whatsapp', 'request_id': 'req1'} }

@pytest.fixture
def base_mock_config():
    """Provides a config structure often returned by the mocked db service."""
    return {'allowed_channels': ['whatsapp', 'email', 'sms'], 'project_status': 'active'}

# --- Test Cases ---

def test_lambda_handler_success_path(mock_dependencies, sample_apigw_event, base_mock_payload, base_mock_config):
    """Test the main handler's successful execution path."""
    mock_context = {'built': 'context'}
    mock_success_resp = {'statusCode': 200, 'body': 'Success'}
    mock_dependencies['parse_request_body'].return_value = base_mock_payload
    mock_dependencies['validate_initiate_request'].return_value = None
    mock_dependencies['get_company_config'].return_value = base_mock_config
    mock_dependencies['build_context_object'].return_value = mock_context
    mock_dependencies['send_message_to_queue'].return_value = True
    mock_dependencies['create_success_response'].return_value = mock_success_resp

    result = index.lambda_handler(sample_apigw_event, None)

    assert result == mock_success_resp
    mock_dependencies['parse_request_body'].assert_called_once_with(sample_apigw_event)
    mock_dependencies['validate_initiate_request'].assert_called_once_with(base_mock_payload)
    mock_dependencies['get_company_config'].assert_called_once_with('c1', 'p1')
    mock_dependencies['build_context_object'].assert_called_once_with(base_mock_payload, base_mock_config, 'test-version-1.0')
    mock_dependencies['send_message_to_queue'].assert_called_once_with('mock_whatsapp_url', mock_context, 'whatsapp')
    mock_dependencies['create_success_response'].assert_called_once_with('req1')
    mock_dependencies['create_error_response'].assert_not_called()


def test_handler_parse_fails(mock_dependencies, sample_apigw_event):
    """Test handler returns error when parse_request_body returns None."""
    mock_dependencies['parse_request_body'].return_value = None
    expected_error_resp = {'statusCode': 400, 'body': 'Parse Error'}
    mock_dependencies['create_error_response'].return_value = expected_error_resp

    result = index.lambda_handler(sample_apigw_event, None)

    assert result == expected_error_resp
    # Assert create_error_response called correctly, including the implicit status_code_hint
    mock_dependencies['create_error_response'].assert_called_once_with(
        error_code='INVALID_REQUEST', # Updated expected code
        error_message='Invalid or missing request body', # Updated expected message
        request_id=ANY, # Use ANY as it's generated internally on parse fail
        status_code_hint=400
    )
    mock_dependencies['validate_initiate_request'].assert_not_called()


def test_handler_validation_fails(mock_dependencies, sample_apigw_event, base_mock_payload):
    """Test handler returns error when validate_initiate_request fails."""
    mock_error = ("TEST_VALIDATION_CODE", "Test validation message")
    mock_dependencies['parse_request_body'].return_value = base_mock_payload
    mock_dependencies['validate_initiate_request'].return_value = mock_error
    expected_error_resp = {'statusCode': 400, 'body': 'Validation Error'}
    mock_dependencies['create_error_response'].return_value = expected_error_resp

    result = index.lambda_handler(sample_apigw_event, None)

    assert result == expected_error_resp
    mock_dependencies['create_error_response'].assert_called_once_with(
        error_code=mock_error[0],
        error_message=mock_error[1],
        request_id=base_mock_payload['request_data']['request_id'],
        status_code_hint=400 # Added hint
    )
    mock_dependencies['get_company_config'].assert_not_called()


def test_handler_db_config_not_found(mock_dependencies, sample_apigw_event, base_mock_payload):
    """Test handler returns error when get_company_config returns COMPANY_NOT_FOUND."""
    mock_error = dynamodb_service.COMPANY_NOT_FOUND
    mock_dependencies['parse_request_body'].return_value = base_mock_payload
    mock_dependencies['validate_initiate_request'].return_value = None
    mock_dependencies['get_company_config'].return_value = mock_error
    expected_error_resp = {'statusCode': 404, 'body': 'Not Found Error'}
    mock_dependencies['create_error_response'].return_value = expected_error_resp

    result = index.lambda_handler(sample_apigw_event, None)

    assert result == expected_error_resp
    mock_dependencies['create_error_response'].assert_called_once_with(
        error_code=mock_error[0],
        error_message=mock_error[1],
        request_id=base_mock_payload['request_data']['request_id'],
        status_code_hint=404 # Added hint
    )
    mock_dependencies['build_context_object'].assert_not_called()


def test_handler_db_project_inactive(mock_dependencies, sample_apigw_event, base_mock_payload):
    """Test handler returns error when get_company_config returns PROJECT_INACTIVE."""
    mock_error = dynamodb_service.PROJECT_INACTIVE
    mock_dependencies['parse_request_body'].return_value = base_mock_payload
    mock_dependencies['validate_initiate_request'].return_value = None
    mock_dependencies['get_company_config'].return_value = mock_error
    expected_error_resp = {'statusCode': 403, 'body': 'Inactive Error'}
    mock_dependencies['create_error_response'].return_value = expected_error_resp

    result = index.lambda_handler(sample_apigw_event, None)

    assert result == expected_error_resp
    mock_dependencies['create_error_response'].assert_called_once_with(
        error_code=mock_error[0],
        error_message=mock_error[1],
        request_id=base_mock_payload['request_data']['request_id'],
        status_code_hint=403 # Added hint
    )
    mock_dependencies['build_context_object'].assert_not_called()


def test_handler_channel_not_allowed(mock_dependencies, sample_apigw_event, base_mock_payload, base_mock_config):
    """Test handler returns error when channel_method is not in allowed_channels."""
    base_mock_payload['request_data']['channel_method'] = 'email'
    base_mock_config['allowed_channels'] = ['whatsapp', 'sms']
    expected_error_resp = {'statusCode': 403, 'body': 'Channel Not Allowed'}
    mock_dependencies['create_error_response'].return_value = expected_error_resp
    mock_dependencies['parse_request_body'].return_value = base_mock_payload
    mock_dependencies['validate_initiate_request'].return_value = None
    mock_dependencies['get_company_config'].return_value = base_mock_config

    result = index.lambda_handler(sample_apigw_event, None)

    assert result == expected_error_resp
    mock_dependencies['create_error_response'].assert_called_once_with(
        error_code='CHANNEL_NOT_ALLOWED',
        error_message=ANY,
        request_id=base_mock_payload['request_data']['request_id'],
        status_code_hint=403 # Added hint
    )
    mock_dependencies['build_context_object'].assert_not_called()


def test_handler_sqs_send_fails(mock_dependencies, sample_apigw_event, base_mock_payload, base_mock_config):
    """Test handler returns error when send_message_to_queue returns False."""
    mock_context = {'built': 'context'}
    expected_error_resp = {'statusCode': 500, 'body': 'SQS Error'}
    mock_dependencies['create_error_response'].return_value = expected_error_resp
    mock_dependencies['parse_request_body'].return_value = base_mock_payload
    mock_dependencies['validate_initiate_request'].return_value = None
    mock_dependencies['get_company_config'].return_value = base_mock_config
    mock_dependencies['build_context_object'].return_value = mock_context
    mock_dependencies['send_message_to_queue'].return_value = False # Simulate failure

    result = index.lambda_handler(sample_apigw_event, None)

    assert result == expected_error_resp
    mock_dependencies['send_message_to_queue'].assert_called_once() # Check it was called
    mock_dependencies['create_error_response'].assert_called_once_with(
        error_code='QUEUE_ERROR', # Corrected expected error code
        error_message=ANY,
        request_id=base_mock_payload['request_data']['request_id'],
        status_code_hint=500 # Added hint
    )
    mock_dependencies['create_success_response'].assert_not_called()


@pytest.mark.parametrize("channel, expected_url_env_var", [
    ("whatsapp", "WHATSAPP_QUEUE_URL"),
    ("email", "EMAIL_QUEUE_URL"),
    ("sms", "SMS_QUEUE_URL"),
])
def test_handler_correct_queue_url(mock_dependencies, sample_apigw_event, base_mock_payload, base_mock_config, channel, expected_url_env_var):
    """Test that the correct queue URL is selected based on channel_method."""
    base_mock_payload['request_data']['channel_method'] = channel
    mock_context = {'built': 'context'}
    mock_success_resp = {'statusCode': 200, 'body': 'Success'}
    mock_dependencies['parse_request_body'].return_value = base_mock_payload
    mock_dependencies['validate_initiate_request'].return_value = None
    mock_dependencies['get_company_config'].return_value = base_mock_config
    mock_dependencies['build_context_object'].return_value = mock_context
    mock_dependencies['send_message_to_queue'].return_value = True
    mock_dependencies['create_success_response'].return_value = mock_success_resp

    index.lambda_handler(sample_apigw_event, None)

    # Assert send_message_to_queue was called with the correct URL from mocked env vars
    # Use os.environ.get directly as it's mocked by patch.dict now
    expected_queue_url = os.environ.get(expected_url_env_var)

    mock_dependencies['send_message_to_queue'].assert_called_once_with(
        expected_queue_url,
        mock_context,
        channel
    )
    # Make sure success path was taken
    mock_dependencies['create_success_response'].assert_called_once()
    mock_dependencies['create_error_response'].assert_not_called()


def test_handler_unknown_queue_url(mock_dependencies, sample_apigw_event, base_mock_payload, base_mock_config):
    """Test handler returns error if channel is valid but queue URL env var is missing."""
    base_mock_payload['request_data']['channel_method'] = 'fax'
    base_mock_config['allowed_channels'].append('fax')
    expected_error_resp = {'statusCode': 500, 'body': 'Config Error'}
    mock_dependencies['create_error_response'].return_value = expected_error_resp
    mock_dependencies['parse_request_body'].return_value = base_mock_payload
    mock_dependencies['validate_initiate_request'].return_value = None
    mock_dependencies['get_company_config'].return_value = base_mock_config

    result = index.lambda_handler(sample_apigw_event, None)

    assert result == expected_error_resp
    mock_dependencies['create_error_response'].assert_called_once_with(
        error_code='CONFIGURATION_ERROR',
        error_message=ANY,
        request_id=base_mock_payload['request_data']['request_id'],
        status_code_hint=500 # Added hint
    )
    mock_dependencies['send_message_to_queue'].assert_not_called() 