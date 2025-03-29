"""
Mock implementation of AWS Secrets Manager for testing.

This module provides a mock implementation of AWS Secrets Manager
that can be used in tests without requiring actual AWS access.
"""

import json
from typing import Dict, Optional, Any, List
from datetime import datetime

from src.shared.secrets.reference import (
    SecretReference, SecretType, Credentials,
    validate_credential_structure
)
from src.shared.secrets.manager import (
    SecretsManagerError, SecretNotFoundError, SecretInvalidFormatError
)


class MockSecretsManager:
    """
    Mock implementation of AWS Secrets Manager.
    
    This class mimics the behavior of the real SecretsManager class,
    but stores secrets in memory instead of using AWS.
    """
    
    def __init__(self):
        """Initialize with empty secrets dictionary."""
        self.secrets: Dict[str, Dict[str, Any]] = {}
    
    def get_secret(self, reference: str, timeout: int = 5) -> Credentials:
        """
        Retrieve a mock secret by its reference.
        
        Args:
            reference: The secret reference
            timeout: Timeout in seconds for the API call (not used in mock)
            
        Returns:
            Secret value as a typed dictionary
            
        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretInvalidFormatError: If the secret has an invalid format
        """
        # Validate reference format
        if not SecretReference.is_valid_reference(reference):
            raise ValueError(f"Invalid secret reference format: {reference}")
        
        # Check if the secret exists
        if reference not in self.secrets:
            raise SecretNotFoundError(f"Secret not found: {reference}")
        
        # Parse reference to determine secret type
        secret_ref = SecretReference.from_string(reference)
        
        # Get the secret value
        secret_value = self.secrets[reference]['value']
        
        # Validate required fields for this secret type
        if not validate_credential_structure(secret_value, secret_ref.secret_type):
            missing_fields = set(
                SecretReference.get_required_fields(secret_ref.secret_type)
            ) - set(secret_value.keys())
            
            raise SecretInvalidFormatError(
                f"Secret {reference} is missing required fields: {missing_fields}"
            )
        
        return secret_value
    
    def create_secret(
        self,
        reference: str,
        value: Dict[str, Any],
        description: Optional[str] = None
    ) -> str:
        """
        Create a new mock secret.
        
        Args:
            reference: The secret reference
            value: The secret value as a dictionary
            description: Optional description for the secret
            
        Returns:
            ARN of the created secret (mock format)
            
        Raises:
            ValueError: If the reference is invalid or the value doesn't match requirements
            SecretsManagerError: If the secret already exists
        """
        # Validate reference format
        if not SecretReference.is_valid_reference(reference):
            raise ValueError(f"Invalid secret reference format: {reference}")
        
        # Check if the secret already exists
        if reference in self.secrets:
            raise SecretsManagerError(f"Secret already exists: {reference}")
        
        # Parse reference to determine secret type
        secret_ref = SecretReference.from_string(reference)
        
        # Validate that the value has the required fields for this type
        if not validate_credential_structure(value, secret_ref.secret_type):
            missing_fields = set(
                SecretReference.get_required_fields(secret_ref.secret_type)
            ) - set(value.keys())
            
            raise ValueError(
                f"Secret value is missing required fields for {secret_ref.secret_type.name}: "
                f"{missing_fields}"
            )
        
        # Store the secret
        timestamp = datetime.now().isoformat()
        self.secrets[reference] = {
            'value': value,
            'description': description,
            'created_date': timestamp,
            'modified_date': timestamp
        }
        
        # Return a mock ARN
        return f"arn:aws:secretsmanager:us-east-1:123456789012:secret:{reference}"
    
    def update_secret(self, reference: str, value: Dict[str, Any]) -> str:
        """
        Update an existing mock secret.
        
        Args:
            reference: The secret reference
            value: The new secret value as a dictionary
            
        Returns:
            ARN of the updated secret (mock format)
            
        Raises:
            SecretNotFoundError: If the secret doesn't exist
            ValueError: If the value doesn't match requirements
        """
        # Validate reference format
        if not SecretReference.is_valid_reference(reference):
            raise ValueError(f"Invalid secret reference format: {reference}")
        
        # Check if the secret exists
        if reference not in self.secrets:
            raise SecretNotFoundError(f"Secret not found: {reference}")
        
        # Parse reference to determine secret type
        secret_ref = SecretReference.from_string(reference)
        
        # Validate that the value has the required fields for this type
        if not validate_credential_structure(value, secret_ref.secret_type):
            missing_fields = set(
                SecretReference.get_required_fields(secret_ref.secret_type)
            ) - set(value.keys())
            
            raise ValueError(
                f"Secret value is missing required fields for {secret_ref.secret_type.name}: "
                f"{missing_fields}"
            )
        
        # Update the secret
        self.secrets[reference]['value'] = value
        self.secrets[reference]['modified_date'] = datetime.now().isoformat()
        
        # Return a mock ARN
        return f"arn:aws:secretsmanager:us-east-1:123456789012:secret:{reference}"
    
    def delete_secret(
        self, 
        reference: str, 
        recovery_window_days: int = 30
    ) -> None:
        """
        Delete a mock secret.
        
        Args:
            reference: The secret reference
            recovery_window_days: Days to keep the secret recoverable (not used in mock)
            
        Raises:
            SecretNotFoundError: If the secret doesn't exist
        """
        # Validate reference format
        if not SecretReference.is_valid_reference(reference):
            raise ValueError(f"Invalid secret reference format: {reference}")
        
        # Check if the secret exists
        if reference not in self.secrets:
            raise SecretNotFoundError(f"Secret not found: {reference}")
        
        # Delete the secret
        del self.secrets[reference]
    
    def list_secrets(self) -> List[str]:
        """
        List all mock secrets.
        
        Returns:
            List of secret references
        """
        return list(self.secrets.keys())
    
    def reset(self) -> None:
        """Clear all mock secrets."""
        self.secrets = {}


