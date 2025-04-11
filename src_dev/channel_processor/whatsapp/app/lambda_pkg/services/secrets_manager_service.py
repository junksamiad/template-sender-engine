"""
Handles interactions with AWS Secrets Manager to retrieve secrets like API keys.
"""
import boto3
import logging
import os
import json
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional, TYPE_CHECKING # Import TYPE_CHECKING

# Import boto3 types for type hinting if available
if TYPE_CHECKING:
    from mypy_boto3_secretsmanager.client import SecretsManagerClient

# Initialize logger
logger = logging.getLogger(__name__)

# Constants from environment variables or defaults
SECRETS_MANAGER_REGION = os.environ.get("SECRETS_MANAGER_REGION", "eu-north-1") # Default same as index.py

# Remove module-level client initialization
# secrets_manager_client = None
# try:
#     secrets_manager_client = boto3.client("secretsmanager", region_name=SECRETS_MANAGER_REGION)
#     logger.info(f"Successfully initialized Secrets Manager client in region: {SECRETS_MANAGER_REGION}")
# except Exception as e:
#     logger.exception("Failed to initialize Secrets Manager client.")

def get_secret(
    secret_name_or_arn: str,
    # Add optional client argument for DI
    sm_client: Optional['SecretsManagerClient'] = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieves a secret from AWS Secrets Manager and parses it as JSON.

    Args:
        secret_name_or_arn: The name or ARN of the secret to retrieve.
        sm_client: Optional boto3 SecretsManager client for testing/injection.

    Returns:
        A dictionary representing the parsed JSON secret, or None if retrieval fails.
    """
    # Initialize client inside function if not provided
    if sm_client is None:
        try:
            sm_client = boto3.client("secretsmanager", region_name=SECRETS_MANAGER_REGION)
            logger.debug(f"Initialized default Secrets Manager client in region: {SECRETS_MANAGER_REGION}")
        except Exception as e:
            logger.exception("Failed to initialize default Secrets Manager client.")
            return None

    # Check again after attempting initialization
    if sm_client is None:
        logger.error("Secrets Manager client could not be initialized. Cannot retrieve secret.")
        return None

    if not secret_name_or_arn:
        logger.warning("Attempted to retrieve secret with an empty name/ARN.")
        return None

    logger.debug(f"Attempting to retrieve secret: {secret_name_or_arn}")

    try:
        # Use the provided or initialized client
        get_secret_value_response = sm_client.get_secret_value(
            SecretId=secret_name_or_arn
        )

        # Check if secret is string or binary - assume string for credentials usually
        if 'SecretString' in get_secret_value_response:
            secret_value = get_secret_value_response['SecretString']
            logger.info(f"Successfully retrieved secret string for: {secret_name_or_arn}")
        # elif 'SecretBinary' in get_secret_value_response:
            # Handle binary secret if necessary - decode appropriately
            # secret_value = base64.b64decode(get_secret_value_response['SecretBinary'])
            # logger.info(f"Successfully retrieved secret binary for: {secret_name_or_arn}")
            # For now, we only expect string secrets (JSON)
            # return None # Or raise error if binary unexpected
        else:
            # Should not happen based on API spec, but handle defensively
            logger.error(f"Secret value not found in response for: {secret_name_or_arn}")
            return None

        # Parse the secret string (assuming it's JSON)
        try:
            parsed_secret = json.loads(secret_value)
            return parsed_secret
        except json.JSONDecodeError:
            logger.error(f"Failed to parse secret JSON for: {secret_name_or_arn}. Returning raw string.")
            # Depending on use case, might return the raw string or None/raise error
            # For now, returning None as we expect a dict
            return None

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'ResourceNotFoundException':
            logger.error(f"Secret not found: {secret_name_or_arn}")
        elif error_code == 'AccessDeniedException':
             logger.error(f"Access denied when trying to retrieve secret: {secret_name_or_arn}")
        else:
            logger.error(f"Secrets Manager ClientError retrieving {secret_name_or_arn}: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error retrieving secret {secret_name_or_arn}: {e}")
        return None

# Example usage (for testing if needed)
# if __name__ == '__main__':
#     # Add mock environment variable or real secret name for testing
#     test_secret_name = "your/test/secret/name"
#     retrieved_secret = get_secret(test_secret_name)
#     if retrieved_secret:
#         print(f"Successfully retrieved: {retrieved_secret}")
#     else:
#         print(f"Failed to retrieve secret: {test_secret_name}") 