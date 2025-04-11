# tests/unit/channel_router/test_index.py

import pytest
from unittest.mock import patch, MagicMock, ANY
import json
import os
import uuid # Import uuid for mock fixture

# --- Path Setup Removed --- # Handled by pytest.ini

# Import the handler function directly
from src_dev.channel_router.app.index import lambda_handler

# Import specific error codes for assertions (if needed)
# Note: These might not be needed if we mock the db_service correctly
from src_dev.channel_router.app.services import dynamodb_service

# --- Test Fixtures ---

# Environment Variable Fixture (using patch.dict)
@pytest.fixture(scope="function", autouse=True)
def set_router_environment_variables():
    """Sets required environment variables using patch.dict."""
    env_vars = {
        'COMPANY_DATA_TABLE': 'mock-company-table',
        'WHATSAPP_QUEUE_URL': 'mock_whatsapp_url',
        'EMAIL_QUEUE_URL': 'mock_email_url',
        'SMS_QUEUE_URL': 'mock_sms_url',
        'VERSION': 'test-router-1.0',
        'LOG_LEVEL': 'INFO'
    }
    with patch.dict(os.environ, env_vars, clear=True) as patched_env:
        yield patched_env

# Individual Mock Fixtures for Dependencies
@pytest.fixture
def mock_req_parser():
    return MagicMock()

@pytest.fixture
def mock_req_validator():
    mock = MagicMock()
    mock.validate_initiate_request.return_value = None # Default: validation passes
    return mock

@pytest.fixture
def mock_db_service():
    mock = MagicMock()
    # Define specific error constants on the mock if tests rely on them
    mock.COMPANY_NOT_FOUND = dynamodb_service.COMPANY_NOT_FOUND
    mock.PROJECT_INACTIVE = dynamodb_service.PROJECT_INACTIVE
    return mock

@pytest.fixture
def mock_queue_service():
    mock = MagicMock()
    mock.send_message_to_queue.return_value = True # Default: send succeeds
    return mock

@pytest.fixture
def mock_ctx_builder():
    return MagicMock()

@pytest.fixture
def mock_resp_builder():
    mock = MagicMock()
    # Provide default mock returns for response functions
    mock.create_success_response.return_value = {'statusCode': 200, 'body': json.dumps({'message': 'Success', 'request_id': 'mock_req_id'})}
    mock.create_error_response.return_value = {'statusCode': 500, 'body': json.dumps({'error': {'code': 'MOCK_ERROR', 'message': 'Mock error response'}})}
    return mock

@pytest.fixture
def mock_logger():
    return MagicMock()

@pytest.fixture
def mock_id_generator():
    mock = MagicMock()
    mock.uuid4.return_value = uuid.UUID('11111111-1111-1111-1111-111111111111') # Fixed mock UUID
    return mock

# Fixtures for test data
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

def test_lambda_handler_success_path(
    mock_req_parser, mock_req_validator, mock_db_service,
    mock_queue_service, mock_ctx_builder, mock_resp_builder, mock_logger,
    sample_apigw_event, base_mock_payload, base_mock_config
):
    """Test the main handler's successful execution path."""
    mock_context = {'built': 'context'}
    mock_success_resp = {'statusCode': 200, 'body': 'Success Body'}
    mock_req_parser.parse_request_body.return_value = base_mock_payload
    # mock_req_validator already defaults to success
    mock_db_service.get_company_config.return_value = base_mock_config
    mock_ctx_builder.build_context_object.return_value = mock_context
    # mock_queue_service already defaults to success
    mock_resp_builder.create_success_response.return_value = mock_success_resp

    # Call the handler with injected mocks
    result = lambda_handler(
        sample_apigw_event, None,
        req_parser=mock_req_parser,
        req_validator=mock_req_validator,
        db_service=mock_db_service,
        queue_service=mock_queue_service,
        ctx_builder=mock_ctx_builder,
        resp_builder=mock_resp_builder,
        log=mock_logger
        # id_generator will use default mock if not specified
    )

    assert result == mock_success_resp
    mock_req_parser.parse_request_body.assert_called_once_with(sample_apigw_event)
    mock_req_validator.validate_initiate_request.assert_called_once_with(base_mock_payload)
    mock_db_service.get_company_config.assert_called_once_with('c1', 'p1')
    mock_ctx_builder.build_context_object.assert_called_once_with(base_mock_payload, base_mock_config, 'test-router-1.0')
    mock_queue_service.send_message_to_queue.assert_called_once_with('mock_whatsapp_url', mock_context, 'whatsapp')
    mock_resp_builder.create_success_response.assert_called_once_with('req1')
    mock_resp_builder.create_error_response.assert_not_called()
    mock_logger.error.assert_not_called()
    mock_logger.warning.assert_not_called()

