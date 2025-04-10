# AWS Secrets Manager - Low-Level Design (LLD) - Dev Environment

## 1. Introduction

This document details the configuration and usage of AWS Secrets Manager within the AI Multi-Communications Engine's development (`src_dev`) environment. Secrets Manager is used to securely store and manage sensitive credentials required for external service integrations (e.g., Twilio, OpenAI, SendGrid).

## 2. Purpose & Interaction Flow

*   **Purpose:** To store API keys, tokens, and other sensitive credentials needed by the Channel Processor Lambda functions (e.g., `whatsapp-channel-processor-dev`, `sms-channel-processor-dev`, `email-channel-processor-dev`).
*   **Interaction:**
    1.  Configuration entries in the `company-data-dev` DynamoDB table contain *reference strings* (secret names/paths) pointing to the relevant credentials in Secrets Manager (e.g., under `channel_config.<channel>.credentials_id` or `ai_config.ai_api_key_reference`).
    2.  The Channel Router Lambda reads these reference strings from DynamoDB and includes them in the `Context Object` sent to the SQS queue.
    3.  The respective Channel Processor Lambda receives the `Context Object`, extracts the reference string for the required service (e.g., Twilio, OpenAI).
    4.  The Channel Processor Lambda uses the reference string to call the `secretsmanager:GetSecretValue` API action to retrieve the actual sensitive credential value(s) at runtime.
    5.  The Channel Router Lambda **does not** directly interact with Secrets Manager.

## 3. Secret Naming Convention

A consistent naming convention will be used for secrets in the development environment, based on the structure outlined in `lld/secrets-manager/aws-referencing-v1.0.md`:

**Channel-Specific Credentials:**
```
{credential_type}/{company_name}/{project_name}/{provider}
```
*   `{credential_type}`: Identifies the channel (e.g., `whatsapp-credentials`, `sms-credentials`, `email-credentials`).
*   `{company_name}`: The unique identifier for the company (e.g., `cucumber-recruitment`).
*   `{project_name}`: The unique identifier for the project (e.g., `cv-analysis`).
*   `{provider}`: The service provider for the channel (e.g., `twilio`, `sendgrid`).

**Channel-Specific AI API Keys:**
```
openai-api-key/<channel>
```
*   `<channel>`: The channel the key applies to (`whatsapp`, `sms`, `email`).
*   Separate secrets hold the API keys for OpenAI usage specific to each channel.

**Examples:**

*   `whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio`
*   `sms-credentials/cucumber-recruitment/cv-analysis/twilio`
*   `email-credentials/cucumber-recruitment/cv-analysis/sendgrid`
*   `openai-api-key/whatsapp`
*   `openai-api-key/sms`
*   `openai-api-key/email`

## 4. Required Secrets & JSON Structure (Initial Setup - Dev)

The following secrets need to be created, using the JSON structures defined in `lld/secrets-manager/aws-referencing-v1.0.md`:

| Secret Name Pattern                                   | Service        | JSON Structure                                                                                                                                                            | Initial Values                                    |
| :---------------------------------------------------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------------------------------ |
| `whatsapp-credentials/{company_name}/{project_name}/twilio` | Twilio         | `{"twilio_account_sid": "string", "twilio_auth_token": "string", "twilio_template_sid": "string"}`                                                                       | Placeholders (e.g., "PLACEHOLDER_SID", "...")     |
| `sms-credentials/{company_name}/{project_name}/twilio`      | Twilio         | `{"twilio_account_sid": "string", "twilio_auth_token": "string", "twilio_template_sid": "string"}`                                                                       | Placeholders                                      |
| `email-credentials/{company_name}/{project_name}/sendgrid`  | SendGrid (TBC) | `{"sendgrid_auth_value": "string", "sendgrid_from_email": "string", "sendgrid_from_name": "string", "sendgrid_template_id": "string"}`                                | Placeholders                                      |
| `openai-api-key/whatsapp`                             | OpenAI         | `{"ai_api_key": "string"}`                                                                                                                                                  | Placeholders (e.g., "PLACEHOLDER_WHATSAPP_...")  |
| `openai-api-key/sms`                                  | OpenAI         | `{"ai_api_key": "string"}`                                                                                                                                                  | Placeholders (e.g., "PLACEHOLDER_SMS_...")     |
| `openai-api-key/email`                                 | OpenAI         | `{"ai_api_key": "string"}`                                                                                                                                                  | Placeholders (e.g., "PLACEHOLDER_EMAIL_...")    |

*(TBC = To Be Confirmed if SendGrid is the chosen provider)*

Placeholder values will be used initially. Actual credential values can be updated later using the `aws secretsmanager update-secret` command without requiring Lambda code changes.

## 5. JSON Structure within Secrets

*   **Status:** Defined above in Section 4. Refer to `lld/secrets-manager/aws-referencing-v1.0.md` for detailed field descriptions if needed.

## 6. Region

Secrets must be created in the same AWS region as the Lambda functions that will access them (e.g., `eu-north-1`).

## 7. IAM Permissions

*   The IAM role associated with each Channel Processor Lambda (e.g., `ai-multi-comms-whatsapp-channel-processor-dev-role`) requires `secretsmanager:GetSecretValue` permission.
*   **Action:** Verify the existing policy (`ai-multi-comms-whatsapp-channel-processor-dev-policy`) grants this permission and update the `Resource` list to match the naming convention defined in Section 3.
*   **Best Practice:** Permissions should be scoped using the `Resource` element in the IAM policy to restrict access only to secrets matching the expected naming patterns (e.g., `arn:aws:secretsmanager:<region>:<account-id>:secret:whatsapp-credentials/*/*/twilio-*`, `arn:aws:secretsmanager:<region>:<account-id>:secret:openai-api-key/whatsapp-*`, etc.).

## 8. Creation Method

Secrets will be created and managed primarily via the AWS CLI (`aws secretsmanager create-secret`, `aws secretsmanager update-secret`).

## 9. Excluded Secrets

*   API Gateway API Keys will **not** be stored in Secrets Manager. They are managed directly within the API Gateway service. 