# Create a singleton instance for use in tests
mock_secrets_manager = MockSecretsManager()


def get_mock_secrets_manager() -> MockSecretsManager:
    """
    Get the singleton instance of MockSecretsManager.
    
    Returns:
        MockSecretsManager instance
    """
    return mock_secrets_manager


def mock_whatsapp_credentials(
    account_sid: str = "AC1234567890abcdef1234567890abcdef",
    auth_token: str = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    template_sid: str = "HX1234567890abcdef1234567890abcdef"
) -> Dict[str, str]:
    """
    Create mock WhatsApp credentials.
    
    Args:
        account_sid: Twilio account SID
        auth_token: Twilio auth token
        template_sid: Twilio template SID
        
    Returns:
        WhatsApp credentials dictionary
    """
    return {
        "twilio_account_sid": account_sid,
        "twilio_auth_token": auth_token,
        "twilio_template_sid": template_sid
    }


def mock_sms_credentials(
    account_sid: str = "AC1234567890abcdef1234567890abcdef",
    auth_token: str = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    template_sid: str = "HX1234567890abcdef1234567890abcdef"
) -> Dict[str, str]:
    """
    Create mock SMS credentials.
    
    Args:
        account_sid: Twilio account SID
        auth_token: Twilio auth token
        template_sid: Twilio template SID
        
    Returns:
        SMS credentials dictionary
    """
    return {
        "twilio_account_sid": account_sid,
        "twilio_auth_token": auth_token,
        "twilio_template_sid": template_sid
    }


def mock_email_credentials(
    auth_value: str = "SG.1234567890abcdef1234567890abcdef",
    from_email: str = "no-reply@example.com",
    from_name: str = "Example Company",
    template_id: str = "d-1234567890abcdef1234567890abcdef"
) -> Dict[str, str]:
    """
    Create mock Email credentials.
    
    Args:
        auth_value: SendGrid auth value
        from_email: Sender email address
        from_name: Sender display name
        template_id: SendGrid template ID
        
    Returns:
        Email credentials dictionary
    """
    return {
        "sendgrid_auth_value": auth_value,
        "sendgrid_from_email": from_email,
        "sendgrid_from_name": from_name,
        "sendgrid_template_id": template_id
    }


def mock_ai_credentials(
    api_key: str = "sk-1234567890abcdef1234567890abcdef"
) -> Dict[str, str]:
    """
    Create mock AI credentials.
    
    Args:
        api_key: AI API key
        
    Returns:
        AI credentials dictionary
    """
    return {
        "ai_api_key": api_key
    }


def mock_auth_credentials(
    auth_value: str = "secret-api-key-1234567890"
) -> Dict[str, str]:
    """
    Create mock authentication credentials.
    
    Args:
        auth_value: Authentication value
        
    Returns:
        Authentication credentials dictionary
    """
    return {
        "auth_value": auth_value
    } 