def test_handler_parse_fails(
    mock_req_parser, mock_resp_builder, mock_req_validator, mock_logger, mock_id_generator,
    sample_apigw_event
):
    """Test handler returns error when parse_request_body returns None."""
    mock_req_parser.parse_request_body.return_value = None
    expected_error_resp = {'statusCode': 400, 'body': 'Parse Error Response'}
    mock_resp_builder.create_error_response.return_value = expected_error_resp
    fixed_request_id = str(mock_id_generator.uuid4()) # Get the fixed UUID

    result = lambda_handler(
        sample_apigw_event, None,
        req_parser=mock_req_parser,
        resp_builder=mock_resp_builder,
        log=mock_logger,
        id_generator=mock_id_generator # Ensure fixed ID is used
    )

    assert result == expected_error_resp
    mock_resp_builder.create_error_response.assert_called_once_with(
        error_code='INVALID_REQUEST',
        error_message='Invalid or missing request body',
        request_id=fixed_request_id, # Assert the fixed UUID was used
        status_code_hint=400
    )
    mock_req_validator.validate_initiate_request.assert_not_called()

def test_handler_validation_fails(
    mock_req_parser, mock_req_validator, mock_resp_builder, mock_logger,
    sample_apigw_event, base_mock_payload
):
    """Test handler returns error when validate_initiate_request fails."""
    mock_error = ("TEST_VALIDATION_CODE", "Test validation message")
    mock_req_parser.parse_request_body.return_value = base_mock_payload
    mock_req_validator.validate_initiate_request.return_value = mock_error
    expected_error_resp = {'statusCode': 400, 'body': 'Validation Error Response'}
    mock_resp_builder.create_error_response.return_value = expected_error_resp

    result = lambda_handler(
        sample_apigw_event, None,
        req_parser=mock_req_parser,
        req_validator=mock_req_validator,
        resp_builder=mock_resp_builder,
        log=mock_logger
    )

    assert result == expected_error_resp
    mock_resp_builder.create_error_response.assert_called_once_with(
        error_code=mock_error[0],
        error_message=mock_error[1],
        request_id=base_mock_payload['request_data']['request_id'],
        status_code_hint=400
    )

def test_handler_db_config_not_found(
    mock_req_parser, mock_req_validator, mock_db_service, mock_resp_builder, mock_logger,
    sample_apigw_event, base_mock_payload
):
    """Test handler returns error when get_company_config returns COMPANY_NOT_FOUND."""
    mock_error = mock_db_service.COMPANY_NOT_FOUND # Use error from mock
    mock_req_parser.parse_request_body.return_value = base_mock_payload
    mock_db_service.get_company_config.return_value = mock_error
    expected_error_resp = {'statusCode': 404, 'body': 'Not Found Response'}
    mock_resp_builder.create_error_response.return_value = expected_error_resp

    result = lambda_handler(
        sample_apigw_event, None,
        req_parser=mock_req_parser,
        req_validator=mock_req_validator,
        db_service=mock_db_service,
        resp_builder=mock_resp_builder,
        log=mock_logger
    )

    assert result == expected_error_resp
    mock_resp_builder.create_error_response.assert_called_once_with(
        error_code=mock_error[0],
        error_message=mock_error[1],
        request_id=base_mock_payload['request_data']['request_id'],
        status_code_hint=404
    )

def test_handler_db_project_inactive(
    mock_req_parser, mock_req_validator, mock_db_service, mock_resp_builder, mock_logger,
    sample_apigw_event, base_mock_payload
):
    """Test handler returns error when get_company_config returns PROJECT_INACTIVE."""
    mock_error = mock_db_service.PROJECT_INACTIVE # Use error from mock
    mock_req_parser.parse_request_body.return_value = base_mock_payload
    mock_db_service.get_company_config.return_value = mock_error
    expected_error_resp = {'statusCode': 403, 'body': 'Inactive Response'}
    mock_resp_builder.create_error_response.return_value = expected_error_resp

    result = lambda_handler(
        sample_apigw_event, None,
        req_parser=mock_req_parser,
        req_validator=mock_req_validator,
        db_service=mock_db_service,
        resp_builder=mock_resp_builder,
        log=mock_logger
    )

    assert result == expected_error_resp
    mock_resp_builder.create_error_response.assert_called_once_with(
        error_code=mock_error[0],
        error_message=mock_error[1],
        request_id=base_mock_payload['request_data']['request_id'],
        status_code_hint=403
    )

def test_handler_channel_not_allowed(
    mock_req_parser, mock_req_validator, mock_db_service, mock_resp_builder, mock_logger,
    sample_apigw_event, base_mock_payload, base_mock_config
):
    """Test handler returns error when channel_method is not in allowed_channels."""
    base_mock_payload['request_data']['channel_method'] = 'email' # Request email
    base_mock_config['allowed_channels'] = ['whatsapp', 'sms'] # But only allow others
    mock_req_parser.parse_request_body.return_value = base_mock_payload
    mock_db_service.get_company_config.return_value = base_mock_config
    expected_error_resp = {'statusCode': 403, 'body': 'Channel Not Allowed Response'}
    mock_resp_builder.create_error_response.return_value = expected_error_resp

    result = lambda_handler(
        sample_apigw_event, None,
        req_parser=mock_req_parser,
        req_validator=mock_req_validator,
        db_service=mock_db_service,
        resp_builder=mock_resp_builder,
        log=mock_logger
    )

    assert result == expected_error_resp
    mock_resp_builder.create_error_response.assert_called_once_with(
        error_code='CHANNEL_NOT_ALLOWED',
        error_message=ANY, # Message contains the channel name
        request_id=base_mock_payload['request_data']['request_id'],
        status_code_hint=403
    )

