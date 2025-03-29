"""
CDK stack for AWS Secrets Manager.

This module defines the CDK stack for AWS Secrets Manager and the
infrastructure for the reference-based credential management system.
"""

from aws_cdk import (
    Stack,
    aws_secretsmanager as secretsmanager,
    aws_iam as iam,
    RemovalPolicy,
)
from constructs import Construct
from typing import Any, Dict, List, Optional


class SecretsStack(Stack):
    """
    AWS Secrets Manager CDK stack.
    
    This stack defines the AWS Secrets Manager infrastructure,
    including the base secrets for each credential type.
    """
    
    def __init__(
        self, scope: Construct, construct_id: str, **kwargs: Any
    ) -> None:
        """Initialize the stack."""
        super().__init__(scope, construct_id, **kwargs)
        
        # Global AI API key secret
        self.ai_api_key = secretsmanager.Secret(
            self,
            "AIAPIKey",
            secret_name="ai-api-key/global",
            description="AI API key used across all channels",
            removal_policy=RemovalPolicy.RETAIN,  # Important for production keys
        )
        
        # Template secrets for different channel types
        # These serve as templates for company-specific secrets
        
        # WhatsApp template secret (using Twilio)
        self.whatsapp_template = secretsmanager.Secret(
            self,
            "WhatsAppTemplate",
            secret_name="whatsapp-credentials/template/template/twilio",
            description="Template for WhatsApp credentials using Twilio",
            removal_policy=RemovalPolicy.DESTROY,  # Template can be destroyed
            generate_secret_string=secretsmanager.SecretStringGenerator(
                generate_string_key="twilio_auth_token",
                secret_string_template='{"twilio_account_sid":"AC_ACCOUNT_SID_PLACEHOLDER","twilio_template_sid":"TEMPLATE_SID_PLACEHOLDER"}',
                exclude_characters="/@\"'\\",
            ),
        )
        
        # SMS template secret (using Twilio)
        self.sms_template = secretsmanager.Secret(
            self,
            "SMSTemplate",
            secret_name="sms-credentials/template/template/twilio",
            description="Template for SMS credentials using Twilio",
            removal_policy=RemovalPolicy.DESTROY,  # Template can be destroyed
            generate_secret_string=secretsmanager.SecretStringGenerator(
                generate_string_key="twilio_auth_token",
                secret_string_template='{"twilio_account_sid":"AC_ACCOUNT_SID_PLACEHOLDER","twilio_template_sid":"TEMPLATE_SID_PLACEHOLDER"}',
                exclude_characters="/@\"'\\",
            ),
        )
        
        # Email template secret (using SendGrid)
        self.email_template = secretsmanager.Secret(
            self,
            "EmailTemplate",
            secret_name="email-credentials/template/template/sendgrid",
            description="Template for Email credentials using SendGrid",
            removal_policy=RemovalPolicy.DESTROY,  # Template can be destroyed
            generate_secret_string=secretsmanager.SecretStringGenerator(
                generate_string_key="sendgrid_auth_value",
                secret_string_template='{"sendgrid_from_email":"no-reply@example.com","sendgrid_from_name":"Company Name","sendgrid_template_id":"TEMPLATE_ID_PLACEHOLDER"}',
                exclude_characters="/@\"'\\",
            ),
        )
        
        # Authentication template secret
        self.auth_template = secretsmanager.Secret(
            self,
            "AuthTemplate",
            secret_name="auth/template/template/auth",
            description="Template for authentication credentials",
            removal_policy=RemovalPolicy.DESTROY,  # Template can be destroyed
            generate_secret_string=secretsmanager.SecretStringGenerator(
                generate_string_key="auth_value",
                secret_string_template='{}',
                exclude_characters="/@\"'\\",
            ),
        )
        
        # Create a policy for reading secrets
        read_policy_statement = iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:whatsapp-credentials/*/*/twilio",
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:sms-credentials/*/*/twilio",
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:email-credentials/*/*/sendgrid",
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:auth/*/*/auth",
                self.ai_api_key.secret_arn,
            ],
        )
        
        # Create the read policy
        self.read_policy = iam.ManagedPolicy(
            self,
            "SecretsReadPolicy",
            statements=[read_policy_statement],
            description="Policy for reading secrets using reference-based approach",
        )
        
        # Create a policy for administering secrets
        admin_policy_statement = iam.PolicyStatement(
            actions=[
                "secretsmanager:GetSecretValue",
                "secretsmanager:CreateSecret",
                "secretsmanager:DeleteSecret",
                "secretsmanager:PutSecretValue",
                "secretsmanager:UpdateSecret",
                "secretsmanager:RotateSecret",
                "secretsmanager:ListSecrets",
                "secretsmanager:DescribeSecret",
                "secretsmanager:TagResource",
                "secretsmanager:UntagResource",
            ],
            resources=[
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:*",
            ],
        )
        
        # Create the admin policy
        self.admin_policy = iam.ManagedPolicy(
            self,
            "SecretsAdminPolicy",
            statements=[admin_policy_statement],
            description="Policy for administering all secrets",
        )
    
    def add_company_secrets(
        self, 
        company_id: str, 
        project_id: str,
        description: Optional[str] = None
    ) -> Dict[str, secretsmanager.Secret]:
        """
        Add a set of secrets for a company and project.
        
        Args:
            company_id: The company ID
            project_id: The project ID
            description: Optional description prefix
            
        Returns:
            Dictionary of created secrets
        """
        desc_prefix = f"{description} - " if description else ""
        
        # Create WhatsApp credentials secret
        whatsapp_secret = secretsmanager.Secret(
            self,
            f"WhatsApp{company_id}{project_id}",
            secret_name=f"whatsapp-credentials/{company_id}/{project_id}/twilio",
            description=f"{desc_prefix}WhatsApp credentials for {company_id}/{project_id}",
            removal_policy=RemovalPolicy.RETAIN,
        )
        
        # Create SMS credentials secret
        sms_secret = secretsmanager.Secret(
            self,
            f"SMS{company_id}{project_id}",
            secret_name=f"sms-credentials/{company_id}/{project_id}/twilio",
            description=f"{desc_prefix}SMS credentials for {company_id}/{project_id}",
            removal_policy=RemovalPolicy.RETAIN,
        )
        
        # Create Email credentials secret
        email_secret = secretsmanager.Secret(
            self,
            f"Email{company_id}{project_id}",
            secret_name=f"email-credentials/{company_id}/{project_id}/sendgrid",
            description=f"{desc_prefix}Email credentials for {company_id}/{project_id}",
            removal_policy=RemovalPolicy.RETAIN,
        )
        
        # Create Authentication credentials secret
        auth_secret = secretsmanager.Secret(
            self,
            f"Auth{company_id}{project_id}",
            secret_name=f"auth/{company_id}/{project_id}/auth",
            description=f"{desc_prefix}Authentication credentials for {company_id}/{project_id}",
            removal_policy=RemovalPolicy.RETAIN,
        )
        
        return {
            "whatsapp": whatsapp_secret,
            "sms": sms_secret,
            "email": email_secret,
            "auth": auth_secret,
        }
    
    def create_company_policy(
        self,
        policy_id: str,
        company_id: str,
        project_ids: List[str],
        description: Optional[str] = None,
        include_global_ai: bool = True
    ) -> iam.ManagedPolicy:
        """
        Create an IAM policy for a company's secrets.
        
        Args:
            policy_id: Unique ID for the policy
            company_id: The company ID
            project_ids: List of project IDs
            description: Optional policy description
            include_global_ai: Whether to include access to the global AI key
            
        Returns:
            IAM ManagedPolicy
        """
        resources = []
        
        # Add company/project-specific resources
        for project_id in project_ids:
            resources.extend([
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:whatsapp-credentials/{company_id}/{project_id}/twilio",
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:sms-credentials/{company_id}/{project_id}/twilio",
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:email-credentials/{company_id}/{project_id}/sendgrid",
                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:auth/{company_id}/{project_id}/auth",
            ])
        
        # Add global AI key if requested
        if include_global_ai:
            resources.append(self.ai_api_key.secret_arn)
        
        # Create policy statement
        policy_statement = iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=resources,
        )
        
        # Create the policy
        return iam.ManagedPolicy(
            self,
            f"CompanyPolicy{policy_id}",
            statements=[policy_statement],
            description=description or f"Policy for {company_id} secrets",
        ) 