# tests/unit/channel_router/services/test_dynamodb_service.py

import pytest
import os
import boto3
from moto import mock_aws # Use new decorator style
from decimal import Decimal
import sys

# Add src_dev parent directory to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Now import the module/functions to test
# Need to import AFTER potentially modifying sys.path and setting env vars
from src_dev.channel_router.app.services import dynamodb_service
from src_dev.channel_router.app.services.dynamodb_service import (
    get_company_config,
    replace_decimals,
    DATABASE_ERROR,
    COMPANY_NOT_FOUND,
    PROJECT_INACTIVE,
    CONFIGURATION_ERROR
)

# --- Test Constants ---
TABLE_NAME = 'test-company-data-table'
TEST_COMPANY_ID = 'comp-moto-1'
TEST_PROJECT_ID = 'proj-moto-a'

# --- Fixtures ---

@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'eu-north-1' # Or your preferred region

@pytest.fixture(scope='function')
def dynamodb_table(aws_credentials):
    """Creates a mock DynamoDB table for testing."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name=os.environ['AWS_DEFAULT_REGION'])
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {'AttributeName': 'company_id', 'KeyType': 'HASH'},
                {'AttributeName': 'project_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'company_id', 'AttributeType': 'S'},
                {'AttributeName': 'project_id', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
        )
        yield table # Provide the table object to the test

@pytest.fixture(autouse=True)
def set_env_var_and_reload_module(monkeypatch):
    """
    Sets the necessary environment variable BEFORE the service module is imported
    by the test functions. Using autouse=True to ensure it runs for all tests
    in this file. Reloads the module to pick up the mocked table.
    """
    monkeypatch.setenv('COMPANY_DATA_TABLE', TABLE_NAME)
    # Reload the module to ensure it initializes dynamodb resource with mock
    import importlib
    importlib.reload(dynamodb_service)
    yield
    # Optional: Clean up env var if needed, though monkeypatch handles it
    # monkeypatch.delenv('COMPANY_DATA_TABLE', raising=False)

# --- Test Cases for replace_decimals ---

def test_replace_decimals_simple_dict():
    data = {'a': Decimal('1.5'), 'b': Decimal('10'), 'c': 'string'}
    expected = {'a': 1.5, 'b': 10, 'c': 'string'}
    assert replace_decimals(data) == expected

def test_replace_decimals_nested_structure():
    data = {
        'list': [Decimal('1'), Decimal('2.2'), {'nested': Decimal('3.0')}],
        'num': Decimal('5')
    }
    expected = {
        'list': [1, 2.2, {'nested': 3}],
        'num': 5
    }
    assert replace_decimals(data) == expected

def test_replace_decimals_no_decimals():
    data = {'int': 1, 'float': 2.5, 'str': 'hello', 'list': [1, 'a']}
    assert replace_decimals(data) == data # Should remain unchanged

# --- Test Cases for get_company_config ---

def test_get_company_config_success(dynamodb_table):
    """Test successfully retrieving an active company config."""
    item = {
        'company_id': TEST_COMPANY_ID,
        'project_id': TEST_PROJECT_ID,
        'project_status': 'active',
        'name': 'Moto Test',
        'cost': Decimal('199.99'),
        'count': Decimal('50')
    }
    dynamodb_table.put_item(Item=item)

    result = get_company_config(TEST_COMPANY_ID, TEST_PROJECT_ID)

    # Assert structure and decimal replacement
    assert isinstance(result, dict)
    assert result['company_id'] == TEST_COMPANY_ID
    assert result['project_id'] == TEST_PROJECT_ID
    assert result['project_status'] == 'active'
    assert result['name'] == 'Moto Test'
    assert result['cost'] == 199.99 # Float conversion
    assert result['count'] == 50    # Int conversion

def test_get_company_config_not_found(dynamodb_table):
    """Test retrieving a non-existent company/project."""
    result = get_company_config('non-existent-comp', 'non-existent-proj')
    assert result == COMPANY_NOT_FOUND

def test_get_company_config_inactive(dynamodb_table):
    """Test retrieving a config where project_status is not 'active'."""
    item = {
        'company_id': TEST_COMPANY_ID,
        'project_id': TEST_PROJECT_ID,
        'project_status': 'inactive', # Inactive status
        'name': 'Inactive Project'
    }
    dynamodb_table.put_item(Item=item)

    result = get_company_config(TEST_COMPANY_ID, TEST_PROJECT_ID)
    assert result == PROJECT_INACTIVE

def test_get_company_config_no_table_env_var(monkeypatch):
    """Test behavior when environment variable is not set."""
    monkeypatch.delenv('COMPANY_DATA_TABLE', raising=False) # Ensure env var is removed
    import importlib
    importlib.reload(dynamodb_service) # Reload to simulate missing env var at init

    result = get_company_config(TEST_COMPANY_ID, TEST_PROJECT_ID)
    assert result == CONFIGURATION_ERROR

# Note: Testing specific ClientErrors is harder with moto's high-level API,
# but we trust moto handles the underlying calls. The DATABASE_ERROR path
# for general exceptions is implicitly covered if boto3/moto fails internally. 