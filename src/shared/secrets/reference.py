"""
Reference module for AWS Secrets Manager.

This module defines the structure and format for secret references used in the system,
along with utilities for generating, validating, and parsing references.
"""

import re
from enum import Enum
from typing import Dict, List, Optional, TypedDict, Union, Literal


class SecretType(Enum):
    """Enumeration of secret types supported by the system."""
    WHATSAPP = "whatsapp-credentials"
    SMS = "sms-credentials"
    EMAIL = "email-credentials"
    AI = "ai-api-key"
    AUTH = "auth"


class Provider(Enum):
    """Enumeration of credential providers supported by the system."""
    TWILIO = "twilio"
    SENDGRID = "sendgrid"
    GLOBAL = "global"  # For global credentials like AI
    AUTH = "auth"  # For authentication


class WhatsAppCredentials(TypedDict):
    """TypedDict for WhatsApp (Twilio) credentials."""
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_template_sid: str


class SMSCredentials(TypedDict):
    """TypedDict for SMS (Twilio) credentials."""
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_template_sid: str


class EmailCredentials(TypedDict):
    """TypedDict for Email (SendGrid) credentials."""
    sendgrid_auth_value: str
    sendgrid_from_email: str
    sendgrid_from_name: str
    sendgrid_template_id: str


class AICredentials(TypedDict):
    """TypedDict for AI API credentials."""
    ai_api_key: str


class AuthCredentials(TypedDict):
    """TypedDict for authentication credentials."""
    auth_value: str


# Union type for all credential types
Credentials = Union[
    WhatsAppCredentials,
    SMSCredentials,
    EmailCredentials,
    AICredentials,
    AuthCredentials
]


# Regular expression for validating secret references
SECRET_REFERENCE_PATTERN = re.compile(
    r"^(whatsapp-credentials|sms-credentials|email-credentials|ai-api-key|auth)/"  # Secret type
    r"([a-zA-Z0-9_-]+)/"  # Company ID (or 'global' for AI)
    r"([a-zA-Z0-9_-]+)/"  # Project ID
    r"(twilio|sendgrid|global|auth)$"  # Provider
)


class SecretReference:
    """
    Class for handling secret references in the correct format.
    
    Format: {credential_type}/{company_id}/{project_id}/{provider}
    
    Example: whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio
    """
    
    def __init__(
        self,
        secret_type: SecretType,
        company_id: str,
        project_id: str,
        provider: Provider,
    ):
        """
        Initialize a new secret reference.
        
        Args:
            secret_type: The type of secret (e.g., WhatsApp, SMS, etc.)
            company_id: The company ID (or 'global' for global secrets)
            project_id: The project ID
            provider: The credential provider (e.g., Twilio, SendGrid)
        """
        self.secret_type = secret_type
        self.company_id = company_id
        self.project_id = project_id
        self.provider = provider
    
    @classmethod
    def from_string(cls, reference: str) -> 'SecretReference':
        """
        Create a SecretReference from a reference string.
        
        Args:
            reference: The reference string in format {type}/{company}/{project}/{provider}
            
        Returns:
            SecretReference object
            
        Raises:
            ValueError: If the reference format is invalid
        """
        match = SECRET_REFERENCE_PATTERN.match(reference)
        if not match:
            raise ValueError(
                f"Invalid secret reference format: {reference}. "
                f"Expected format: {{type}}/{{company}}/{{project}}/{{provider}}"
            )
        
        secret_type_str, company_id, project_id, provider_str = match.groups()
        
        try:
            secret_type = SecretType(secret_type_str)
        except ValueError:
            raise ValueError(f"Invalid secret type: {secret_type_str}")
            
        try:
            provider = Provider(provider_str)
        except ValueError:
            raise ValueError(f"Invalid provider: {provider_str}")
        
        return cls(secret_type, company_id, project_id, provider)
    
    def to_string(self) -> str:
        """
        Convert the reference to its string representation.
        
        Returns:
            String representation of the reference
        """
        return f"{self.secret_type.value}/{self.company_id}/{self.project_id}/{self.provider.value}"
    
    def __str__(self) -> str:
        return self.to_string()
    
    def __repr__(self) -> str:
        return f"SecretReference({self.to_string()})"
    
    @staticmethod
    def is_valid_reference(reference: str) -> bool:
        """
        Check if a reference string is valid.
        
        Args:
            reference: The reference string to validate
            
        Returns:
            True if valid, False otherwise
        """
        return bool(SECRET_REFERENCE_PATTERN.match(reference))
    
    @staticmethod
    def get_required_fields(secret_type: SecretType) -> List[str]:
        """
        Get the required fields for a given secret type.
        
        Args:
            secret_type: The secret type to get required fields for
            
        Returns:
            List of required field names
        """
        if secret_type == SecretType.WHATSAPP or secret_type == SecretType.SMS:
            return ["twilio_account_sid", "twilio_auth_token", "twilio_template_sid"]
        elif secret_type == SecretType.EMAIL:
            return ["sendgrid_auth_value", "sendgrid_from_email", 
                    "sendgrid_from_name", "sendgrid_template_id"]
        elif secret_type == SecretType.AI:
            return ["ai_api_key"]
        elif secret_type == SecretType.AUTH:
            return ["auth_value"]
        else:
            raise ValueError(f"Unknown secret type: {secret_type}")


def create_whatsapp_reference(company_id: str, project_id: str) -> str:
    """
    Create a WhatsApp credentials reference.
    
    Args:
        company_id: The company ID
        project_id: The project ID
        
    Returns:
        Reference string for WhatsApp credentials
    """
    ref = SecretReference(
        SecretType.WHATSAPP,
        company_id,
        project_id,
        Provider.TWILIO
    )
    return ref.to_string()


def create_sms_reference(company_id: str, project_id: str) -> str:
    """
    Create an SMS credentials reference.
    
    Args:
        company_id: The company ID
        project_id: The project ID
        
    Returns:
        Reference string for SMS credentials
    """
    ref = SecretReference(
        SecretType.SMS,
        company_id,
        project_id,
        Provider.TWILIO
    )
    return ref.to_string()


def create_email_reference(company_id: str, project_id: str) -> str:
    """
    Create an Email credentials reference.
    
    Args:
        company_id: The company ID
        project_id: The project ID
        
    Returns:
        Reference string for Email credentials
    """
    ref = SecretReference(
        SecretType.EMAIL,
        company_id,
        project_id,
        Provider.SENDGRID
    )
    return ref.to_string()


def create_ai_reference() -> str:
    """
    Create an AI API key reference (global).
    
    Returns:
        Reference string for AI API key
    """
    ref = SecretReference(
        SecretType.AI,
        "global",
        "global",
        Provider.GLOBAL
    )
    return ref.to_string()


def create_auth_reference(company_id: str, project_id: str) -> str:
    """
    Create an authentication credentials reference.
    
    Args:
        company_id: The company ID
        project_id: The project ID
        
    Returns:
        Reference string for authentication credentials
    """
    ref = SecretReference(
        SecretType.AUTH,
        company_id,
        project_id,
        Provider.AUTH
    )
    return ref.to_string()


def validate_credential_structure(
    credentials: Dict,
    secret_type: SecretType
) -> bool:
    """
    Validate that a credential object has the required fields for its type.
    
    Args:
        credentials: The credential object to validate
        secret_type: The type of secret
        
    Returns:
        True if valid, False if missing required fields
    """
    required_fields = SecretReference.get_required_fields(secret_type)
    return all(field in credentials for field in required_fields) 