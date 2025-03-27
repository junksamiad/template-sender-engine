# Test Environment Configuration

## Overview
This document outlines all test accounts, credentials, and configurations needed for local and AWS testing during implementation. The AI agent will reference this document when setting up test environments.

## Required Test Accounts

### WhatsApp/Twilio
- [ ] Twilio Account SID
- [ ] Twilio Auth Token
- [ ] WhatsApp Test Phone Numbers
- [ ] Approved Message Templates
- [ ] Webhook URLs

### OpenAI
- [ ] API Key
- [ ] Assistant ID
- [ ] Model Configuration

### AWS Test Environment
- [ ] AWS Account ID
- [ ] Test Environment Region
- [ ] IAM Role ARNs
- [ ] Test SQS Queue URLs
- [ ] Test DynamoDB Table Names

### Test Recipients
- [ ] List of Test Phone Numbers
- [ ] Test Email Addresses
- [ ] Test Company IDs

## Configuration Instructions

### Local Testing
1. Create a `.env.test` file in the root directory
2. Add the following environment variables (values to be provided):
```
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
OPENAI_API_KEY=
OPENAI_ASSISTANT_ID=
TEST_PHONE_NUMBER=
TEST_WEBHOOK_URL=
```

### AWS Testing
1. Create a `test-config.json` file in the `config` directory
2. Add the following configuration (values to be provided):
```json
{
  "aws": {
    "region": "",
    "accountId": "",
    "iamRole": "",
    "sqsQueues": {
      "whatsapp": "",
      "email": "",
      "sms": "",
      "dlq": ""
    },
    "dynamoTables": {
      "conversations": "",
      "companyData": ""
    }
  },
  "twilio": {
    "accountSid": "",
    "testNumbers": [],
    "templates": []
  },
  "openai": {
    "assistantId": "",
    "model": "gpt-4-turbo-preview"
  },
  "testRecipients": {
    "phones": [],
    "emails": [],
    "companyIds": []
  }
}
```

## Security Notes
1. Never commit actual credentials to the repository
2. Store all sensitive values in AWS Secrets Manager
3. Use environment variables for local testing
4. Rotate test credentials regularly

## Template Examples
Add approved message templates here when available:

### WhatsApp Templates
- Template Name: 
- Template Content:
- Variables:
- Language:
- Category:

## Next Steps
1. Fill in the test account details above
2. Configure local environment variables
3. Set up AWS test environment
4. Verify all test accounts are working 