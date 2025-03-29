"""
AWS Secrets Manager integration module.

This module provides utilities for interacting with AWS Secrets Manager
to create, retrieve, update, and delete secrets.
"""

import json
import logging
from typing import Dict, Optional, Any, Union
import boto3
from botocore.exceptions import ClientError

from src.shared.logging import get_logger
from src.shared.secrets.reference import (
    SecretReference, SecretType, Credentials,
    validate_credential_structure
)

# Configure logger
logger = get_logger(__name__)


class SecretsManagerError(Exception):
    """Base exception for Secrets Manager operations."""
    pass


class SecretNotFoundError(SecretsManagerError):
    """Raised when a secret is not found."""
    pass


class SecretInvalidFormatError(SecretsManagerError):
    """Raised when a secret has an invalid format."""
    pass


class SecretsManager:
    """
    AWS Secrets Manager client wrapper.
    
    This class provides methods for interacting with AWS Secrets Manager
    using the reference-based credential management approach.
    """
    
    def __init__(self, region_name: Optional[str] = None):
        """
        Initialize the Secrets Manager client.
        
        Args:
            region_name: AWS region name (optional, uses default if not provided)
        """
        self.client = boto3.client('secretsmanager', region_name=region_name)
    
    def get_secret(self, reference: str, timeout: int = 5) -> Credentials:
        """
        Retrieve a secret by its reference.
        
        Args:
            reference: The secret reference
            timeout: Timeout in seconds for the API call (default: 5)
            
        Returns:
            Secret value as a typed dictionary
            
        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretInvalidFormatError: If the secret has an invalid format
            SecretsManagerError: For other failures
        """
        # Validate reference format
        if not SecretReference.is_valid_reference(reference):
            raise ValueError(f"Invalid secret reference format: {reference}")
        
        # Parse reference to determine secret type
        secret_ref = SecretReference.from_string(reference)
        
        try:
            response = self.client.get_secret_value(SecretId=reference)
            
            # Parse the secret string
            if 'SecretString' in response:
                secret_value = json.loads(response['SecretString'])
            elif 'SecretBinary' in response:
                # Binary secrets are not supported/expected in our system
                raise SecretInvalidFormatError(
                    f"Binary secrets not supported: {reference}"
                )
            else:
                raise SecretInvalidFormatError(
                    f"Secret response has no value: {reference}"
                )
            
            # Validate that the secret has the required fields for its type
            if not validate_credential_structure(secret_value, secret_ref.secret_type):
                missing_fields = set(
                    SecretReference.get_required_fields(secret_ref.secret_type)
                ) - set(secret_value.keys())
                raise SecretInvalidFormatError(
                    f"Secret {reference} is missing required fields: {missing_fields}"
                )
            
            return secret_value
        
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'ResourceNotFoundException':
                raise SecretNotFoundError(f"Secret not found: {reference}")
            elif error_code == 'DecryptionFailureException':
                raise SecretsManagerError(
                    f"Unable to decrypt secret: {reference}"
                )
            elif error_code == 'InternalServiceError':
                raise SecretsManagerError(
                    f"Internal service error accessing secret: {reference}"
                )
            else:
                raise SecretsManagerError(
                    f"Error accessing secret {reference}: {error_code}"
                )
    
    def create_secret(
        self,
        reference: str,
        value: Dict[str, Any],
        description: Optional[str] = None
    ) -> str:
        """
        Create a new secret.
        
        Args:
            reference: The secret reference
            value: The secret value as a dictionary
            description: Optional description for the secret
            
        Returns:
            ARN of the created secret
            
        Raises:
            ValueError: If the reference is invalid or the value doesn't match requirements
            SecretsManagerError: For failures during secret creation
        """
        # Validate reference format
        if not SecretReference.is_valid_reference(reference):
            raise ValueError(f"Invalid secret reference format: {reference}")
        
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
        
        # Create keyword arguments for the create_secret call
        create_args = {
            'Name': reference,
            'SecretString': json.dumps(value)
        }
        
        if description:
            create_args['Description'] = description
        
        try:
            response = self.client.create_secret(**create_args)
            logger.info(
                f"Created secret {reference}",
                extra={"secret_type": secret_ref.secret_type.name}
            )
            return response['ARN']
        
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'ResourceExistsException':
                raise SecretsManagerError(f"Secret already exists: {reference}")
            else:
                raise SecretsManagerError(
                    f"Error creating secret {reference}: {error_code}"
                )
    
    def update_secret(self, reference: str, value: Dict[str, Any]) -> str:
        """
        Update an existing secret.
        
        Args:
            reference: The secret reference
            value: The new secret value as a dictionary
            
        Returns:
            ARN of the updated secret
            
        Raises:
            SecretNotFoundError: If the secret doesn't exist
            ValueError: If the value doesn't match requirements
            SecretsManagerError: For other failures
        """
        # Validate reference format
        if not SecretReference.is_valid_reference(reference):
            raise ValueError(f"Invalid secret reference format: {reference}")
        
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
        
        try:
            response = self.client.update_secret(
                SecretId=reference,
                SecretString=json.dumps(value)
            )
            logger.info(
                f"Updated secret {reference}",
                extra={"secret_type": secret_ref.secret_type.name}
            )
            return response['ARN']
        
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'ResourceNotFoundException':
                raise SecretNotFoundError(f"Secret not found: {reference}")
            else:
                raise SecretsManagerError(
                    f"Error updating secret {reference}: {error_code}"
                )
    
    def delete_secret(
        self, 
        reference: str, 
        recovery_window_days: int = 30
    ) -> None:
        """
        Delete a secret.
        
        Args:
            reference: The secret reference
            recovery_window_days: Days to keep the secret recoverable (0 for immediate, permanent deletion)
            
        Raises:
            SecretNotFoundError: If the secret doesn't exist
            SecretsManagerError: For other failures
        """
        # Validate reference format
        if not SecretReference.is_valid_reference(reference):
            raise ValueError(f"Invalid secret reference format: {reference}")
        
        try:
            delete_args = {
                'SecretId': reference,
            }
            
            if recovery_window_days > 0:
                delete_args['RecoveryWindowInDays'] = recovery_window_days
            else:
                delete_args['ForceDeleteWithoutRecovery'] = True
            
            self.client.delete_secret(**delete_args)
            logger.info(f"Deleted secret {reference}")
        
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'ResourceNotFoundException':
                raise SecretNotFoundError(f"Secret not found: {reference}")
            else:
                raise SecretsManagerError(
                    f"Error deleting secret {reference}: {error_code}"
                )


# Singleton instance for easy access
_secrets_manager = None


def get_secrets_manager(region_name: Optional[str] = None) -> SecretsManager:
    """
    Get a singleton instance of the SecretsManager.
    
    Args:
        region_name: AWS region name (optional)
        
    Returns:
        SecretsManager instance
    """
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager(region_name)
    return _secrets_manager 