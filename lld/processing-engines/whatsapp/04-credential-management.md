# WhatsApp Processing Engine - Credential Management

> **Part 4 of 10 in the WhatsApp Processing Engine documentation series**

## 1. Introduction

This document details how the WhatsApp Processing Engine securely accesses and manages credentials for external services (OpenAI and Twilio) using AWS Secrets Manager. The system follows a reference-based approach where only credential references are stored in DynamoDB and passed through the system, with actual values retrieved from Secrets Manager when needed.

## 2. Credential Reference Architecture

### 2.1 Design Principles

The credential management system follows these key principles:

1. **Reference-Only Storage**: Only credential references are stored in DynamoDB and context objects
2. **Just-in-Time Access**: Credentials are retrieved only when needed for specific API calls
3. **Clear Separation**: Different credential types are stored in separate secrets
4. **Scoped Access**: Each credential is scoped to a specific company/project combination
5. **Secure Handling**: Credentials are never logged or persisted outside Secrets Manager

### 2.2 Flow Diagram

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

## 3. Reference Format

References in the context object and DynamoDB follow a consistent path format:

```
{credential_type}/{company_id}/{project_id}/{provider}
```

For example:
- `whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio`
- `ai-api-key/global`

This format makes credentials easy to organize, manage, and scope appropriately.

## 4. Credential Types and Structures

### 4.1 WhatsApp Channel (Twilio)

**Reference Path**: `whatsapp-credentials/{company_id}/{project_id}/twilio`

**Object Structure**:
```json
{
  "twilio_account_sid": "AC1234567890abcdef1234567890abcdef",
  "twilio_auth_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "twilio_template_sid": "HX1234567890abcdef1234567890abcdef"
}
```

### 4.2 AI API Key (Global)

**Reference Path**: `ai-api-key/global`

**Object Structure**:
```json
{
  "ai_api_key": "sk-1234567890abcdef1234567890abcdef"
}
```

## 5. Implementation Details

### 5.1 Accessing Credentials in the Processing Engine

The WhatsApp Processing Engine retrieves credentials from Secrets Manager at two key points:

1. Before creating a thread with OpenAI (retrieving the OpenAI API key)
2. Before sending a message via Twilio (retrieving Twilio credentials)

### 5.2 Credential Retrieval Function

```javascript
/**
 * Retrieve credentials from AWS Secrets Manager using the provided reference
 * @param {string} secretId - Reference to the secret containing credentials
 * @returns {Promise<object>} - The parsed credentials object
 */
async function getCredentials(secretId) {
  try {
    // Create Secrets Manager client
    const secretsManager = new AWS.SecretsManager();
    
    // Get the secret value
    const secretValue = await secretsManager.getSecretValue({
      SecretId: secretId
    }).promise();
    
    // Verify that the secret has a value
    if (!secretValue.SecretString) {
      throw new Error(`No secret found for ID: ${secretId}`);
    }
    
    // Parse the secret value as JSON
    const credentials = JSON.parse(secretValue.SecretString);
    
    return credentials;
  } catch (error) {
    // Enhanced error logging with redacted secret ID
    const redactedSecretId = secretId.split('/').slice(0, -1).join('/') + '/****';
    
    console.error('Error retrieving credentials from Secrets Manager', {
      redacted_secret_id: redactedSecretId,
      error_code: error.code,
      error_message: error.message
    });
    
    // Rethrow with sanitized message
    throw new Error(`Failed to retrieve credentials: ${error.code}`);
  }
}
```

### 5.3 Extracting References from Context Object

```javascript
// Extract credential references from context object
const { frontend_payload, channel_config, ai_config } = contextObject;
const whatsappCredentialsId = channel_config.whatsapp.whatsapp_credentials_id;
const aiApiKeyReference = ai_config.ai_api_key_reference;

// Log reference access (without showing the actual reference path)
console.log('Retrieving channel credentials', {
  channel: 'whatsapp',
  credential_type: 'whatsapp-credentials'
});
```

### 5.4 Retrieving and Using OpenAI Credentials

```javascript
// Get AI credentials from AWS Secrets Manager
const aiCredentials = await getCredentials(aiApiKeyReference);

// Initialize OpenAI client with API key
const openai = new OpenAI({
  apiKey: aiCredentials.ai_api_key
});

// Process with OpenAI
const aiResponse = await processWithOpenAI(openai, conversation, contextObject);
```

### 5.5 Retrieving and Using Twilio Credentials

```javascript
// Get Twilio credentials from AWS Secrets Manager
const twilioCredentials = await getCredentials(whatsappCredentialsId);

// Initialize Twilio client
const twilioClient = twilio(
  twilioCredentials.twilio_account_sid,
  twilioCredentials.twilio_auth_token
);

// Send message via Twilio
const deliveryResult = await sendViaTwilio(
  twilioClient, 
  recipient_data.recipient_tel, 
  aiResponse.content, 
  twilioCredentials.twilio_template_sid
);
```

## 6. Error Handling

