# tests/unit/channel_router/utils/test_request_parser.py

import pytest
import json
import base64
import sys
import os

# Import the function to test
# Assuming the source code is now in src_dev/channel_router/app/...
from src_dev.channel_router.app.utils.request_parser import parse_request_body

# --- Test Data ---
VALID_PAYLOAD_DICT = {"key": "value", "number": 123}
VALID_PAYLOAD_JSON = json.dumps(VALID_PAYLOAD_DICT)
VALID_PAYLOAD_BASE64 = base64.b64encode(VALID_PAYLOAD_JSON.encode('utf-8')).decode('utf-8')

# --- Test Cases ---

def test_parse_valid_json_body_no_base64():
    """Test parsing a valid JSON body, not Base64 encoded."""
    event = {
        "body": VALID_PAYLOAD_JSON,
        "isBase64Encoded": False
    }
    result = parse_request_body(event)
    assert result == VALID_PAYLOAD_DICT

def test_parse_valid_json_body_with_base64():
    """Test parsing a valid JSON body that IS Base64 encoded."""
    event = {
        "body": VALID_PAYLOAD_BASE64,
        "isBase64Encoded": True
    }
    result = parse_request_body(event)
    assert result == VALID_PAYLOAD_DICT

def test_parse_body_missing():
    """Test parsing when 'body' key is missing or None."""
    event_missing = {"isBase64Encoded": False}
    event_none = {"body": None, "isBase64Encoded": False}
    assert parse_request_body(event_missing) is None
    assert parse_request_body(event_none) is None

def test_parse_body_empty_string():
    """Test parsing when body is an empty string."""
    event = {"body": "", "isBase64Encoded": False}
    assert parse_request_body(event) is None

def test_parse_body_whitespace_string():
    """Test parsing when body is only whitespace."""
    event = {"body": "   \n \t ", "isBase64Encoded": False}
    assert parse_request_body(event) is None

def test_parse_body_not_json_no_base64():
    """Test parsing when body is not valid JSON (not Base64 encoded)."""
    event = {"body": "this is not json", "isBase64Encoded": False}
    assert parse_request_body(event) is None

def test_parse_body_invalid_base64():
    """Test parsing invalid Base64 when isBase64Encoded is True."""
    event = {"body": "this is invalid base64!@#", "isBase64Encoded": True}
    assert parse_request_body(event) is None

def test_parse_body_not_json_with_base64():
    """Test parsing valid Base64 containing non-JSON content."""
    not_json_base64 = base64.b64encode(b"this is not json").decode('utf-8')
    event = {"body": not_json_base64, "isBase64Encoded": True}
    assert parse_request_body(event) is None

def test_parse_non_string_body():
    """Test parsing when the body is not a string."""
    event_dict = {"body": {"a": 1}, "isBase64Encoded": False}
    event_int = {"body": 123, "isBase64Encoded": False}
    assert parse_request_body(event_dict) is None
    assert parse_request_body(event_int) is None

def test_parse_with_other_event_keys():
    """Test parsing works correctly with other event keys present."""
    event = {
        "resource": "/initiate-conversation",
        "path": "/initiate-conversation",
        "httpMethod": "POST",
        "headers": {"Content-Type": "application/json", "x-api-key": "dummy"},
        "body": VALID_PAYLOAD_JSON,
        "isBase64Encoded": False,
        "queryStringParameters": None
    }
    result = parse_request_body(event)
    assert result == VALID_PAYLOAD_DICT

def test_parse_body_is_json_null():
    """Test parsing when the body is the JSON literal 'null'."""
    event_no_base64 = {"body": "null", "isBase64Encoded": False}
    event_base64 = {"body": base64.b64encode(b"null").decode('utf-8'), "isBase64Encoded": True}
    # json.loads("null") results in None
    assert parse_request_body(event_no_base64) is None
    assert parse_request_body(event_base64) is None

def test_parse_body_is_json_number_or_string():
    """Test parsing when body is a valid JSON number or string (not object)."""
    event_num = {"body": "123", "isBase64Encoded": False}
    event_str = {"body": "\"a string\"", "isBase64Encoded": False}
    # The function should return the parsed primitive if successful,
    # assuming downstream validation handles non-dict types if necessary.
    assert parse_request_body(event_num) == 123
    assert parse_request_body(event_str) == "a string" 