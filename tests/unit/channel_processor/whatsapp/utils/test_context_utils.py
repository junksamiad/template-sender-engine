import pytest
import json
from src_dev.channel_processor.whatsapp.app.lambda_pkg.utils.context_utils import (
    deserialize_context,
    validate_context,
)

# --- Tests for deserialize_context ---

def test_deserialize_context_success():
    """Test successful deserialization of a valid JSON string."""
    context_dict = {"key": "value", "number": 123}
    context_json = json.dumps(context_dict)
    deserialized = deserialize_context(context_json)
    assert deserialized == context_dict

def test_deserialize_context_invalid_json():
    """Test deserialization with invalid JSON string raises ValueError."""
    invalid_json = '{"key": "value"'  # Missing closing brace - Corrected string definition
    with pytest.raises(ValueError, match="Invalid Context JSON string received."):
        deserialize_context(invalid_json)

def test_deserialize_context_not_a_dict():
    """Test deserialization of valid JSON that is not a dictionary raises ValueError."""
    not_a_dict_json = json.dumps([1, 2, 3])  # JSON array
    with pytest.raises(ValueError, match="Deserialized context is not a dictionary."):
        deserialize_context(not_a_dict_json)

def test_deserialize_context_empty_string():
    """Test deserialization with an empty string raises ValueError."""
    with pytest.raises(ValueError, match="Invalid Context JSON string received."):
        deserialize_context("")

# --- Tests for validate_context ---

# Helper function to create a valid context object for testing
def create_valid_context():
    return {
        "metadata": {"some_meta": "data"},
        "frontend_payload": {
            "company_data": {"company_id": "comp_123", "project_id": "proj_456"},
            "recipient_data": {"recipient_tel": "+1234567890"},
            "request_data": {"request_id": "req_789", "channel_method": "whatsapp"}
        },
        "company_data_payload": {
            "channel_config": {
                "whatsapp": {
                    "whatsapp_credentials_id": "cred_abc",
                    "company_whatsapp_number": "+0987654321"
                }
            },
            "ai_config": {
                "openai_config": {
                    "whatsapp": {
                        "api_key_reference": "secret_ref_api_key",
                        "assistant_id_template_sender": "asst_xyz"
                    }
                }
            }
        },
        "conversation_data": {
            "conversation_id": "conv_pqr"
        }
    }

def test_validate_context_success():
    """Test validation succeeds with a complete and valid context object."""
    context = create_valid_context()
    errors = validate_context(context)
    assert not errors  # No errors expected

def test_validate_context_not_a_dictionary():
    """Test validation fails if the input is not a dictionary."""
    errors = validate_context("not_a_dict")
    assert len(errors) == 1
    assert "Context object root is not a dictionary" in errors[0]

def test_validate_context_missing_top_level_key():
    """Test validation fails if a required top-level key is missing."""
    context = create_valid_context()
    del context["frontend_payload"]
    errors = validate_context(context)
    assert any("Missing required top-level key: 'frontend_payload'" in e for e in errors)

def test_validate_context_top_level_key_not_dict():
    """Test validation fails if a top-level key is not a dictionary."""
    context = create_valid_context()
    context["company_data_payload"] = "not_a_dict"
    errors = validate_context(context)
    assert any("Top-level key 'company_data_payload' is not a dictionary" in e for e in errors)

def test_validate_context_missing_nested_keys():
    """Test validation fails for various missing required nested keys."""
    required_paths_and_errors = {
        ("frontend_payload", "company_data", "company_id"): "Missing 'frontend_payload.company_data.company_id'",
        ("frontend_payload", "company_data", "project_id"): "Missing 'frontend_payload.company_data.project_id'",
        ("frontend_payload", "recipient_data", "recipient_tel"): "Missing 'frontend_payload.recipient_data.recipient_tel'",
        ("frontend_payload", "request_data", "request_id"): "Missing 'frontend_payload.request_data.request_id'",
        ("company_data_payload", "channel_config", "whatsapp", "whatsapp_credentials_id"): "Missing 'company_data_payload.channel_config.whatsapp.whatsapp_credentials_id'",
        ("company_data_payload", "channel_config", "whatsapp", "company_whatsapp_number"): "Missing 'company_data_payload.channel_config.whatsapp.company_whatsapp_number'",
        ("company_data_payload", "ai_config", "openai_config", "whatsapp", "api_key_reference"): "Missing 'company_data_payload.ai_config.openai_config.whatsapp.api_key_reference'",
        ("company_data_payload", "ai_config", "openai_config", "whatsapp", "assistant_id_template_sender"): "Missing 'company_data_payload.ai_config.openai_config.whatsapp.assistant_id_template_sender'",
        ("conversation_data", "conversation_id"): "Missing 'conversation_data.conversation_id'",
    }

    for path_keys, expected_error in required_paths_and_errors.items():
        context = create_valid_context()
        # Drill down and delete the key
        temp = context
        for i, key in enumerate(path_keys):
            if i == len(path_keys) - 1:
                if key in temp:
                    del temp[key]
            elif key in temp:
                temp = temp[key]
            else:
                # Parent key missing, this case is covered elsewhere, skip
                break
        else: # Only run validation if the loop completed without break
            errors = validate_context(context)
            assert any(expected_error in e for e in errors), f"Expected error '{expected_error}' not found for missing path {path_keys}"

def test_validate_context_incorrect_channel_method():
    """Test validation fails if channel_method is not 'whatsapp'."""
    context = create_valid_context()
    context["frontend_payload"]["request_data"]["channel_method"] = "email"
    errors = validate_context(context)
    assert any("'frontend_payload.request_data.channel_method' is not 'whatsapp'" in e for e in errors) 