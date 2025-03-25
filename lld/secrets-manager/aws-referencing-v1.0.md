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
│                │     │               │     │  Processing         │
│  DynamoDB      │     │  Context      │     │  Engine             │
│  wa_company_data│────▶│  Object       │────▶│                    │
│                │     │               │     │                    │
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
{credential_type}/{company_id}/{project_id}/{provider}
```

This format makes it easy to organize and manage permissions at different levels of granularity, while ensuring that credentials are properly scoped to specific projects within a company.

## Object Structure by Service Type

Each reference points to an object in AWS Secrets Manager with specific fields required for that service. Below are the structures for each service type.

### WhatsApp Channel (Twilio)

**Reference Path**: `whatsapp-credentials/{company_id}/{project_id}/twilio`

**Object Structure**:
```json
{
  "twilio_account_sid": "string - Twilio account identifier",
  "twilio_auth_token": "string - Twilio authentication token",
  "twilio_template_sid": "string - Twilio template identifier"
}
```

### SMS Channel (Twilio)

**Reference Path**: `sms-credentials/{company_id}/{project_id}/twilio`

**Object Structure**:
```json
{
  "twilio_account_sid": "string - Twilio account identifier",
  "twilio_auth_token": "string - Twilio authentication token",
  "twilio_template_sid": "string - Twilio template identifier"
}
```

### Email Channel (SendGrid)

**Reference Path**: `email-credentials/{company_id}/{project_id}/sendgrid`

**Object Structure**:
```json
{
  "sendgrid_auth_value": "string - SendGrid authentication value",
  "sendgrid_from_email": "string - Sender email address",
  "sendgrid_from_name": "string - Sender display name",
  "sendgrid_template_id": "string - SendGrid template identifier"
}
```

### AI API Key (Global)

**Reference Path**: `ai-api-key/global`

**Object Structure**:
```json
{
  "ai_api_key": "string - AI service API key used across all channels and companies"
}
```

### Authentication

**Reference Path**: `auth/{company_id}/{project_id}/auth`

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

### 2. Passing References in Context Object

The Channel Router includes these references in the context object:

```json
"channel_config": {
  "whatsapp": {
    "whatsapp_credentials_id": "whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio",
    "company_whatsapp_number": "+14155238886"
  }
}
```

### 3. Retrieving Values When Needed

The Processing Engine retrieves values using the references only when needed:

```javascript
// Get channel-specific credentials
async function getChannelCredentials(channelConfig) {
  const secretsManager = new AWS.SecretsManager();
  
  let whatsappCredentials = null;
  if (channelConfig.whatsapp) {
    const response = await secretsManager.getSecretValue({
      SecretId: channelConfig.whatsapp.whatsapp_credentials_id
    }).promise();
    
    whatsappCredentials = JSON.parse(response.SecretString);
  }
  
  return whatsappCredentials;
}

// Get AI API key separately
async function getAiCredentials(aiConfig) {
  const secretsManager = new AWS.SecretsManager();
  
  const response = await secretsManager.getSecretValue({
    SecretId: aiConfig.ai_api_key_reference
  }).promise();
  
  return JSON.parse(response.SecretString);
}

// Usage example
async function processMessage(contextObject) {
  // Get channel credentials based on channel type
  const channelCredentials = await getChannelCredentials(contextObject.channel_config);
  
  // Get AI credentials (global)
  const aiCredentials = await getAiCredentials(contextObject.ai_config);
  
  // Initialize clients
  const openai = new OpenAI({
    apiKey: aiCredentials.ai_api_key
  });
  
  const twilioClient = new twilio(
    channelCredentials.twilio_account_sid,
    channelCredentials.twilio_auth_token
  );
  
  // Process message using both credential sets
  // ...
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

## Separation of Channel and AI Credentials

The system maintains a clear separation between channel-specific credentials and AI service credentials:

1. **Channel Credentials**: 
   - Stored in paths like `whatsapp-credentials/{company_id}/{project_id}/twilio`
   - Contain channel-specific authentication details (account SIDs, tokens, etc.)
   - Scoped to specific company/project combinations
   - Used only by the relevant channel processing engines

2. **AI Credentials**: 
   - Stored in the global path `ai-api-key/global`
   - Referenced from each company's `ai_config.ai_api_key_reference` field
   - Used across all channels and companies
   - Single source of truth for the AI API key

### Benefits of This Separation

- **Clearer Security Boundaries**: Channel and AI credentials have distinct access patterns and permissions
- **Simplified Key Management**: The AI API key is managed in a single location
- **Reduced Duplication**: No need to store the same AI key in multiple channel credential objects
- **Easier Key Rotation**: Rotating the AI API key affects all services simultaneously
- **Future-Proofing**: If we need to switch AI providers, we only need to update one reference

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
        "arn:aws:secretsmanager:region:account-id:secret:whatsapp-credentials/*/*/twilio",
        "arn:aws:secretsmanager:region:account-id:secret:sms-credentials/*/*/twilio",
        "arn:aws:secretsmanager:region:account-id:secret:email-credentials/*/*/sendgrid",
        "arn:aws:secretsmanager:region:account-id:secret:ai-api-key/global"
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