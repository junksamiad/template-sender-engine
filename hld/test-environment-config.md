# Test Environment Configuration

## Overview
This document outlines all test accounts, credentials, and configurations needed for local testing during implementation. The AI agent will reference this document when setting up the local test environment.

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

### Test Recipients
- [ ] List of Test Phone Numbers
- [ ] Test Email Addresses
- [ ] Test Company IDs

## Local Testing Configuration

1. Create a `.env.test` file in the root directory
2. Add the following environment variables (values to be provided):
```
# Twilio Configuration
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TEST_PHONE_NUMBER=
TEST_WEBHOOK_URL=

# OpenAI Configuration
OPENAI_API_KEY=
OPENAI_ASSISTANT_ID=

# Test Recipients
TEST_RECIPIENT_PHONE=
TEST_RECIPIENT_EMAIL=
TEST_COMPANY_ID=

# Local Development
LOCAL_PORT=3000
NODE_ENV=development
```

## Security Notes
1. Never commit actual credentials to the repository
2. Keep `.env.test` in `.gitignore`
3. Use environment variables for all sensitive data
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
2. Configure local environment variables in `.env.test`
3. Verify all test accounts are working locally
4. Document any issues or missing configurations 