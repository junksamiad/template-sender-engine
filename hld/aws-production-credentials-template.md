# ⚠️ AWS PRODUCTION CREDENTIALS ⚠️

## ❗ATTENTION AI AGENT❗
This document has two purposes:
1. It contains AWS account credentials provided by the human supervisor
2. YOU (the AI agent) must document all resources you create during implementation

## 🔐 AWS Account Credentials
These credentials provide access to all AWS services (not service-specific):
```
AWS_REGION=eu-north-1
AWS_ACCOUNT_ID=[ACCOUNT_ID]
AWS_ACCESS_KEY_ID=[ACCESS_KEY_ID]
AWS_SECRET_ACCESS_KEY=[SECRET_ACCESS_KEY]
```

## 🛠️ AWS Resources Tracking Document
**AI AGENT: Document all resources you create below**

### DynamoDB Tables
```
# Document tables as you create them:
CONVERSATIONS_TABLE_NAME=
COMPANY_DATA_TABLE_NAME=
```

### SQS Queues
```
# Document queues as you create them:
WHATSAPP_QUEUE_URL=
EMAIL_QUEUE_URL=
SMS_QUEUE_URL=
DLQ_URL=
```

### IAM Roles
```
# Document roles as you create them:
LAMBDA_EXECUTION_ROLE=
API_GATEWAY_ROLE=
```

### CloudWatch Resources
```
# Document CloudWatch resources as you create them:
LOG_GROUP_PREFIX=
DASHBOARD_NAME=
```

### Secrets Manager Secrets
```
# Document secrets as you create them:
TWILIO_CREDENTIALS_SECRET_NAME=
OPENAI_CREDENTIALS_SECRET_NAME=
```

## 📋 Resource Documentation Process

AI Agent: Follow these steps when working with AWS resources:

1. **Before creating any resource**:
   - Document what you plan to create and its purpose
   - Request explicit authorization from the human supervisor

2. **After creating each resource**:
   - Update this document with resource details (ARNs, URLs, names)
   - Document any configuration specifics
   - Commit and push the updated document
   - Mark the resource as completed with ✅

3. **For all Lambda functions, include**:
   - Function name and ARN
   - IAM role used
   - Environment variables (excluding sensitive values)
   - Trigger configuration

4. **For all DynamoDB tables, include**:
   - Table name and ARN
   - Key schema
   - Throughput settings

## ⚠️ IMPORTANT SECURITY NOTES ⚠️

1. NEVER include AWS credentials in code or commit them to the repository
2. Use AWS Secrets Manager for all sensitive values
3. Follow least privilege principle for all IAM roles
4. Keep this document updated with ALL created resources

## 📣 DEPLOYMENT AUTHORIZATION

Before proceeding with any resource creation in AWS:
1. Document specifically what you intend to create
2. Include estimated costs where applicable
3. Explain why the resource is needed
4. Provide a rollback plan
5. **Wait for explicit human authorization**

---
*This document serves as both a credentials reference and a resource inventory*
