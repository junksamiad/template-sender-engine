import pytest
import json
import base64
# Import the utils module directly
from src_dev.channel_router.lambda import utils

# --- Test Fixtures (Example Structure) ---
# You might create fixtures later in conftest.py for shared setup

# --- Test Cases ---

def test_parse_valid_json_body():
    """Test parsing a standard valid JSON body."
    valid_payload = {"key": "value", "number": 123}
    event = {
        "body": json.dumps(valid_payload),
        "isBase64Encoded": False
    }
    
    parsed_body = utils.request_parser.parse_request_body(event)
    
    assert parsed_body is not None
    assert parsed_body == valid_payload

def test_parse_missing_body():
    """Test event with missing body key."""
    event = {
        "isBase64Encoded": False
        # 'body' key is missing
    }
    
    parsed_body = utils.request_parser.parse_request_body(event)
    
    assert parsed_body is None

def test_parse_none_body():
    """Test event with body key set to None."""
    event = {
        "body": None,
        "isBase64Encoded": False
    }
    
    parsed_body = utils.request_parser.parse_request_body(event)
    
    assert parsed_body is None

def test_parse_empty_string_body():
    """Test event with body as an empty string."""
    event = {
        "body": "",
        "isBase64Encoded": False
    }
    
    parsed_body = utils.request_parser.parse_request_body(event)
    
    assert parsed_body is None

def test_parse_whitespace_string_body():
    """Test event with body as only whitespace."""
    event = {
        "body": "   \n  \t ",
        "isBase64Encoded": False
    }
    
    parsed_body = utils.request_parser.parse_request_body(event)
    
    assert parsed_body is None

def test_parse_invalid_json_body():
    """Test event with invalid JSON string in body."""
    event = {
        "body": "{\"key": "value\",", # Invalid JSON (trailing comma)
        "isBase64Encoded": False
    }
    
    parsed_body = utils.request_parser.parse_request_body(event)
    
    assert parsed_body is None

def test_parse_valid_base64_encoded_body():
    """Test parsing a valid Base64 encoded JSON body."""
    valid_payload = {"message": "hello world"}
    payload_str = json.dumps(valid_payload)
    encoded_body = base64.b64encode(payload_str.encode('utf-8')).decode('utf-8')
    
    event = {
        "body": encoded_body,
        "isBase64Encoded": True
    }
    
    parsed_body = utils.request_parser.parse_request_body(event)
    
    assert parsed_body is not None
    assert parsed_body == valid_payload

def test_parse_invalid_base64_encoding():
    """Test event flagged as Base64 but with invalid encoding."""
    event = {
        "body": "this is not valid base64!@#$",
        "isBase64Encoded": True
    }
    
    parsed_body = utils.request_parser.parse_request_body(event)
    
    assert parsed_body is None

def test_parse_non_string_body():
    """Test event where body is not a string (e.g., already parsed dict)."""
    event = {
        "body": {"key": "value"}, # Body is already a dict
        "isBase64Encoded": False
    }
    
    parsed_body = utils.request_parser.parse_request_body(event)
    
    assert parsed_body is None # Function expects a string body 