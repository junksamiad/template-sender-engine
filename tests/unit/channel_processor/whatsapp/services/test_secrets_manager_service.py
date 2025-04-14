import pytest
import boto3
import os
import json
# from moto import mock_aws
from moto import mock_secretsmanager # Use specific decorator for moto 4.x
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

# Module to test
from src_dev.channel_processor.whatsapp.app.lambda_pkg.services import secrets_manager_service
# Reload the module to re-initialize client with mocked env vars/moto - REMOVED
from importlib import reload

# --- Constants ---
DUMMY_SECRET_NAME = "test/my/secret"
DUMMY_REGION = "eu-north-1" # Match default in service

# --- Fixtures ---

@pytest.fixture(scope="function", autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = DUMMY_REGION # Set default region for moto
    # Ensure the region used by the service is set if it relies on env var
    os.environ["SECRETS_MANAGER_REGION"] = DUMMY_REGION
    # Reload the service here to ensure client uses mocked region - REMOVED
    # reload(secrets_manager_service)
    yield # Yield control to the test

@pytest.fixture(scope="function")
def secrets_manager_client(aws_credentials):
    """Sets up mocked Secrets Manager client."""
    # with mock_aws():
    with mock_secretsmanager(): # Use specific decorator
        yield boto3.client("secretsmanager", region_name=DUMMY_REGION)

# --- Helper Function ---
def create_secret(client, secret_name, secret_value):
    """Helper to create a secret in mocked Secrets Manager."""
    client.create_secret(Name=secret_name, SecretString=secret_value)

# --- Test Cases ---

def test_get_secret_success(secrets_manager_client):
    """Test successful retrieval and parsing of a JSON secret string."""
    secret_dict = {"api_key": "12345-abcde", "username": "testuser"}
    secret_string = json.dumps(secret_dict)
    # Use the client provided by the fixture
    create_secret(secrets_manager_client, DUMMY_SECRET_NAME, secret_string)

    # Pass the mocked client into the service function
    result = secrets_manager_service.get_secret(DUMMY_SECRET_NAME, sm_client=secrets_manager_client)
    assert result == secret_dict

def test_get_secret_not_found(secrets_manager_client, caplog):
    """Test handling ResourceNotFoundException when secret doesn't exist."""
    # Pass the mocked client
    result = secrets_manager_service.get_secret("non/existent/secret", sm_client=secrets_manager_client)
    assert result is None
    assert f"Secret not found: non/existent/secret" in caplog.text

def test_get_secret_not_json(secrets_manager_client, caplog):
    """Test handling when the secret string is not valid JSON."""
    non_json_string = "this is not json"
    create_secret(secrets_manager_client, DUMMY_SECRET_NAME, non_json_string)

    # Pass the mocked client
    result = secrets_manager_service.get_secret(DUMMY_SECRET_NAME, sm_client=secrets_manager_client)
    assert result is None # Expect None as per function logic
    assert f"Failed to parse secret JSON for: {DUMMY_SECRET_NAME}" in caplog.text

def test_get_secret_access_denied(secrets_manager_client, caplog):
    """Test handling AccessDeniedException (simulated via mock)."""
    error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access Denied'}}
    client_error = ClientError(error_response, 'GetSecretValue')

    # Patch the get_secret_value method on the *mocked client*
    with patch.object(secrets_manager_client, 'get_secret_value', side_effect=client_error):
        # Pass the mocked client
        result = secrets_manager_service.get_secret(DUMMY_SECRET_NAME, sm_client=secrets_manager_client)
        assert result is None
        assert f"Access denied when trying to retrieve secret: {DUMMY_SECRET_NAME}" in caplog.text

def test_get_secret_other_client_error(secrets_manager_client, caplog):
    """Test handling other ClientErrors."""
    error_response = {'Error': {'Code': 'InternalServiceErrorException', 'Message': 'Server error'}}
    client_error = ClientError(error_response, 'GetSecretValue')

    # Patch the get_secret_value method on the *mocked client*
    with patch.object(secrets_manager_client, 'get_secret_value', side_effect=client_error):
        # Pass the mocked client
        result = secrets_manager_service.get_secret(DUMMY_SECRET_NAME, sm_client=secrets_manager_client)
        assert result is None
        assert f"Secrets Manager ClientError retrieving {DUMMY_SECRET_NAME}: Server error" in caplog.text

def test_get_secret_empty_name(secrets_manager_client, caplog):
    """Test providing an empty string for secret name."""
    # Pass the mocked client (though it won't be used due to early return)
    result = secrets_manager_service.get_secret("", sm_client=secrets_manager_client)
    assert result is None
    assert "Attempted to retrieve secret with an empty name/ARN." in caplog.text

# Removed test_get_secret_client_not_initialized as DI handles this scenario
# def test_get_secret_client_not_initialized(caplog):
#     ... 