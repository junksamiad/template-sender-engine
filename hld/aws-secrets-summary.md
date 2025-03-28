# AWS Secrets Manager Structure Summary

Based on `lld/secrets-manager/aws-referencing-v1.0.md`, here's the structure of secrets in AWS Secrets Manager:

## Reference Format

All secrets follow this path format:
```
{credential_type}/{company_id}/{project_id}/{provider}
```

## Secret Types and Structures

### 1. WhatsApp Channel (Twilio)
**Path**: `whatsapp-credentials/{company_id}/{project_id}/twilio`

```json
{
  "twilio_account_sid": "string - Twilio account identifier",
  "twilio_auth_token": "string - Twilio authentication token",
  "twilio_template_sid": "string - Twilio template identifier"
}
```

### 2. SMS Channel (Twilio)
**Path**: `sms-credentials/{company_id}/{project_id}/twilio`

```json
{
  "twilio_account_sid": "string - Twilio account identifier",
  "twilio_auth_token": "string - Twilio authentication token",
  "twilio_template_sid": "string - Twilio template identifier"
}
```

### 3. Email Channel (SendGrid)
**Path**: `email-credentials/{company_id}/{project_id}/sendgrid`

```json
{
  "sendgrid_auth_value": "string - SendGrid authentication value",
  "sendgrid_from_email": "string - Sender email address",
  "sendgrid_from_name": "string - Sender display name",
  "sendgrid_template_id": "string - SendGrid template identifier"
}
```

### 4. AI API Key (Global)
**Path**: `ai-api-key/global`

```json
{
  "ai_api_key": "string - AI service API key used across all channels and companies"
}
```

### 5. Authentication
**Path**: `auth/{company_id}/{project_id}/auth`

```json
{
  "auth_value": "string - Authentication value for API access"
}
```

## Usage Pattern

1. References to these secrets are stored in DynamoDB
2. References are passed through the application via context objects
3. Actual values are only retrieved from Secrets Manager when needed
4. Client code validates and uses the retrieved secrets

## Example Secret Reference in DynamoDB

```json
{
  "channel_config": {
    "whatsapp": {
      "whatsapp_credentials_id": "whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio",
      "company_whatsapp_number": "+14155238886"
    },
    "sms": {
      "sms_credentials_id": "sms-credentials/cucumber-recruitment/cv-analysis/twilio"
    },
    "email": {
      "email_credentials_id": "email-credentials/cucumber-recruitment/cv-analysis/sendgrid"
    }
  }
}
```

These references in DynamoDB point to the actual secret values stored in AWS Secrets Manager. 