# AWS Secrets Manager Structure

This document defines the structure of credentials stored in AWS Secrets Manager for the WhatsApp AI chatbot system, explaining how references in DynamoDB connect to the actual secrets.

## Reference Mechanism Overview

1. DynamoDB tables (specifically `wa_company_data`) store **references** to secrets, not the actual secrets
2. These references are paths that point to specific secrets in AWS Secrets Manager
3. When credentials are needed, services use these references to retrieve the actual credentials
4. This approach provides:
   - Centralized credential management
   - Automatic credential rotation
   - Fine-grained access control
   - Audit logging

## Reference Format

Secret references in DynamoDB follow a consistent path format:

```
{service}/{company_id}/{credential-type}
```

For example:
- `twilio/cucumber-recruitment/whatsapp-credentials`
- `sendgrid/cucumber-recruitment/email-credentials`
- `openai/cucumber-recruitment/api-key`

## Secrets Structure by Service

### API Keys (Authentication)

**Reference Pattern:** `secret/api-keys/{company_id}/{project_id}`

**Secret Structure:**
```json
{
  "api_key": "ak_example_api_key_not_real"
}
```

### Twilio WhatsApp Credentials

**Reference Pattern:** `twilio/{company_id}/whatsapp-credentials`

**Secret Structure:**
```json
{
  "account_sid": "AC_EXAMPLE_ACCOUNT_SID_NOT_REAL",
  "auth_token": "example_auth_token_not_real",
  "phone_number": "+14155238886",
  "messaging_service_sid": "MG_EXAMPLE_MESSAGING_SID_NOT_REAL"
}
```

### Twilio SMS Credentials

**Reference Pattern:** `twilio/{company_id}/sms-credentials`

**Secret Structure:**
```json
{
  "account_sid": "AC_EXAMPLE_ACCOUNT_SID_NOT_REAL",
  "auth_token": "example_auth_token_not_real",
  "phone_number": "+14155238886",
  "messaging_service_sid": "MG_EXAMPLE_MESSAGING_SID_NOT_REAL"
}
```

### SendGrid Email Credentials

**Reference Pattern:** `sendgrid/{company_id}/email-credentials`

**Secret Structure:**
```json
{
  "api_key": "SG_EXAMPLE_KEY_NOT_REAL",
  "from_email": "notifications@example.com",
  "from_name": "Example Company",
  "template_id": "d-example-template-id-not-real"
}
```

### OpenAI Credentials

**Reference Pattern:** `openai/{company_id}/api-key`

**Secret Structure:**
```json
{
  "api_key": "sk_example_openai_key_not_real"
}
```

## Retrieval Process

When a service needs to access credentials:

1. The service receives a reference from DynamoDB (via context object or direct query)
2. The service calls AWS Secrets Manager using the reference as the secret ID
3. AWS Secrets Manager returns the secret value
4. The service uses the credentials to make API calls

```javascript
// Example of credential retrieval
async function getCredentials(channelConfig) {
  // Initialize AWS Secrets Manager client
  const secretsManager = new AWS.SecretsManager();
  
  // Get WhatsApp credentials
  let whatsappCredentials = null;
  if (channelConfig.whatsapp) {
    const whatsappSecretResponse = await secretsManager.getSecretValue({
      SecretId: channelConfig.whatsapp.whatsapp_credentials_id
    }).promise();
    
    whatsappCredentials = JSON.parse(whatsappSecretResponse.SecretString);
  }
  
  // Return the credentials
  return {
    whatsapp: whatsappCredentials,
    // Other credentials if needed
  };
}
```

## Security Considerations

1. **IAM Policies**: Services should only have access to the specific secrets they need
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

2. **Secret Rotation**: Configure automatic rotation for sensitive credentials
   - API keys: 90-day rotation
   - Service credentials: 90-day rotation or follow service provider recommendations

3. **Encryption**: All secrets are automatically encrypted at rest by AWS Secrets Manager

4. **Access Logging**: Enable CloudTrail logging for all Secrets Manager operations

5. **Temporary Caching**: Services may temporarily cache credentials in memory to reduce calls to Secrets Manager, but should never persist credentials to disk

## Maintenance and Operations

1. **Adding New Credentials**:
   - Create the secret in AWS Secrets Manager
   - Add the reference to the appropriate DynamoDB record
   - Update IAM policies if needed

2. **Rotating Credentials**:
   - Use AWS Secrets Manager rotation feature
   - For manual rotation, update the secret value in AWS Secrets Manager without changing the reference
   
3. **Auditing Access**:
   - Review CloudTrail logs for all GetSecretValue operations
   - Set up alerts for unusual access patterns

4. **Emergency Credential Rotation**:
   - In case of a credential leak, immediately rotate the affected credential
   - No changes to references or code are needed 