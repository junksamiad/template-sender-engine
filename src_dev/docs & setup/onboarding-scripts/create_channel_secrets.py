import boto3
import json
import os
import re
import sys
from botocore.exceptions import ClientError

# --- Configuration ---
# Use environment variable or default for region
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-north-1")
PROJECT_PREFIX = "ai-multi-comms" # Should match SAM template

# Initialize Secrets Manager client
secrets_manager_client = None
try:
    secrets_manager_client = boto3.client("secretsmanager", region_name=AWS_REGION)
    print(f"Initialized Secrets Manager client in region: {AWS_REGION}")
except Exception as e:
    print(f"Error: Failed to initialize Secrets Manager client: {e}")
    sys.exit(1)

def slugify(value):
    """Converts a string to a slug (lowercase, hyphens for spaces/special chars)."""
    value = str(value).strip().lower()
    # Replace spaces and known problematic chars with hyphens
    value = re.sub(r'[\s_/\\\.]+', '-', value)
    # Remove any characters that are not alphanumeric or hyphens
    value = re.sub(r'[^a-z0-9-]', '', value)
    # Remove leading/trailing hyphens
    value = value.strip('-')
    if not value:
        raise ValueError("Resulting slug is empty after sanitization.")
    return value

def create_secret_if_not_exists(name, description, secret_string):
    """Attempts to create a secret, handling ResourceExistsException gracefully."""
    if not secrets_manager_client:
        print("Error: Secrets Manager client not initialized.")
        return False
    try:
        response = secrets_manager_client.create_secret(
            Name=name,
            Description=description,
            SecretString=secret_string
        )
        print(f"SUCCESS: Created secret '{name}' (ARN: {response.get('ARN')})" )
        return True
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') == 'ResourceExistsException':
            print(f"INFO: Secret '{name}' already exists. Skipping creation.")
            return True # Treat existing as success for this script's purpose
        else:
            print(f"ERROR: Failed to create secret '{name}'. AWS Error: {e}")
            return False
    except Exception as e:
        print(f"ERROR: An unexpected error occurred creating secret '{name}': {e}")
        return False

def main():
    """Main function to prompt user and create secrets."""
    print("--- Channel Secret Creation Script ---")

    # 1. Get Environment
    while True:
        env = input("Enter target environment (dev or prod): ").strip().lower()
        if env in ['dev', 'prod']:
            break
        else:
            print("Invalid environment. Please enter 'dev' or 'prod'.")

    # 2. Get Company and Project Names
    print("\nPlease enter names using standard characters. They will be converted.")
    print("Example: 'Cucumber Recruitment' becomes 'cucumber-recruitment'")
    while True:
        try:
            company_name = input("Enter Company Name: ").strip()
            company_slug = slugify(company_name)
            break
        except ValueError as e:
            print(f"Error processing Company Name: {e}. Please try again.")
        except Exception as e:
            print(f"Unexpected error with Company Name: {e}. Please try again.")

    while True:
        try:
            project_name = input("Enter Project Name: ").strip()
            project_slug = slugify(project_name)
            break
        except ValueError as e:
            print(f"Error processing Project Name: {e}. Please try again.")
        except Exception as e:
            print(f"Unexpected error with Project Name: {e}. Please try again.")

    print(f"\nEnvironment: {env}")
    print(f"Company Slug: {company_slug}")
    print(f"Project Slug: {project_slug}")
    print("-" * 20)

    # 3. Construct Secret Names and Placeholder Data
    secrets_to_create = []

    # WhatsApp (Twilio)
    whatsapp_name = f"{PROJECT_PREFIX}/whatsapp-credentials/{company_slug}/{project_slug}/twilio-{env}"
    whatsapp_desc = f"Twilio WhatsApp Credentials for {company_name}/{project_name} ({env.capitalize()})"
    whatsapp_secret = json.dumps({
        "twilio_account_sid": f"REPLACE_WITH_{env.upper()}_SID",
        "twilio_auth_token": f"REPLACE_WITH_{env.upper()}_TOKEN",
        "twilio_template_sid": f"REPLACE_WITH_{env.upper()}_TEMPLATE_SID"
    })
    secrets_to_create.append((whatsapp_name, whatsapp_desc, whatsapp_secret))

    # SMS (Twilio)
    sms_name = f"{PROJECT_PREFIX}/sms-credentials/{company_slug}/{project_slug}/twilio-{env}"
    sms_desc = f"Twilio SMS Credentials for {company_name}/{project_name} ({env.capitalize()})"
    sms_secret = json.dumps({
        "twilio_account_sid": f"REPLACE_WITH_{env.upper()}_SID", # Often same SID/Token as WhatsApp
        "twilio_auth_token": f"REPLACE_WITH_{env.upper()}_TOKEN",
        "twilio_template_sid": f"REPLACE_WITH_{env.upper()}_SMS_TEMPLATE_SID" # May differ
    })
    secrets_to_create.append((sms_name, sms_desc, sms_secret))

    # Email (SendGrid)
    email_name = f"{PROJECT_PREFIX}/email-credentials/{company_slug}/{project_slug}/sendgrid-{env}"
    email_desc = f"SendGrid Email Credentials for {company_name}/{project_name} ({env.capitalize()})"
    email_secret = json.dumps({
        "sendgrid_api_key": f"REPLACE_WITH_{env.upper()}_SENDGRID_KEY"
    })
    secrets_to_create.append((email_name, email_desc, email_secret))

    # 4. Create Secrets
    print("\nAttempting to create secrets...")
    success_count = 0
    for name, desc, secret_str in secrets_to_create:
        if create_secret_if_not_exists(name, desc, secret_str):
            success_count += 1

    print("-" * 20)
    print(f"Script finished. {success_count}/{len(secrets_to_create)} secrets processed (created or already existed).")
    if success_count < len(secrets_to_create):
        print("One or more secrets failed to create. Check AWS errors above.")
    print("\nIMPORTANT: Remember to manually update the placeholder values in the created/existing secrets with the actual credentials.")

if __name__ == "__main__":
    main() 