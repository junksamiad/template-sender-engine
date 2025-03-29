"""
Unit tests for the IAM policy generator module.
"""

import pytest
from src.shared.secrets.iam import (
    generate_read_policy,
    generate_write_policy,
    generate_rotation_policy
)


class TestIAMPolicyGenerators:
    """Tests for the IAM policy generator functions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.account_id = "123456789012"
        self.region = "us-east-1"
    
    def test_generate_read_policy_all_secrets(self):
        """Test generating a read policy for all secrets."""
        policy = generate_read_policy(
            self.account_id,
            self.region
        )
        
        # Check policy structure
        assert policy["Version"] == "2012-10-17"
        assert len(policy["Statement"]) == 1
        
        statement = policy["Statement"][0]
        assert statement["Effect"] == "Allow"
        assert statement["Action"] == "secretsmanager:GetSecretValue"
        
        # Check resources
        resources = statement["Resource"]
        assert isinstance(resources, list)
        assert len(resources) >= 1  # Should at least have a wildcard
        
        # Should include AI key by default
        ai_key_arn = f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:ai-api-key/global"
        assert ai_key_arn in resources
    
    def test_generate_read_policy_specific_references(self):
        """Test generating a read policy for specific references."""
        references = [
            "whatsapp-credentials/company1/project1/twilio",
            "email-credentials/company1/project1/sendgrid"
        ]
        
        policy = generate_read_policy(
            self.account_id,
            self.region,
            references=references
        )
        
        # Check resources
        resources = policy["Statement"][0]["Resource"]
        assert len(resources) == 3  # 2 references + 1 AI key
        
        # Should include all references
        for ref in references:
            ref_arn = f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:{ref}"
            assert ref_arn in resources
    
    def test_generate_read_policy_channel_types(self):
        """Test generating a read policy for specific channel types."""
        channel_types = ["whatsapp", "email"]
        
        policy = generate_read_policy(
            self.account_id,
            self.region,
            channel_types=channel_types
        )
        
        # Check resources
        resources = policy["Statement"][0]["Resource"]
        assert len(resources) == 3  # 2 channel types + 1 AI key
        
        # Should include patterns for all channel types
        whatsapp_pattern = f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:whatsapp-credentials/*/*/twilio"
        email_pattern = f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:email-credentials/*/*/sendgrid"
        
        assert whatsapp_pattern in resources
        assert email_pattern in resources
    
    def test_generate_read_policy_no_ai_key(self):
        """Test generating a read policy without the AI key."""
        policy = generate_read_policy(
            self.account_id,
            self.region,
            include_global_ai=False
        )
        
        # Check resources
        resources = policy["Statement"][0]["Resource"]
        ai_key_arn = f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:ai-api-key/global"
        assert ai_key_arn not in resources
    
    def test_generate_write_policy(self):
        """Test generating a write policy."""
        policy = generate_write_policy(
            self.account_id,
            self.region
        )
        
        # Check policy structure
        assert policy["Version"] == "2012-10-17"
        assert len(policy["Statement"]) == 1
        
        statement = policy["Statement"][0]
        assert statement["Effect"] == "Allow"
        
        # Should include read and write actions
        actions = statement["Action"]
        assert isinstance(actions, list)
        assert "secretsmanager:GetSecretValue" in actions
        assert "secretsmanager:CreateSecret" in actions
        assert "secretsmanager:UpdateSecret" in actions
        assert "secretsmanager:DeleteSecret" in actions
        assert "secretsmanager:PutSecretValue" in actions
    
    def test_generate_rotation_policy(self):
        """Test generating a rotation policy."""
        policy = generate_rotation_policy(
            self.account_id,
            self.region
        )
        
        # Check policy structure
        assert policy["Version"] == "2012-10-17"
        assert len(policy["Statement"]) == 1
        
        statement = policy["Statement"][0]
        assert statement["Effect"] == "Allow"
        
        # Should include rotation-specific actions
        actions = statement["Action"]
        assert isinstance(actions, list)
        assert "secretsmanager:RotateSecret" in actions
        assert "secretsmanager:ListSecrets" in actions
        
        # Should also include all write actions
        assert "secretsmanager:GetSecretValue" in actions
        assert "secretsmanager:CreateSecret" in actions
        assert "secretsmanager:UpdateSecret" in actions
        assert "secretsmanager:DeleteSecret" in actions
        assert "secretsmanager:PutSecretValue" in actions 