"""
Unit tests for the Secrets Manager module.

These tests use mocks to avoid actually calling AWS Secrets Manager.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

from src.shared.secrets.manager import (
    SecretsManager, get_secrets_manager,
    SecretNotFoundError, SecretInvalidFormatError, SecretsManagerError
)
from src.shared.secrets.reference import (
    SecretType, create_whatsapp_reference
)


class TestSecretsManager:
    """Tests for the SecretsManager class."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create test references
        self.company_id = "test-company"
        self.project_id = "test-project"
        self.whatsapp_ref = create_whatsapp_reference(self.company_id, self.project_id)
        
        # Create valid secret value
        self.valid_secret = {
            "twilio_account_sid": "AC1234567890abcdef1234567890abcdef",
            "twilio_auth_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
            "twilio_template_sid": "HX1234567890abcdef1234567890abcdef"
        }
    
    @patch('boto3.client')
    def test_get_secret_success(self, mock_boto_client):
        """Test successful secret retrieval."""
        # Set up mock response
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps(self.valid_secret)
        }
        
        # Create SecretsManager instance and get secret
        manager = SecretsManager()
        result = manager.get_secret(self.whatsapp_ref)
        
        # Check results
        assert result == self.valid_secret
        mock_client.get_secret_value.assert_called_once_with(
            SecretId=self.whatsapp_ref
        )
    
    @patch('boto3.client')
    def test_get_secret_not_found(self, mock_boto_client):
        """Test secret not found error."""
        # Set up mock response
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Simulate ResourceNotFoundException
        error_response = {
            'Error': {
                'Code': 'ResourceNotFoundException',
                'Message': 'Secret not found'
            }
        }
        mock_client.get_secret_value.side_effect = ClientError(
            error_response, 'GetSecretValue'
        )
        
        # Create SecretsManager instance and try to get secret
        manager = SecretsManager()
        with pytest.raises(SecretNotFoundError):
            manager.get_secret(self.whatsapp_ref)
    
    @patch('boto3.client')
    def test_get_secret_invalid_format(self, mock_boto_client):
        """Test secret with invalid format."""
        # Set up mock response with invalid secret (missing required fields)
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        invalid_secret = {
            "twilio_account_sid": "AC1234567890abcdef1234567890abcdef"
            # Missing auth_token and template_sid
        }
        
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps(invalid_secret)
        }
        
        # Create SecretsManager instance and try to get secret
        manager = SecretsManager()
        with pytest.raises(SecretInvalidFormatError):
            manager.get_secret(self.whatsapp_ref)
    
    @patch('boto3.client')
    def test_create_secret_success(self, mock_boto_client):
        """Test successful secret creation."""
        # Set up mock response
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        mock_client.create_secret.return_value = {
            'ARN': f'arn:aws:secretsmanager:us-east-1:123456789012:secret:{self.whatsapp_ref}'
        }
        
        # Create SecretsManager instance and create secret
        manager = SecretsManager()
        result = manager.create_secret(
            self.whatsapp_ref,
            self.valid_secret,
            "Test WhatsApp credentials"
        )
        
        # Check results
        assert result == f'arn:aws:secretsmanager:us-east-1:123456789012:secret:{self.whatsapp_ref}'
        mock_client.create_secret.assert_called_once()
        
        # Check args
        args, kwargs = mock_client.create_secret.call_args
        assert kwargs['Name'] == self.whatsapp_ref
        assert json.loads(kwargs['SecretString']) == self.valid_secret
        assert kwargs['Description'] == "Test WhatsApp credentials"
    
    @patch('boto3.client')
    def test_create_secret_invalid_value(self, mock_boto_client):
        """Test creating a secret with invalid value."""
        # Set up mock
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Invalid secret (missing required fields)
        invalid_secret = {
            "twilio_account_sid": "AC1234567890abcdef1234567890abcdef"
            # Missing auth_token and template_sid
        }
        
        # Create SecretsManager instance and try to create secret
        manager = SecretsManager()
        with pytest.raises(ValueError):
            manager.create_secret(
                self.whatsapp_ref,
                invalid_secret,
                "Invalid WhatsApp credentials"
            )
        
        # Ensure create_secret was not called
        mock_client.create_secret.assert_not_called()
    
    @patch('boto3.client')
    def test_create_secret_already_exists(self, mock_boto_client):
        """Test creating a secret that already exists."""
        # Set up mock response
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Simulate ResourceExistsException
        error_response = {
            'Error': {
                'Code': 'ResourceExistsException',
                'Message': 'Secret already exists'
            }
        }
        mock_client.create_secret.side_effect = ClientError(
            error_response, 'CreateSecret'
        )
        
        # Create SecretsManager instance and try to create secret
        manager = SecretsManager()
        with pytest.raises(SecretsManagerError):
            manager.create_secret(
                self.whatsapp_ref,
                self.valid_secret,
                "Test WhatsApp credentials"
            )
    
    @patch('boto3.client')
    def test_update_secret_success(self, mock_boto_client):
        """Test successful secret update."""
        # Set up mock response
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        mock_client.update_secret.return_value = {
            'ARN': f'arn:aws:secretsmanager:us-east-1:123456789012:secret:{self.whatsapp_ref}'
        }
        
        # Create SecretsManager instance and update secret
        manager = SecretsManager()
        result = manager.update_secret(
            self.whatsapp_ref,
            self.valid_secret
        )
        
        # Check results
        assert result == f'arn:aws:secretsmanager:us-east-1:123456789012:secret:{self.whatsapp_ref}'
        mock_client.update_secret.assert_called_once()
        
        # Check args
        args, kwargs = mock_client.update_secret.call_args
        assert kwargs['SecretId'] == self.whatsapp_ref
        assert json.loads(kwargs['SecretString']) == self.valid_secret
    
    @patch('boto3.client')
    def test_delete_secret_success(self, mock_boto_client):
        """Test successful secret deletion."""
        # Set up mock response
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Create SecretsManager instance and delete secret
        manager = SecretsManager()
        manager.delete_secret(
            self.whatsapp_ref, 
            recovery_window_days=7
        )
        
        # Check results
        mock_client.delete_secret.assert_called_once_with(
            SecretId=self.whatsapp_ref,
            RecoveryWindowInDays=7
        )
    
    @patch('boto3.client')
    def test_delete_secret_immediate(self, mock_boto_client):
        """Test immediate secret deletion."""
        # Set up mock response
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Create SecretsManager instance and delete secret
        manager = SecretsManager()
        manager.delete_secret(
            self.whatsapp_ref, 
            recovery_window_days=0
        )
        
        # Check results
        mock_client.delete_secret.assert_called_once_with(
            SecretId=self.whatsapp_ref,
            ForceDeleteWithoutRecovery=True
        )


class TestSingleton:
    """Tests for the singleton pattern."""
    
    @patch('boto3.client')
    def test_get_secrets_manager_singleton(self, mock_boto_client):
        """Test that get_secrets_manager returns a singleton instance."""
        # Clear any existing singleton
        from src.shared.secrets.manager import _secrets_manager
        import src.shared.secrets.manager
        src.shared.secrets.manager._secrets_manager = None
        
        # Get two instances
        manager1 = get_secrets_manager()
        manager2 = get_secrets_manager()
        
        # Check that they are the same instance
        assert manager1 is manager2 