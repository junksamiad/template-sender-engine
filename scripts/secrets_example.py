#!/usr/bin/env python
"""
Example script for using the AWS Secrets Manager utilities.

This script demonstrates how to use the secrets manager utilities
to create, retrieve, update, and delete secrets.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.shared.secrets.reference import (
    create_whatsapp_reference, create_sms_reference,
    create_email_reference, create_ai_reference,
    create_auth_reference
)
from src.shared.secrets.manager import get_secrets_manager, SecretNotFoundError
from src.shared.secrets.mock import (
    get_mock_secrets_manager, mock_whatsapp_credentials,
    mock_email_credentials, mock_ai_credentials
)


# Load environment variables from .env file if it exists
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def use_mock_secrets():
    """Demonstrate using mock secrets for local development/testing."""
    logger.info("=== Using Mock Secrets Manager ===")
    
    # Get mock secrets manager
    secrets_manager = get_mock_secrets_manager()
    
    # Define company and project
    company_id = "cucumber-recruitment"
    project_id = "cv-analysis"
    
    # Create references
    whatsapp_ref = create_whatsapp_reference(company_id, project_id)
    email_ref = create_email_reference(company_id, project_id)
    ai_ref = create_ai_reference()
    
    # Reset mock to ensure clean state
    secrets_manager.reset()
    
    # Create mock credentials
    logger.info("Creating mock WhatsApp credentials...")
    whatsapp_creds = mock_whatsapp_credentials(
        account_sid="ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        auth_token="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        template_sid="HXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXFAKE"
    )
    
    secrets_manager.create_secret(
        whatsapp_ref,
        whatsapp_creds,
        "WhatsApp credentials for Cucumber Recruitment CV Analysis"
    )
    
    logger.info("Creating mock Email credentials...")
    email_creds = mock_email_credentials(
        auth_value="SG.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXFAKE",
        from_email="cv-analysis@cucumber-recruitment.example.com",
        from_name="Cucumber Recruitment CV Analysis",
        template_id="d-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXFAKE"
    )
    
    secrets_manager.create_secret(
        email_ref,
        email_creds,
        "Email credentials for Cucumber Recruitment CV Analysis"
    )
    
    logger.info("Creating mock AI credentials...")
    ai_creds = mock_ai_credentials(
        api_key="sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXFAKE"
    )
    
    secrets_manager.create_secret(
        ai_ref,
        ai_creds,
        "Global AI API key"
    )
    
    # List all secrets
    logger.info("Listing all secrets:")
    for secret_ref in secrets_manager.list_secrets():
        logger.info(f"  - {secret_ref}")
    
    # Retrieve and display WhatsApp credentials
    logger.info("Retrieving WhatsApp credentials...")
    retrieved_whatsapp = secrets_manager.get_secret(whatsapp_ref)
    logger.info(f"  Account SID: {retrieved_whatsapp['twilio_account_sid']}")
    logger.info(f"  Template SID: {retrieved_whatsapp['twilio_template_sid']}")
    logger.info(f"  Auth Token: {retrieved_whatsapp['twilio_auth_token'][0:3]}...{retrieved_whatsapp['twilio_auth_token'][-3:]}")
    
    # Update WhatsApp credentials
    logger.info("Updating WhatsApp credentials...")
    updated_whatsapp = mock_whatsapp_credentials(
        account_sid="ACYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY",
        auth_token="yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
        template_sid="HXYYYYYYYYYYYYYYYYYYYYYYYYYYYYFAKE"
    )
    
    secrets_manager.update_secret(whatsapp_ref, updated_whatsapp)
    
    # Retrieve updated credentials
    logger.info("Retrieving updated WhatsApp credentials...")
    retrieved_updated = secrets_manager.get_secret(whatsapp_ref)
    logger.info(f"  Account SID: {retrieved_updated['twilio_account_sid']}")
    logger.info(f"  Template SID: {retrieved_updated['twilio_template_sid']}")
    logger.info(f"  Auth Token: {retrieved_updated['twilio_auth_token'][0:3]}...{retrieved_updated['twilio_auth_token'][-3:]}")
    
    # Delete a secret
    logger.info("Deleting Email credentials...")
    secrets_manager.delete_secret(email_ref)
    
    # Try to retrieve deleted secret (should raise exception)
    logger.info("Trying to retrieve deleted Email credentials...")
    try:
        secrets_manager.get_secret(email_ref)
    except SecretNotFoundError:
        logger.info("  Secret not found (as expected)")


def use_aws_secrets():
    """Demonstrate using actual AWS Secrets Manager."""
    # Check for AWS credentials
    if not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        logger.warning("AWS credentials not found in environment. Skipping AWS example.")
        return
    
    logger.info("=== Using AWS Secrets Manager ===")
    
    # Get AWS secrets manager
    secrets_manager = get_secrets_manager()
    
    # Define company and project
    company_id = "cucumber-recruitment"
    project_id = "cv-analysis"
    
    # Create references
    ai_ref = create_ai_reference()
    
    # Try to retrieve the AI key
    logger.info(f"Attempting to retrieve AI API key: {ai_ref}")
    try:
        ai_creds = secrets_manager.get_secret(ai_ref)
        logger.info(f"  Found AI API key: {ai_creds['ai_api_key'][0:3]}...{ai_creds['ai_api_key'][-3:]}")
    except SecretNotFoundError:
        logger.info("  AI API key not found in AWS Secrets Manager")
        
        # You would create the secret here if needed
        # Example:
        # logger.info("  Creating AI API key...")
        # secrets_manager.create_secret(
        #     ai_ref,
        #     {"ai_api_key": "sk-1234567890abcdef1234567890abcdef"},
        #     "Global AI API key"
        # )


if __name__ == "__main__":
    # Always run the mock example
    use_mock_secrets()
    
    # Conditionally run the AWS example
    if os.environ.get("USE_AWS", "false").lower() == "true":
        use_aws_secrets()
    else:
        logger.info("\nSkipping AWS example. Set USE_AWS=true to run with real AWS.") 