def test_handler_sqs_send_fails(
    mock_req_parser, mock_req_validator, mock_db_service,
    mock_queue_service, mock_ctx_builder, mock_resp_builder, mock_logger,
    sample_apigw_event, base_mock_payload, base_mock_config
):
    """Test handler returns error when send_message_to_queue returns False."""
    mock_context = {'built': 'context'}
    mock_req_parser.parse_request_body.return_value = base_mock_payload
    mock_db_service.get_company_config.return_value = base_mock_config
    mock_ctx_builder.build_context_object.return_value = mock_context
    mock_queue_service.send_message_to_queue.return_value = False # Simulate failure
    expected_error_resp = {'statusCode': 500, 'body': 'SQS Error Response'}
    mock_resp_builder.create_error_response.return_value = expected_error_resp

    result = lambda_handler(
        sample_apigw_event, None,
        req_parser=mock_req_parser,
        req_validator=mock_req_validator,
        db_service=mock_db_service,
        queue_service=mock_queue_service,
        ctx_builder=mock_ctx_builder,
        resp_builder=mock_resp_builder,
        log=mock_logger
    )

    assert result == expected_error_resp
    mock_queue_service.send_message_to_queue.assert_called_once() # Check it was called
    mock_resp_builder.create_error_response.assert_called_once_with(
        error_code='QUEUE_ERROR',
        error_message=ANY,
        request_id=base_mock_payload['request_data']['request_id'],
        status_code_hint=500
    )
    mock_resp_builder.create_success_response.assert_not_called()

@pytest.mark.parametrize("channel, expected_url_env_var", [
    ("whatsapp", "WHATSAPP_QUEUE_URL"),
    ("email", "EMAIL_QUEUE_URL"),
    ("sms", "SMS_QUEUE_URL"),
])
def test_handler_correct_queue_url(
    mock_req_parser, mock_req_validator, mock_db_service,
    mock_queue_service, mock_ctx_builder, mock_resp_builder, mock_logger,
    sample_apigw_event, base_mock_payload, base_mock_config,
    channel, expected_url_env_var
):
    """Test that the correct queue URL is selected based on channel_method."""
    base_mock_payload['request_data']['channel_method'] = channel
    mock_context = {'built': 'context'}
    mock_success_resp = {'statusCode': 200, 'body': 'Success Response'}
    mock_req_parser.parse_request_body.return_value = base_mock_payload
    mock_db_service.get_company_config.return_value = base_mock_config
    mock_ctx_builder.build_context_object.return_value = mock_context
    mock_resp_builder.create_success_response.return_value = mock_success_resp

    lambda_handler(
        sample_apigw_event, None,
        req_parser=mock_req_parser,
        req_validator=mock_req_validator,
        db_service=mock_db_service,
        queue_service=mock_queue_service,
        ctx_builder=mock_ctx_builder,
        resp_builder=mock_resp_builder,
        log=mock_logger
    )

    # Assert send_message_to_queue was called with the correct URL from env vars
    expected_queue_url = os.environ.get(expected_url_env_var)
    mock_queue_service.send_message_to_queue.assert_called_once_with(
        expected_queue_url,
        mock_context,
        channel
    )
    mock_resp_builder.create_success_response.assert_called_once()
    mock_resp_builder.create_error_response.assert_not_called()

def test_handler_unknown_queue_url(
    mock_req_parser, mock_req_validator, mock_db_service, mock_resp_builder, mock_logger,
    mock_queue_service,
    sample_apigw_event, base_mock_payload, base_mock_config
):
    """Test handler returns error if channel is valid but queue URL env var is missing."""
    base_mock_payload['request_data']['channel_method'] = 'fax' # Use unsupported channel
    base_mock_config['allowed_channels'].append('fax') # Allow it in config
    mock_req_parser.parse_request_body.return_value = base_mock_payload
    mock_db_service.get_company_config.return_value = base_mock_config
    expected_error_resp = {'statusCode': 500, 'body': 'Config Error Response'}
    mock_resp_builder.create_error_response.return_value = expected_error_resp

    result = lambda_handler(
        sample_apigw_event, None,
        req_parser=mock_req_parser,
        req_validator=mock_req_validator,
        db_service=mock_db_service,
        resp_builder=mock_resp_builder,
        log=mock_logger
    )

    assert result == expected_error_resp
    mock_resp_builder.create_error_response.assert_called_once_with(
        error_code='CONFIGURATION_ERROR',
        error_message=ANY,
        request_id=base_mock_payload['request_data']['request_id'],
        status_code_hint=500
    )
    mock_queue_service.send_message_to_queue.assert_not_called() 