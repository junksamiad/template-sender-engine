# tests/unit/channel_router/utils/test_validators.py

import pytest
import sys
import os
import uuid
from datetime import datetime, timezone

# Update the import path to reflect the new code structure
from src_dev.channel_router.app.lambda_pkg.utils.validators import validate_initiate_request, SUPPORTED_CHANNELS
# Import any specific custom exceptions if defined in validators.py
# from src_dev.channel_router.app.utils.validators import ValidationFailedError # Example

# --- Test Data ---

def get_valid_payload():
    """Returns a baseline valid payload dictionary."""
    return {
        "company_data": {
            "company_id": "ci-test-123",
            "project_id": "pi-test-abc"
        },
        "recipient_data": {
            "recipient_tel": "+447123456789",
            "recipient_email": "test@example.com", # Include both for generality
            "comms_consent": True
        },
        "request_data": {
            "request_id": str(uuid.uuid4()), # Generate valid UUID
            "channel_method": "whatsapp",
            "initial_request_timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z') # Generate valid timestamp
        },
        "project_data": { # Optional section
            "some_key": "some_value"
        }
    }

# Helper to check for specific error code
def assert_validation_fails(payload: dict, expected_error_code: str):
    result = validate_initiate_request(payload)
    assert result is not None, f"Validation succeeded unexpectedly for expected error '{expected_error_code}'"
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert result[0] == expected_error_code, f"Expected error code '{expected_error_code}', but got '{result[0]}'"
    assert isinstance(result[1], str)

# --- Test Cases ---

def test_validate_valid_payload():
    """Test validation passes with a fully valid payload."""
    payload = get_valid_payload()
    assert validate_initiate_request(payload) is None

def test_validate_valid_payload_no_optional_project_data():
    """Test validation passes when optional 'project_data' is missing."""
    payload = get_valid_payload()
    del payload["project_data"]
    assert validate_initiate_request(payload) is None

def test_validate_valid_payload_different_channels():
    """Test validation passes for all supported channels."""
    for channel in SUPPORTED_CHANNELS:
        payload = get_valid_payload()
        payload["request_data"]["channel_method"] = channel
        # Ensure required recipient info exists for the channel
        if channel != 'email' and 'recipient_tel' not in payload["recipient_data"]:
             payload["recipient_data"]["recipient_tel"] = "+15551234567"
        if channel == 'email' and 'recipient_email' not in payload["recipient_data"]:
             payload["recipient_data"]["recipient_email"] = "email@example.com"
        assert validate_initiate_request(payload) is None, f"Validation failed for channel '{channel}'"

# --- Tests for Missing Sections ---

def test_validate_missing_company_data():
    payload = get_valid_payload()
    del payload["company_data"]
    assert_validation_fails(payload, "MISSING_COMPANY_DATA")

def test_validate_missing_recipient_data():
    payload = get_valid_payload()
    del payload["recipient_data"]
    assert_validation_fails(payload, "MISSING_RECIPIENT_DATA")

def test_validate_missing_request_data():
    payload = get_valid_payload()
    del payload["request_data"]
    assert_validation_fails(payload, "MISSING_REQUEST_DATA")

# --- Tests for Invalid Section Types ---

def test_validate_company_data_not_dict():
    payload = get_valid_payload()
    payload["company_data"] = "not a dict"
    assert_validation_fails(payload, "INVALID_COMPANY_DATA_TYPE")

def test_validate_recipient_data_not_dict():
    payload = get_valid_payload()
    payload["recipient_data"] = ["not a dict"]
    assert_validation_fails(payload, "INVALID_RECIPIENT_DATA_TYPE")

def test_validate_request_data_not_dict():
    payload = get_valid_payload()
    payload["request_data"] = None
    assert_validation_fails(payload, "INVALID_REQUEST_DATA_TYPE")

# --- Tests for Missing Required Fields ---

# Note: company_id/project_id presence checked in index.py Step 2 per validator code
# No explicit tests here for those missing, assuming index catches them earlier.

def test_validate_missing_request_id():
    payload = get_valid_payload()
    del payload["request_data"]["request_id"]
    assert_validation_fails(payload, "MISSING_REQUEST_ID")

