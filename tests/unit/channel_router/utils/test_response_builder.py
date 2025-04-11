# tests/unit/channel_router/utils/test_response_builder.py

import pytest
import json
from datetime import datetime, timezone

# Assuming the source code is now in src_dev/channel_router/app/...
from src_dev.channel_router.app.utils.response_builder import (
    create_success_response,
    create_error_response,
    COMMON_HEADERS
)

# --- Test Cases for create_success_response ---

def test_create_success_response_structure():
    """Test the basic structure and status code of a success response."""
    request_id = "test-req-123"
    response = create_success_response(request_id)

    assert isinstance(response, dict)
    assert response.get('statusCode') == 200
    assert response.get('headers') == COMMON_HEADERS
    assert 'body' in response
    assert isinstance(response['body'], str)

def test_create_success_response_body_content():
    """Test the content of the JSON body in a success response."""
    request_id = "test-req-abc"
    response = create_success_response(request_id)
    body = json.loads(response['body'])

    assert body.get('status') == 'success'
    assert body.get('request_id') == request_id
    assert 'message' in body
    assert isinstance(body['message'], str)
    assert 'queue_timestamp' in body
    # Check timestamp format (loosely)
    try:
        datetime.fromisoformat(body['queue_timestamp'].replace('Z', '+00:00'))
        assert True
    except ValueError:
        pytest.fail("queue_timestamp is not a valid ISO 8601 string")

# --- Test Cases for create_error_response ---

def test_create_error_response_structure():
    """Test the basic structure of an error response."""
    error_code = "TEST_ERROR"
    error_message = "Something went wrong"
    request_id = "err-req-456"
    response = create_error_response(error_code, error_message, request_id)

    assert isinstance(response, dict)
    assert 'statusCode' in response
    assert isinstance(response['statusCode'], int)
    assert response.get('headers') == COMMON_HEADERS
    assert 'body' in response
    assert isinstance(response['body'], str)

def test_create_error_response_body_content():
    """Test the content of the JSON body in an error response."""
    error_code = "MY_CODE"
    error_message = "Detailed message"
    request_id = "err-req-xyz"
    response = create_error_response(error_code, error_message, request_id)
    body = json.loads(response['body'])

    assert body.get('status') == 'error'
    assert body.get('error_code') == error_code
    assert body.get('message') == error_message
    assert body.get('request_id') == request_id

def test_create_error_response_unknown_request_id():
    """Test error response body when request_id is None."""
    error_code = "EARLY_ERROR"
    error_message = "Failed before ID"
    response = create_error_response(error_code, error_message, request_id=None)
    body = json.loads(response['body'])

    assert body.get('request_id') == 'unknown'

def test_create_error_response_status_code_mapping():
    """Test that known error codes map to correct HTTP status codes."""
    test_cases = [
        ("INVALID_REQUEST", 400),
        ("MISSING_IDENTIFIERS", 400),
        ("UNSUPPORTED_CHANNEL", 400),
        ("INVALID_TIMESTAMP", 400),
        ("COMPANY_NOT_FOUND", 404),
        ("PROJECT_INACTIVE", 403),
        ("CHANNEL_NOT_ALLOWED", 403),
        ("UNAUTHORIZED", 401),
        ("RATE_LIMIT_EXCEEDED", 429),
        ("DATABASE_ERROR", 500),
        ("QUEUE_ERROR", 500),
        ("CONFIGURATION_ERROR", 500),
        ("INTERNAL_ERROR", 500),
    ]
    for error_code, expected_status in test_cases:
        response = create_error_response(error_code, "Test message", "req-test")
        assert response.get('statusCode') == expected_status, f"Failed for error code: {error_code}"

def test_create_error_response_status_code_hint():
    """Test that status_code_hint is used for unmapped error codes."""
    error_code = "TOTALLY_NEW_ERROR"
    error_message = "A novel failure"
    request_id = "hint-test"
    hint = 418 # I'm a teapot

    # Test default hint (500)
    response_default = create_error_response(error_code, error_message, request_id)
    assert response_default.get('statusCode') == 500

    # Test provided hint
    response_hinted = create_error_response(error_code, error_message, request_id, status_code_hint=hint)
    assert response_hinted.get('statusCode') == hint 