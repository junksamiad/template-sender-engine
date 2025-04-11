# tests/unit/channel_router/services/test_dynamodb_service.py

import pytest
import os
import boto3
# from moto import mock_aws # Use new decorator style
from moto import mock_dynamodb # Use specific decorator for moto 4.x
from decimal import Decimal
# import sys # Removed
from unittest.mock import patch, MagicMock # Keep patch for env var test
from botocore.exceptions import ClientError # Import ClientError
from importlib import reload

# Add src_dev parent directory to sys.path - REMOVED
# Need to ensure pytest can find the src_dev module structure - REMOVED
# module_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))
# if module_dir not in sys.path:
#     sys.path.insert(0, module_dir)

# Now import the module/functions to test
# Import AFTER potentially modifying sys.path and setting env vars - REMOVED
from src_dev.channel_router.app.lambda_pkg.services import dynamodb_service # Updated path
# Import error constants directly if needed, using the updated path
from src_dev.channel_router.app.lambda_pkg.services.dynamodb_service import (
    replace_decimals,
    get_company_config,
    COMPANY_NOT_FOUND, # Example error code
    PROJECT_INACTIVE, # Example error code
    DATABASE_ERROR, # Example error code
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
    # with mock_aws():
    with mock_dynamodb(): # Use specific decorator
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
        # Yield the Table object directly
        yield table

# Removed autouse fixture for setting env var and reloading
# @pytest.fixture(autouse=True)
# def set_env_var_and_reload_module(monkeypatch):
#     ...

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

    # Pass the table fixture to the function
    result = dynamodb_service.get_company_config(
        TEST_COMPANY_ID, TEST_PROJECT_ID, ddb_table=dynamodb_table
    )

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
    # Pass the table fixture
    result = dynamodb_service.get_company_config(
        'non-existent-comp', 'non-existent-proj', ddb_table=dynamodb_table
    )
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

    # Pass the table fixture
    result = dynamodb_service.get_company_config(
        TEST_COMPANY_ID, TEST_PROJECT_ID, ddb_table=dynamodb_table
    )
    assert result == PROJECT_INACTIVE

def test_get_company_config_no_table_env_var():
    """Test behavior when env var is not set and no table is passed."""
    # Ensure env var is not set for this test only
    with patch.dict(os.environ, {}, clear=True):
        # Call without passing a table - should try to init and fail
        result = dynamodb_service.get_company_config(TEST_COMPANY_ID, TEST_PROJECT_ID)
        assert result == CONFIGURATION_ERROR

# Note: Testing specific ClientErrors is harder with moto's high-level API,
# but we trust moto handles the underlying calls. The DATABASE_ERROR path
# for general exceptions is implicitly covered if boto3/moto fails internally.
# To specifically test the DATABASE_ERROR return on ClientError, we can patch get_item:

def test_get_company_config_client_error(dynamodb_table):
    """Test DATABASE_ERROR return on generic ClientError."""
    # Patch the get_item method of the *mocked* table object
    with patch.object(dynamodb_table, 'get_item') as mock_get:
        error_response = {'Error': {'Code': 'SomeDynamoError', 'Message': 'Something failed'}}
        mock_get.side_effect = ClientError(error_response, 'GetItem')

        # Pass the table fixture
        result = dynamodb_service.get_company_config(
            TEST_COMPANY_ID, TEST_PROJECT_ID, ddb_table=dynamodb_table
        )
        assert result == DATABASE_ERROR
        mock_get.assert_called_once() 