The credential retrieval process implements specialized error handling to maintain security while providing useful debugging information:

### 6.1 Error Categories

1. **Access Denied**: The Lambda doesn't have permission to access the secret
2. **Resource Not Found**: The referenced secret doesn't exist
3. **Validation Exception**: The secret has invalid format
4. **Service Exception**: AWS Secrets Manager service issues
5. **Throttling**: Rate limit exceeded for Secrets Manager

### 6.2 Error Handling Implementation

```javascript
try {
  const credentials = await getCredentials(secretId);
  // Use credentials
} catch (error) {
  // Categorize error
  let errorCategory = 'unknown';
  
  if (error.code === 'AccessDeniedException') {
    errorCategory = 'access_denied';
  } else if (error.code === 'ResourceNotFoundException') {
    errorCategory = 'not_found';
  } else if (error.code === 'ValidationException') {
    errorCategory = 'validation';
  } else if (error.code === 'ServiceException') {
    errorCategory = 'service';
  } else if (error.code === 'ThrottlingException') {
    errorCategory = 'throttling';
  }
  
  // Log error with category
  console.error('Credential retrieval error', {
    error_category: errorCategory,
    credential_type: secretId.split('/')[0]
  });
  
  // Handle based on category
  if (errorCategory === 'throttling') {
    // Implement exponential backoff for throttling
    await new Promise(resolve => setTimeout(resolve, 1000));
    // Retry operation
  } else {
    // For other errors, fail the operation
    throw new Error(`Credential error: ${errorCategory}`);
  }
}
```

## 7. Security Considerations

### 7.1 Permissions Model

The WhatsApp Processing Engine Lambda requires these IAM permissions for Secrets Manager access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": [
        "arn:aws:secretsmanager:${region}:${account-id}:secret:whatsapp-credentials/*/*/twilio",
        "arn:aws:secretsmanager:${region}:${account-id}:secret:ai-api-key/global"
      ]
    }
  ]
}
```

### 7.2 Credential Lifecycle

1. **Creation**: Credentials are created and stored in Secrets Manager by operations personnel
2. **Rotation**: Credentials are rotated on a regular schedule (90 days recommended)
3. **Access**: Credentials are accessed only when needed for API calls
4. **Monitoring**: All access to credentials is logged and monitored

### 7.3 Never Log Credentials

The system is designed to never log actual credential values:

```javascript
// WRONG - Don't do this!
console.log('Retrieved API key', apiKey);

// CORRECT - Log reference only
console.log('Retrieved credentials for', {
  credential_type: secretId.split('/')[0],
  company_id: secretId.split('/')[1]
});
```

## 8. Separation of Channel and AI Credentials

The system maintains a clear separation between channel-specific credentials and AI service credentials:

### 8.1 Channel Credentials

- Stored in paths like `whatsapp-credentials/{company_id}/{project_id}/twilio`
- Contain channel-specific authentication details
- Scoped to specific company/project combinations

### 8.2 AI Credentials

- Stored in the global path `ai-api-key/global`
- Referenced from each company's `ai_config.ai_api_key_reference` field
- Used across all channels and companies
- Single source of truth for the AI API key

### 8.3 Benefits of This Separation

- **Clearer Security Boundaries**: Different types of credentials have distinct access patterns
- **Simplified Key Management**: The AI API key is managed in a single location
- **Reduced Duplication**: The same AI key doesn't need to be stored multiple times
- **Easier Key Rotation**: Rotating the AI API key affects all services simultaneously

## 9. Implementation in AWS CDK

```typescript
// In CDK stack
const whatsappLambda = new lambda.Function(this, 'WhatsAppProcessingFunction', {
  // Other configuration
  environment: {
    // Other environment variables
    OPENAI_API_KEY_SECRET_NAME: 'ai-api-key/global'
  }
});

// Grant permission to access specific secrets
whatsappLambda.addToRolePolicy(new iam.PolicyStatement({
  actions: ['secretsmanager:GetSecretValue'],
  resources: [
    `arn:aws:secretsmanager:${this.region}:${this.account}:secret:ai-api-key/*`,
    `arn:aws:secretsmanager:${this.region}:${this.account}:secret:whatsapp-credentials/*`
  ]
}));
```

## 10. Best Practices for Credential Management

1. **Cache with Caution**: If implementing credential caching to reduce API calls, use short-lived memory caching only
2. **Clear Memory**: Clear credentials from memory when no longer needed
3. **Handle Failed Rotations**: Implement fallback mechanisms for credential rotation failures
4. **Monitor Access Patterns**: Set up alerts for unusual access patterns to credentials
5. **Audit Regular Access**: Review who and what is accessing credentials on a regular basis

## 11. Related Documentation

- [Overview and Architecture](./01-overview-architecture.md)
- [AWS Reference Management](../../secrets-manager/aws-referencing-v1.0.md)
- [OpenAI Integration](./05-openai-integration.md)
- [Twilio Integration](./07-twilio-integration.md) 