def test_validate_missing_channel_method():
    payload = get_valid_payload()
    del payload["request_data"]["channel_method"]
    assert_validation_fails(payload, "MISSING_CHANNEL_METHOD")

def test_validate_missing_timestamp():
    payload = get_valid_payload()
    del payload["request_data"]["initial_request_timestamp"]
    assert_validation_fails(payload, "MISSING_INITIAL_REQUEST_TIMESTAMP")

def test_validate_missing_recipient_tel_for_whatsapp():
    payload = get_valid_payload()
    payload["request_data"]["channel_method"] = "whatsapp"
    del payload["recipient_data"]["recipient_tel"]
    assert_validation_fails(payload, "MISSING_RECIPIENT_TEL")

def test_validate_missing_recipient_tel_for_sms():
    payload = get_valid_payload()
    payload["request_data"]["channel_method"] = "sms"
    del payload["recipient_data"]["recipient_tel"]
    assert_validation_fails(payload, "MISSING_RECIPIENT_TEL")

def test_validate_missing_recipient_email_for_email():
    payload = get_valid_payload()
    payload["request_data"]["channel_method"] = "email"
    del payload["recipient_data"]["recipient_email"]
    assert_validation_fails(payload, "MISSING_RECIPIENT_EMAIL")

def test_validate_missing_comms_consent():
    payload = get_valid_payload()
    del payload["recipient_data"]["comms_consent"]
    assert_validation_fails(payload, "MISSING_COMMS_CONSENT")

# --- Tests for Incorrect Data Types/Format ---

def test_validate_request_id_not_string():
    payload = get_valid_payload()
    payload["request_data"]["request_id"] = 12345
    assert_validation_fails(payload, "INVALID_REQUEST_ID_FORMAT") # Checks for non-empty string first

def test_validate_request_id_empty_string():
    payload = get_valid_payload()
    payload["request_data"]["request_id"] = "   "
    assert_validation_fails(payload, "INVALID_REQUEST_ID_FORMAT")

def test_validate_request_id_invalid_uuid():
    payload = get_valid_payload()
    payload["request_data"]["request_id"] = "not-a-uuid"
    assert_validation_fails(payload, "INVALID_REQUEST_ID")

def test_validate_channel_method_not_string():
    payload = get_valid_payload()
    payload["request_data"]["channel_method"] = True
    assert_validation_fails(payload, "INVALID_CHANNEL_METHOD_FORMAT")

def test_validate_timestamp_not_string():
    payload = get_valid_payload()
    payload["request_data"]["initial_request_timestamp"] = 123.45
    assert_validation_fails(payload, "INVALID_INITIAL_REQUEST_TIMESTAMP_FORMAT")

def test_validate_timestamp_invalid_iso():
    payload = get_valid_payload()
    payload["request_data"]["initial_request_timestamp"] = "2024/01/01 12:00:00"
    assert_validation_fails(payload, "INVALID_TIMESTAMP")

def test_validate_recipient_tel_not_string():
    payload = get_valid_payload()
    payload["request_data"]["channel_method"] = "whatsapp"
    payload["recipient_data"]["recipient_tel"] = 123
    assert_validation_fails(payload, "INVALID_RECIPIENT_TEL")

def test_validate_recipient_email_not_string():
    payload = get_valid_payload()
    payload["request_data"]["channel_method"] = "email"
    payload["recipient_data"]["recipient_email"] = {}
    assert_validation_fails(payload, "INVALID_RECIPIENT_EMAIL")

def test_validate_comms_consent_not_bool():
    payload = get_valid_payload()
    payload["recipient_data"]["comms_consent"] = "true" # String, not boolean
    assert_validation_fails(payload, "INVALID_COMMS_CONSENT_TYPE")

# --- Tests for Invalid Values ---

def test_validate_invalid_channel_method_value():
    payload = get_valid_payload()
    payload["request_data"]["channel_method"] = "telegram"
    assert_validation_fails(payload, "UNSUPPORTED_CHANNEL")

# --- Optional: Test project_data type if present ---
# Based on code, it seems type of project_data isn't checked if present
# def test_validate_project_data_not_dict_if_present():
#     payload = get_valid_payload()
#     payload["project_data"] = "optional but wrong type"
#     # Should this pass or fail? Validator doesn't check optional sections.
#     assert validate_initiate_request(payload) is None # Assuming it passes 