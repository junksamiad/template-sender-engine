"""
IAM permissions utilities for AWS Secrets Manager.

This module defines IAM policy generators for working with secrets
according to our reference-based credential management approach.
"""

from typing import List, Optional, Dict, Any


def generate_read_policy(
    account_id: str,
    region: str,
    references: Optional[List[str]] = None,
    channel_types: Optional[List[str]] = None,
    include_global_ai: bool = True
) -> Dict[str, Any]:
    """
    Generate an IAM policy for reading secrets.
    
    Args:
        account_id: The AWS account ID
        region: The AWS region
        references: Specific references to allow access to (optional)
        channel_types: Channel types to allow access to (optional)
        include_global_ai: Whether to include access to the global AI key
        
    Returns:
        IAM policy document as a dictionary
    """
    resources = []
    
    # Add specific references if provided
    if references:
        for reference in references:
            resources.append(
                f"arn:aws:secretsmanager:{region}:{account_id}:secret:{reference}"
            )
    
    # Add channel types if provided
    if channel_types:
        for channel_type in channel_types:
            if channel_type == "whatsapp":
                resources.append(
                    f"arn:aws:secretsmanager:{region}:{account_id}:secret:whatsapp-credentials/*/*/twilio"
                )
            elif channel_type == "sms":
                resources.append(
                    f"arn:aws:secretsmanager:{region}:{account_id}:secret:sms-credentials/*/*/twilio"
                )
            elif channel_type == "email":
                resources.append(
                    f"arn:aws:secretsmanager:{region}:{account_id}:secret:email-credentials/*/*/sendgrid"
                )
            elif channel_type == "auth":
                resources.append(
                    f"arn:aws:secretsmanager:{region}:{account_id}:secret:auth/*/*/auth"
                )
    
    # Add global AI key
    if include_global_ai:
        resources.append(
            f"arn:aws:secretsmanager:{region}:{account_id}:secret:ai-api-key/global"
        )
    
    # If no resources were added, add a wildcard
    if not resources:
        resources.append(
            f"arn:aws:secretsmanager:{region}:{account_id}:secret:*"
        )
    
    # Create policy document
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "secretsmanager:GetSecretValue",
                "Resource": resources
            }
        ]
    }
    
    return policy


def generate_write_policy(
    account_id: str,
    region: str,
    references: Optional[List[str]] = None,
    channel_types: Optional[List[str]] = None,
    include_global_ai: bool = True
) -> Dict[str, Any]:
    """
    Generate an IAM policy for writing (creating, updating, deleting) secrets.
    
    Args:
        account_id: The AWS account ID
        region: The AWS region
        references: Specific references to allow access to (optional)
        channel_types: Channel types to allow access to (optional)
        include_global_ai: Whether to include access to the global AI key
        
    Returns:
        IAM policy document as a dictionary
    """
    # Generate the same resources as for read
    read_policy = generate_read_policy(
        account_id, region, references, channel_types, include_global_ai
    )
    
    # Create policy document with write actions
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:CreateSecret",
                    "secretsmanager:UpdateSecret",
                    "secretsmanager:DeleteSecret",
                    "secretsmanager:PutSecretValue",
                    "secretsmanager:GetSecretValue"
                ],
                "Resource": read_policy["Statement"][0]["Resource"]
            }
        ]
    }
    
    return policy


def generate_rotation_policy(
    account_id: str,
    region: str,
    references: Optional[List[str]] = None,
    channel_types: Optional[List[str]] = None,
    include_global_ai: bool = True
) -> Dict[str, Any]:
    """
    Generate an IAM policy for rotating secrets.
    
    Args:
        account_id: The AWS account ID
        region: The AWS region
        references: Specific references to allow access to (optional)
        channel_types: Channel types to allow access to (optional)
        include_global_ai: Whether to include access to the global AI key
        
    Returns:
        IAM policy document as a dictionary
    """
    # Generate the same resources as for write
    write_policy = generate_write_policy(
        account_id, region, references, channel_types, include_global_ai
    )
    
    # Create policy document with rotation actions
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:CreateSecret",
                    "secretsmanager:UpdateSecret",
                    "secretsmanager:DeleteSecret",
                    "secretsmanager:PutSecretValue",
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:RotateSecret",
                    "secretsmanager:ListSecrets"
                ],
                "Resource": write_policy["Statement"][0]["Resource"]
            }
        ]
    }
    
    return policy 