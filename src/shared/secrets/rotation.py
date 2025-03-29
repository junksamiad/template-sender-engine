"""
Secret rotation utilities.

This module provides utilities for rotating secrets in AWS Secrets Manager.
"""

import json
import logging
from typing import Dict, Any, Optional, List
import datetime

from src.shared.logging import get_logger
from src.shared.secrets.reference import SecretReference
from src.shared.secrets.manager import (
    get_secrets_manager, SecretsManager, 
    SecretNotFoundError, SecretsManagerError
)

# Configure logger
logger = get_logger(__name__)


class RotationError(Exception):
    """Exception raised for rotation failures."""
    pass


def rotate_secret(
    reference: str,
    new_value: Dict[str, Any],
    backup_days: int = 7,
    description: Optional[str] = None
) -> str:
    """
    Rotate a secret by creating a new version and backing up the old one.
    
    Args:
        reference: The secret reference
        new_value: The new secret value
        backup_days: Days to keep the backup (default: 7)
        description: Optional description for the secret
        
    Returns:
        ARN of the updated secret
        
    Raises:
        RotationError: If rotation fails
    """
    # Validate reference format
    if not SecretReference.is_valid_reference(reference):
        raise ValueError(f"Invalid secret reference format: {reference}")
    
    # Get secrets manager
    secrets_manager = get_secrets_manager()
    
    # Create backup name
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    backup_reference = f"{reference}-backup-{timestamp}"
    
    try:
        # Get the current secret value
        try:
            current_value = secrets_manager.get_secret(reference)
        except SecretNotFoundError:
            # If the secret doesn't exist, just create it with the new value
            return secrets_manager.create_secret(
                reference,
                new_value,
                description=description
            )
        
        # Create a backup of the current secret
        backup_description = f"Backup of {reference} created during rotation at {timestamp}"
        backup_arn = secrets_manager.create_secret(
            backup_reference,
            current_value,
            description=backup_description
        )
        
        # Schedule deletion of the backup after the specified days
        if backup_days > 0:
            secrets_manager.delete_secret(
                backup_reference,
                recovery_window_days=backup_days
            )
        
        # Update the original secret with the new value
        return secrets_manager.update_secret(reference, new_value)
    
    except (SecretsManagerError, ValueError) as e:
        raise RotationError(f"Failed to rotate secret {reference}: {str(e)}")


def list_backups(reference: str) -> List[str]:
    """
    List all backup versions of a secret.
    
    Args:
        reference: The original secret reference
        
    Returns:
        List of backup references
    """
    # This is an approximation based on AWS CLI/SDK capabilities
    # In practice, we would need to list all secrets and filter
    # This is currently a placeholder for future implementation
    raise NotImplementedError(
        "Listing backups is not fully implemented yet. "
        "This would require listing all secrets and filtering by name pattern."
    ) 