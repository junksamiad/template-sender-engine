"""
Unit tests for the mock secrets manager module.
"""

import pytest
from src.shared.secrets.mock import (
    get_mock_secrets_manager, 
    mock_whatsapp_credentials, 
    mock_email_credentials,
    mock_sms_credentials,
    mock_ai_credentials,
    mock_auth_credentials
)
from src.shared.secrets.reference import (
    create_whatsapp_reference,
    create_sms_reference,
    create_email_reference,
    create_ai_reference,
    create_auth_reference
)
from src.shared.secrets.manager import (
    SecretNotFoundError,
    SecretInvalidFormatError,
    SecretsManagerError
)


class TestMockSecretsManager:
    """Tests for the MockSecretsManager class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.secrets_manager = get_mock_secrets_manager()
        self.secrets_manager.reset()
        
        # Create test references
        self.company_id = "test-company"
        self.project_id = "test-project"
        self.whatsapp_ref = create_whatsapp_reference(self.company_id, self.project_id)
        self.sms_ref = create_sms_reference(self.company_id, self.project_id)
        self.email_ref = create_email_reference(self.company_id, self.project_id)
        self.ai_ref = create_ai_reference()
        self.auth_ref = create_auth_reference(self.company_id, self.project_id)
    
    def test_create_and_get_secret(self):
        """Test creating and retrieving a secret."""
        # Create WhatsApp credentials
        whatsapp_creds = mock_whatsapp_credentials()
        
        # Store in mock secrets manager
        self.secrets_manager.create_secret(
            self.whatsapp_ref,
            whatsapp_creds,
            "Test WhatsApp credentials"
        )
        
        # Retrieve and validate
        retrieved = self.secrets_manager.get_secret(self.whatsapp_ref)
        assert retrieved == whatsapp_creds
    
    def test_create_secret_invalid_reference(self):
        """Test creating a secret with an invalid reference."""
        with pytest.raises(ValueError):
            self.secrets_manager.create_secret(
                "invalid-reference",
                mock_whatsapp_credentials(),
                "Invalid reference"
            )
    
    def test_create_secret_already_exists(self):
        """Test creating a secret that already exists."""
        # Create the secret first
        self.secrets_manager.create_secret(
            self.whatsapp_ref,
            mock_whatsapp_credentials(),
            "Test WhatsApp credentials"
        )
        
        # Try to create it again
        with pytest.raises(SecretsManagerError):
            self.secrets_manager.create_secret(
                self.whatsapp_ref,
                mock_whatsapp_credentials(),
                "Duplicate WhatsApp credentials"
            )
    
    def test_get_secret_not_found(self):
        """Test retrieving a non-existent secret."""
        with pytest.raises(SecretNotFoundError):
            self.secrets_manager.get_secret(self.whatsapp_ref)
    
    def test_get_secret_invalid_reference(self):
        """Test retrieving a secret with an invalid reference."""
        with pytest.raises(ValueError):
            self.secrets_manager.get_secret("invalid-reference")
    
    def test_get_secret_invalid_structure(self):
        """Test retrieving a secret with an invalid structure."""
        # Create a secret with missing required fields
        invalid_creds = {"twilio_account_sid": "AC1234567890abcdef1234567890abcdef"}
        
        # Directly add to secrets dictionary to bypass validation
        self.secrets_manager.secrets[self.whatsapp_ref] = {
            "value": invalid_creds,
            "description": "Invalid WhatsApp credentials",
            "created_date": "2023-01-01T00:00:00",
            "modified_date": "2023-01-01T00:00:00"
        }
        
        # Try to retrieve it
        with pytest.raises(SecretInvalidFormatError):
            self.secrets_manager.get_secret(self.whatsapp_ref)
    
    def test_update_secret(self):
        """Test updating a secret."""
        # Create initial credentials
        original_creds = mock_whatsapp_credentials(
            account_sid="AC1111111111111111111111111111111",
            auth_token="a1b1c1d1e1f1g1h1i1j1k1l1m1n1o1p1",
            template_sid="HX1111111111111111111111111111111"
        )
        
        # Store in mock secrets manager
        self.secrets_manager.create_secret(
            self.whatsapp_ref,
            original_creds,
            "Original WhatsApp credentials"
        )
        
        # Create updated credentials
        updated_creds = mock_whatsapp_credentials(
            account_sid="AC2222222222222222222222222222222",
            auth_token="a2b2c2d2e2f2g2h2i2j2k2l2m2n2o2p2",
            template_sid="HX2222222222222222222222222222222"
        )
        
        # Update the secret
        self.secrets_manager.update_secret(self.whatsapp_ref, updated_creds)
        
        # Retrieve and validate
        retrieved = self.secrets_manager.get_secret(self.whatsapp_ref)
        assert retrieved == updated_creds
        assert retrieved != original_creds
    
    def test_update_secret_not_found(self):
        """Test updating a non-existent secret."""
        with pytest.raises(SecretNotFoundError):
            self.secrets_manager.update_secret(
                self.whatsapp_ref,
                mock_whatsapp_credentials()
            )
    
    def test_delete_secret(self):
        """Test deleting a secret."""
        # Create the secret first
        self.secrets_manager.create_secret(
            self.whatsapp_ref,
            mock_whatsapp_credentials(),
            "Test WhatsApp credentials"
        )
        
        # Verify it exists
        assert self.whatsapp_ref in self.secrets_manager.secrets
        
        # Delete it
        self.secrets_manager.delete_secret(self.whatsapp_ref)
        
        # Verify it's gone
        assert self.whatsapp_ref not in self.secrets_manager.secrets
        
        # Verify get_secret raises an error
        with pytest.raises(SecretNotFoundError):
            self.secrets_manager.get_secret(self.whatsapp_ref)
    
    def test_delete_secret_not_found(self):
        """Test deleting a non-existent secret."""
        with pytest.raises(SecretNotFoundError):
            self.secrets_manager.delete_secret(self.whatsapp_ref)
    
    def test_list_secrets(self):
        """Test listing all secrets."""
        # Should be empty initially
        assert len(self.secrets_manager.list_secrets()) == 0
        
        # Add some secrets
        self.secrets_manager.create_secret(
            self.whatsapp_ref,
            mock_whatsapp_credentials(),
            "Test WhatsApp credentials"
        )
        
        self.secrets_manager.create_secret(
            self.email_ref,
            mock_email_credentials(),
            "Test Email credentials"
        )
        
        # List should contain both secrets
        secret_list = self.secrets_manager.list_secrets()
        assert len(secret_list) == 2
        assert self.whatsapp_ref in secret_list
        assert self.email_ref in secret_list
    
    def test_reset(self):
        """Test resetting the mock secrets manager."""
        # Add some secrets
        self.secrets_manager.create_secret(
            self.whatsapp_ref,
            mock_whatsapp_credentials(),
            "Test WhatsApp credentials"
        )
        
        self.secrets_manager.create_secret(
            self.email_ref,
            mock_email_credentials(),
            "Test Email credentials"
        )
        
        # Verify they exist
        assert len(self.secrets_manager.list_secrets()) == 2
        
        # Reset
        self.secrets_manager.reset()
        
        # Verify they're gone
        assert len(self.secrets_manager.list_secrets()) == 0


class TestMockCredentials:
    """Tests for the mock credential helper functions."""
    
    def test_mock_whatsapp_credentials(self):
        """Test creating mock WhatsApp credentials."""
        creds = mock_whatsapp_credentials(
            account_sid="AC1234567890abcdef1234567890abcdef",
            auth_token="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
            template_sid="HX1234567890abcdef1234567890abcdef"
        )
        
        assert creds["twilio_account_sid"] == "AC1234567890abcdef1234567890abcdef"
        assert creds["twilio_auth_token"] == "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
        assert creds["twilio_template_sid"] == "HX1234567890abcdef1234567890abcdef"
    
    def test_mock_sms_credentials(self):
        """Test creating mock SMS credentials."""
        creds = mock_sms_credentials(
            account_sid="AC1234567890abcdef1234567890abcdef",
            auth_token="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
            template_sid="HX1234567890abcdef1234567890abcdef"
        )
        
        assert creds["twilio_account_sid"] == "AC1234567890abcdef1234567890abcdef"
        assert creds["twilio_auth_token"] == "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
        assert creds["twilio_template_sid"] == "HX1234567890abcdef1234567890abcdef"
    
    def test_mock_email_credentials(self):
        """Test creating mock Email credentials."""
        creds = mock_email_credentials(
            auth_value="SG.1234567890abcdef1234567890abcdef",
            from_email="no-reply@example.com",
            from_name="Example Company",
            template_id="d-1234567890abcdef1234567890abcdef"
        )
        
        assert creds["sendgrid_auth_value"] == "SG.1234567890abcdef1234567890abcdef"
        assert creds["sendgrid_from_email"] == "no-reply@example.com"
        assert creds["sendgrid_from_name"] == "Example Company"
        assert creds["sendgrid_template_id"] == "d-1234567890abcdef1234567890abcdef"
    
    def test_mock_ai_credentials(self):
        """Test creating mock AI credentials."""
        creds = mock_ai_credentials(
            api_key="sk-1234567890abcdef1234567890abcdef"
        )
        
        assert creds["ai_api_key"] == "sk-1234567890abcdef1234567890abcdef"
    
    def test_mock_auth_credentials(self):
        """Test creating mock authentication credentials."""
        creds = mock_auth_credentials(
            auth_value="secret-api-key-1234567890"
        )
        
        assert creds["auth_value"] == "secret-api-key-1234567890" 