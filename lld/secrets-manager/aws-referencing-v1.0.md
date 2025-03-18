# AWS Reference Management System

This document outlines how our system manages secure references to environmental variables in AWS, explaining the relationship between references stored in DynamoDB and the actual values stored in AWS Secrets Manager.

## Reference Architecture

### Overview

Our system uses a reference architecture where:

1. Only **references** are stored in DynamoDB and passed through the application
2. Actual variable values are securely stored in AWS Secrets Manager
3. Services retrieve values from Secrets Manager only when needed, using the references

This provides a secure, flexible system with centralized management of sensitive configuration.

### Flow Diagram

```
┌────────────────┐     ┌───────────────┐     ┌─────────────────────┐
│                │     │               │     │                     │
│  DynamoDB      │     │  Context      │     │  Processing         │
│  wa_company_data│────▶│  Object       │────▶│  Engine             │
│                │     │               │     │                     │
└────────────────┘     └───────────────┘     └──────────┬──────────┘
                                                        │
                                                        ▼
                                             ┌─────────────────────┐
                                             │                     │
                                             │  AWS Secrets        │
                                             │  Manager            │
                                             │                     │
                                             └─────────────────────┘
```

## Reference Format

References in DynamoDB follow a consistent path format:

```
{service}/{company_id}/{type}
```

This format makes it easy to organize and manage permissions at different levels of granularity.

## Object Structure by Service Type

Each reference points to an object in AWS Secrets Manager with specific fields required for that service. Below are the structures for each service type.

### WhatsApp Channel (Twilio)

**Reference Path**: `twilio/{company_id}/whatsapp-credentials`

**Object Structure**:
```json
{
  "account_sid": "string - Twilio account identifier",
  "auth_token": "string - Twilio authentication token",
  "phone_number": "string - WhatsApp enabled phone number",
  "messaging_service_sid": "string - Twilio messaging service identifier"
}
```

### SMS Channel (Twilio)

**Reference Path**: `twilio/{company_id}/sms-credentials`

**Object Structure**:
```json
{
  "account_sid": "string - Twilio account identifier",
  "auth_token": "string - Twilio authentication token",
  "phone_number": "string - SMS enabled phone number",
  "messaging_service_sid": "string - Twilio messaging service identifier"
}
```

### Email Channel (SendGrid)

**Reference Path**: `sendgrid/{company_id}/email-credentials`

**Object Structure**:
```json
{
  "auth_value": "string - SendGrid authentication value",
  "from_email": "string - Sender email address",
  "from_name": "string - Sender display name",
  "template_id": "string - SendGrid template identifier"
}
```

### AI Processing (OpenAI)

**Reference Path**: `openai/{company_id}/credentials`

**Object Structure**:
```json
{
  "auth_value": "string - OpenAI authentication value"
}
```

### Authentication

**Reference Path**: `auth/{company_id}/{project_id}`

**Object Structure**:
```json
{
  "auth_value": "string - Authentication value for API access"
}
```

## Implementation Details

### 1. Storing References in DynamoDB

The `wa_company_data` table stores only references:

```json
{
  "channel_config": {
    "whatsapp": {
      "whatsapp_credentials_id": "twilio/company-123/whatsapp-credentials"
    },
    "sms": {
      "sms_credentials_id": "twilio/company-123/sms-credentials"
    },
    "email": {
      "email_credentials_id": "sendgrid/company-123/email-credentials"
    }
  }
}
```

### 2. Passing References in Context Object

The Channel Router includes these references in the context object:

```json
"channel_config": {
  "whatsapp": {
    "whatsapp_credentials_id": "twilio/company-123/whatsapp-credentials"
  }
}
```

### 3. Retrieving Values When Needed

The Processing Engine retrieves values using the references only when needed:

```javascript
async function getCredentials(channelConfig) {
  const secretsManager = new AWS.SecretsManager();
  
  let whatsappCredentials = null;
  if (channelConfig.whatsapp) {
    const response = await secretsManager.getSecretValue({
      SecretId: channelConfig.whatsapp.whatsapp_credentials_id
    }).promise();
    
    whatsappCredentials = JSON.parse(response.SecretString);
  }
  
  return {
    whatsapp: whatsappCredentials
  };
}
```

## Security Benefits

This reference architecture provides several key security benefits:

1. **Separation of Concerns**: References can be freely passed around the system without exposing sensitive values
2. **Least Privilege**: Each service only accesses the specific secrets it needs
3. **Centralized Management**: All sensitive values are managed in one secure location
4. **Rotation Without Disruption**: Values can be rotated without changing references or code
5. **Comprehensive Audit Trail**: All access to values is logged and can be monitored
6. **IAM Integration**: Fine-grained access control through AWS IAM policies

## IAM Configuration

Services accessing Secrets Manager require specific IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": [
        "arn:aws:secretsmanager:region:account-id:secret:twilio/*",
        "arn:aws:secretsmanager:region:account-id:secret:openai/*"
      ]
    }
  ]
}
```

## Important Implementation Notes

1. **Value Caching**: Services may cache values briefly (1-5 minutes) to reduce Secrets Manager calls, but should never persist them to storage
2. **Error Handling**: Robust error handling should be implemented for Secrets Manager failures
3. **Reference Validation**: References should be validated before use to ensure proper format
4. **Default Timeouts**: Set appropriate timeouts for Secrets Manager calls (typically 2-5 seconds)
5. **Metrics and Monitoring**: Track Secret Manager access patterns for optimization 