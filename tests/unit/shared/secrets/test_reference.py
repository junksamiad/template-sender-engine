"""
Unit tests for the reference module.
"""

import pytest
from src.shared.secrets.reference import (
    SecretReference, SecretType, Provider,
    create_whatsapp_reference, create_sms_reference,
    create_email_reference, create_ai_reference,
    create_auth_reference, validate_credential_structure
)


class TestSecretReference:
    """Tests for the SecretReference class."""
    
    def test_initialization(self):
        """Test that a SecretReference can be initialized."""
        ref = SecretReference(
            SecretType.WHATSAPP,
            "example-company",
            "example-project",
            Provider.TWILIO
        )
        
        assert ref.secret_type == SecretType.WHATSAPP
        assert ref.company_id == "example-company"
        assert ref.project_id == "example-project"
        assert ref.provider == Provider.TWILIO
    
    def test_to_string(self):
        """Test that a SecretReference can be converted to a string."""
        ref = SecretReference(
            SecretType.WHATSAPP,
            "example-company",
            "example-project",
            Provider.TWILIO
        )
        
        assert ref.to_string() == "whatsapp-credentials/example-company/example-project/twilio"
    
    def test_from_string_valid(self):
        """Test that a SecretReference can be created from a valid string."""
        ref_str = "whatsapp-credentials/example-company/example-project/twilio"
        ref = SecretReference.from_string(ref_str)
        
        assert ref.secret_type == SecretType.WHATSAPP
        assert ref.company_id == "example-company"
        assert ref.project_id == "example-project"
        assert ref.provider == Provider.TWILIO
    
    def test_from_string_invalid_format(self):
        """Test that an exception is raised for an invalid reference format."""
        invalid_refs = [
            "not-a-valid-reference",
            "whatsapp-credentials/company/project",  # Missing provider
            "whatsapp-credentials/company/project/invalid-provider",  # Invalid provider
            "invalid-type/company/project/twilio",  # Invalid type
        ]
        
        for ref_str in invalid_refs:
            with pytest.raises(ValueError):
                SecretReference.from_string(ref_str)
    
    def test_is_valid_reference(self):
        """Test the reference validation."""
        valid_refs = [
            "whatsapp-credentials/example-company/example-project/twilio",
            "sms-credentials/example-company/example-project/twilio",
            "email-credentials/example-company/example-project/sendgrid",
            "ai-api-key/global/global/global",
            "auth/example-company/example-project/auth",
        ]
        
        invalid_refs = [
            "not-a-valid-reference",
            "whatsapp-credentials/company/project",  # Missing provider
            "whatsapp-credentials/company/project/invalid-provider",  # Invalid provider
            "invalid-type/company/project/twilio",  # Invalid type
        ]
        
        for ref_str in valid_refs:
            assert SecretReference.is_valid_reference(ref_str)
        
        for ref_str in invalid_refs:
            assert not SecretReference.is_valid_reference(ref_str)
    
    def test_get_required_fields(self):
        """Test getting required fields for different secret types."""
        assert SecretReference.get_required_fields(SecretType.WHATSAPP) == [
            "twilio_account_sid", "twilio_auth_token", "twilio_template_sid"
        ]
        
        assert SecretReference.get_required_fields(SecretType.SMS) == [
            "twilio_account_sid", "twilio_auth_token", "twilio_template_sid"
        ]
        
        assert SecretReference.get_required_fields(SecretType.EMAIL) == [
            "sendgrid_auth_value", "sendgrid_from_email", 
            "sendgrid_from_name", "sendgrid_template_id"
        ]
        
        assert SecretReference.get_required_fields(SecretType.AI) == ["ai_api_key"]
        
        assert SecretReference.get_required_fields(SecretType.AUTH) == ["auth_value"]
        
        with pytest.raises(ValueError):
            # Test with invalid enum value
            SecretReference.get_required_fields("invalid")


class TestReferenceHelpers:
    """Tests for the reference helper functions."""
    
    def test_create_whatsapp_reference(self):
        """Test creating a WhatsApp reference."""
        ref = create_whatsapp_reference("example-company", "example-project")
        assert ref == "whatsapp-credentials/example-company/example-project/twilio"
    
    def test_create_sms_reference(self):
        """Test creating an SMS reference."""
        ref = create_sms_reference("example-company", "example-project")
        assert ref == "sms-credentials/example-company/example-project/twilio"
    
    def test_create_email_reference(self):
        """Test creating an email reference."""
        ref = create_email_reference("example-company", "example-project")
        assert ref == "email-credentials/example-company/example-project/sendgrid"
    
    def test_create_ai_reference(self):
        """Test creating an AI reference."""
        ref = create_ai_reference()
        assert ref == "ai-api-key/global/global/global"
    
    def test_create_auth_reference(self):
        """Test creating an auth reference."""
        ref = create_auth_reference("example-company", "example-project")
        assert ref == "auth/example-company/example-project/auth"


class TestValidation:
    """Tests for credential validation."""
    
    def test_validate_credential_structure_whatsapp(self):
        """Test validating WhatsApp credentials."""
        valid = {
            "twilio_account_sid": "AC1234567890abcdef1234567890abcdef",
            "twilio_auth_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
            "twilio_template_sid": "HX1234567890abcdef1234567890abcdef"
        }
        
        invalid = {
            "twilio_account_sid": "AC1234567890abcdef1234567890abcdef",
            # Missing auth_token and template_sid
        }
        
        assert validate_credential_structure(valid, SecretType.WHATSAPP)
        assert not validate_credential_structure(invalid, SecretType.WHATSAPP)
    
    def test_validate_credential_structure_email(self):
        """Test validating Email credentials."""
        valid = {
            "sendgrid_auth_value": "SG.1234567890abcdef1234567890abcdef",
            "sendgrid_from_email": "no-reply@example.com",
            "sendgrid_from_name": "Example Company",
            "sendgrid_template_id": "d-1234567890abcdef1234567890abcdef"
        }
        
        invalid = {
            "sendgrid_auth_value": "SG.1234567890abcdef1234567890abcdef",
            # Missing other fields
        }
        
        assert validate_credential_structure(valid, SecretType.EMAIL)
        assert not validate_credential_structure(invalid, SecretType.EMAIL)
    
    def test_validate_credential_structure_ai(self):
        """Test validating AI credentials."""
        valid = {
            "ai_api_key": "sk-1234567890abcdef1234567890abcdef"
        }
        
        invalid = {
            "api_key": "sk-1234567890abcdef1234567890abcdef"  # Wrong field name
        }
        
        assert validate_credential_structure(valid, SecretType.AI)
        assert not validate_credential_structure(invalid, SecretType.AI) 