# Development Environment - Business Onboarding Process

> **Note:** This document outlines the onboarding process specifically for the **development environment (`src_dev`)**. Procedures may differ significantly from the production environment, which relies more heavily on Infrastructure as Code (IaC). This guide assumes setup is performed primarily via the AWS Console or CLI.

## 1. Introduction

This document outlines the process for onboarding new businesses (or test projects) within the **development environment** of the Adaptix Innovation multi-channel communications platform. The goal is to facilitate rapid setup for testing and development purposes. This document serves as a guide for the team members responsible for setting up new test clients/projects.

## 2. Onboarding Overview

The development onboarding process mirrors the production one but uses development-specific resources:

1.  **Business Requirements Analysis**: Understanding the client's business needs and use cases (can be simplified for dev testing).
2.  **(Optional) Messaging Provider Configuration**: Setting up accounts like Twilio for WhatsApp/SMS if testing end-to-end message flow.
3.  **Database Configuration**: Creating necessary records in the development DynamoDB table (`company-data-dev`).
4.  **API Gateway Configuration**: Setting up API Keys and Usage Plans for authentication.
5.  **(Optional) Secrets Manager Configuration**: Storing external credentials securely (e.g., Twilio, OpenAI, Email provider).
6.  **(Optional) AI Assistant Configuration**: Setting up and training the OpenAI assistant if needed for the use case.
7.  **Frontend Development/Testing**: Creating/using a frontend or test script for the business use case.
8.  **Testing & Deployment**: Validating end-to-end functionality within the dev environment.
9.  **Monitoring Setup**: Checking CloudWatch logs.

## 3. Business Requirements Analysis (Development Context)

For development, this step can be simplified:

-   **Test Use Case**: Define the scenario being tested (e.g., simple message send, specific data mapping, recruitment CV analysis).
-   **Test Data**: Determine the structure of the data needed for the test request payload (see sample payloads).
-   **Test Template**: If testing WhatsApp, identify an approved template or use a simple notification structure for testing the router.

## 4. (Optional) Messaging Provider Configuration (Development Context)

If testing the full message flow (e.g., WhatsApp, SMS):

-   Use development/test credentials for the provider (e.g., Twilio).
-   Ensure a test sender (e.g., WhatsApp number, SMS number) is configured.
-   Use an existing approved message template or create one specifically for testing.
-   Document any relevant Template IDs/SIDs.

*If only testing the Channel Router and initial queuing, this section might be skipped.* 

## 5. Database Configuration (`company-data-dev`)

### 5.1 Creating Company/Project Entry in `company-data-dev`

Create a new item in the `company-data-dev` DynamoDB table using the AWS Console or CLI. Ensure `_dev` suffixes are used where appropriate for related resource names/references.

```json
/**
 * Example company-data-dev entry for a test recruitment project
 */
{
  "company_id": "ci-aaa-001",
  "project_id": "pi-aaa-001",
  "company_name": "Cucumber Recruitment",
  "project_name": "Clarify CV",
  "api_key_reference": "a1b2c3d4e5", // ** CRITICAL: Set this to the API Gateway Key ID created for this project (see Section 6) **
  "allowed_channels": ["whatsapp", "sms", "email"],
  "rate_limits": {
    "requests_per_minute": 60,
    "requests_per_day": 2000,
    "concurrent_conversations": 30,
    "max_message_length": 4096
  },
  "project_status": "active",
  "company_rep": {
    "company_rep_1": "Carol",
    "company_rep_2": null,
    "company_rep_3": null,
    "company_rep_4": null,
    "company_rep_5": null
  },
  "ai_config": {
    "openai_config": {
      "whatsapp": {
        "api_key_reference": "openai-api-key/whatsapp",
        "assistant_id_template_sender": "asst_cv_clarification_abc123",
        "assistant_id_replies": "asst_recruitment_replies_xyz789",
        "assistant_id_3": "",
        "assistant_id_4": "",
        "assistant_id_5": ""
      },
      "sms": {
        "api_key_reference": "openai-api-key/sms",
        "assistant_id_template_sender": "",
        "assistant_id_replies": "",
        "assistant_id_3": "",
        "assistant_id_4": "",
        "assistant_id_5": ""
      },
      "email": {
        "api_key_reference": "openai-api-key/email",
        "assistant_id_template_sender": "",
        "assistant_id_replies": "",
        "assistant_id_3": "",
        "assistant_id_4": "",
        "assistant_id_5": ""
      }
    }
  },
  "channel_config": {
    "whatsapp": {
      "company_whatsapp_number": "+447588713814", // Example WhatsApp number. **Must include international prefix (+44).**
      "whatsapp_credentials_id": "whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio" // Reference to WhatsApp credentials secret
    },
    "email": {                               // Configure if testing email channel
      "company_email": "replies@cucumber-recruitment.com",
      "email_credentials_id": "email-credentials/cucumber-recruitment/cv-analysis/sendgrid" // Reference to Email credentials secret
    },
    "sms": {                                 // Configure if testing SMS channel
        "company_sms_number": "+447700900444", // Example SMS number. **Must include international prefix (+44).**
        "sms_credentials_id": "sms-credentials/cucumber-recruitment/cv-analysis/twilio" // Reference to SMS credentials secret
      }
  },
  "created_at": "2023-10-27T10:00:00Z",     // Set current timestamp on creation
  "updated_at": "2023-10-27T10:00:00Z"      // Set current timestamp on creation/update
}
```

**Key Points:**

-   Use unique but identifiable `company_id` and `project_id` for dev testing (e.g., `ci-test-001`, `pi-test-whatsapp-001`).
-   The `api_key_reference` **must** be updated with the **API Key ID** (not the key value itself) created in API Gateway (see Section 6). This is crucial for operational reference and correlating logs/metrics.
-   **`project_status` (String): Must be set to `"active"`** in the DynamoDB item for the project to accept requests. This allows disabling projects without deleting records.
-   **`allowed_channels` (List of Strings): Define which channels this project can use** (e.g., `["whatsapp", "email"]`). The order doesn't matter. Supported values are `"whatsapp"`, `"email"`, `"sms"`. The Channel Router will reject requests for channels not listed here.
-   Configure the relevant sections within `channel_config` based on the channels being enabled and tested.
-   Configure the `ai_config.openai_config.<channel>` section for each enabled channel, providing the correct channel-specific `api_key_reference` and any required `assistant_id_*` values.
-   Ensure phone numbers (`company_whatsapp_number`, `company_sms_number`) are stored with the international prefix (e.g., `+44`, `+1`).

## 6. API Gateway Configuration (`ai-multi-comms-dev-api`)

Authentication for the development API (`ai-multi-comms-dev-api`) is handled directly by API Gateway using API Keys and Usage Plans. The API key is **NOT** sent in the request payload to the Lambda; it **must** be sent in the `x-api-key` HTTP header.

### 6.1 Setting Up API Authentication (Console/CLI)

1.  **Navigate to API Gateway:** Go to the `ai-multi-comms-dev-api` API in the AWS Console.
2.  **Create API Key:**
    *   Go to "API Keys".
    *   Create a new key (e.g., `ci-aaa-001-pi-aaa-001-key`). Use Auto Generate or create a custom key.
    *   **IMPORTANT:** Note down the **API Key ID** (e.g., `a1b2c3d4e5`). This ID **must** be put into the `api_key_reference` field in the corresponding DynamoDB item (Section 5.1).
    *   Note down the **API Key value** itself securely – this is what the client/test script will use in the `x-api-key` header.
3.  **Create/Verify Usage Plan:**
    *   Go to "Usage Plans".
    *   Use the existing `dev-usage-plan` or create a new one if specific limits are needed for this test.
    *   Ensure the plan has appropriate throttling limits set (e.g., Rate, Burst).
4.  **Associate Key with Plan:**
    *   In the Usage Plan settings, go to "API Keys".
    *   Add the newly created API Key to this usage plan.
5.  **Associate Plan with API Stage:**
    *   In the Usage Plan settings, go to "API Stages".
    *   Ensure the plan is associated with the `dev` stage of the `ai-multi-comms-dev-api`.
6.  **Configure Method for API Key Requirement:**
    *   Go to the API's "Resources".
    *   Select the `POST` method under the `/initiate-conversation` resource.
    *   Click on "Method Request".
    *   Ensure "API Key Required" is set to `true`.

The setup team provides the **API Key value** (not the ID) to the developer/tester who needs to call the API.

## 7. (Optional) Secrets Manager Configuration (Development Context)

If testing components that require external credentials (e.g., Twilio, OpenAI, Email provider):

1.  **Define References in DynamoDB:** Ensure the correct secret reference paths are defined in the `company-data-dev` record (as shown in Section 5.1). These paths follow the conventions:
    *   Channels Provider Credentials: `{credential_type}/{company_name}/{project_name}/{provider}` (e.g., `whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio`)
    *   Channel AI Key: `openai-api-key/<channel>` (e.g., `openai-api-key/whatsapp`)
    *   The fields in DynamoDB should use the `_id` suffix for channel provider credentials (e.g., `whatsapp_credentials_id`) and be placed under `channel_config.<channel>`.
    *   The AI key reference should use the `api_key_reference` key and be placed under `ai_config.openai_config.<channel>`.

2.  **Create/Update Secrets in Secrets Manager:**
    *   **This is a mandatory step if the project uses external services requiring authentication.** The administrator/setup team must ensure that secrets corresponding exactly to the paths defined in the DynamoDB record exist in AWS Secrets Manager.
    *   Use the AWS CLI (`aws secretsmanager create-secret` or `aws secretsmanager update-secret`) or the AWS Console.
    *   Populate these secrets with the correct JSON structure and either the actual development/test credentials or clearly defined placeholder values.
    *   If using placeholders initially, ensure a process exists to update them with real credentials before full testing.
    *   Refer to `src_dev/docs & setup/lld/aws-secrets-manager-dev.md` for the required JSON structure within each secret type.

3.  **Configure IAM Permissions:** Ensure the IAM roles for the *downstream* Lambda functions (e.g., `ai-multi-comms-whatsapp-channel-processor-dev-role`) have `secretsmanager:GetSecretValue` permission scoped correctly to the required secret paths (as detailed in `src_dev/docs & setup/lld/iam-role-whatsapp-channel-processor-dev.md`). The Channel Router Lambda itself usually doesn't need direct access to these external credentials.

## 8. (Optional) AI Assistant Configuration (Development Context)

If testing AI variable mapping or template sending:

-   Create a test assistant in OpenAI if needed (using the appropriate channel API key).
-   Configure basic system instructions relevant to the test data and template.
-   Note the Assistant ID and add it to the relevant `assistant_id_*` field(s) in the `ai_config.openai_config.<channel>` section of the DynamoDB record for the specific channel.

## 9. Frontend Development/Testing (Development Context)

When developing a frontend or test script to call the `dev` API endpoint:

-   **API Endpoint:** Use the invoke URL for the `dev` stage of `ai-multi-comms-dev-api`.
-   **Authentication:** The request **must** include the correct **API Key value** (obtained during setup in Section 6) in the `x-api-key` HTTP header.
-   **Request Payload:** See Section 9.1 below for a detailed structure summary.
-   **Test Scripts:** `curl` or tools like Postman/Insomnia can be used for testing. Ensure the `x-api-key` header and `Content-Type: application/json` header are correctly set.

### 9.1 Payload Structure Summary

The JSON payload sent in the request body **must** contain the following top-level objects:

-   `company_data` (Object): Contains identifiers for the company/project.
    -   **Required Fields:**
        -   `company_id` (String): Matches the `company_id` in the DynamoDB record.
        -   `project_id` (String): Matches the `project_id` in the DynamoDB record.
    -   **Do NOT include `api_key` here.**
-   `recipient_data` (Object): Contains information about the communication recipient.
    -   **Required Fields (Conditional):**
        -   `recipient_tel` (String): Required and non-empty if `channel_method` is `whatsapp` or `sms`.
        -   `recipient_email` (String): Required and non-empty if `channel_method` is `email`.
    -   **Required Fields (Always):**
        -   `comms_consent` (Boolean): Must be `true` or `false`, indicating user consent.
    -   Other fields like `recipient_first_name`, `recipient_last_name` can be included as needed by the use case.
-   `request_data` (Object): Contains metadata about the request.
    -   **Required Fields:**
        -   `request_id` (String): Must be a valid UUID v4 string (e.g., generated by the client).
        -   `channel_method` (String): Must be one of the supported channels (`whatsapp`, `email`, `sms`) and must be listed in the `allowed_channels` for the project in DynamoDB.
        -   `initial_request_timestamp` (String): Must be a valid ISO 8601 timestamp string (e.g., `YYYY-MM-DDTHH:MM:SSZ`).

The payload **may optionally** contain the following top-level object:

-   `project_data` (Object): Contains arbitrary key-value pairs specific to the use case (e.g., data for populating templates, guiding AI). This object can be omitted entirely if not needed.

### 9.2 Example Payload (`curl`)

```bash
# Replace YOUR_API_GATEWAY_DEV_INVOKE_URL and YOUR_API_KEY_VALUE_HERE
curl -X POST \
  'YOUR_API_GATEWAY_DEV_INVOKE_URL/initiate-conversation' \
  --header 'Content-Type: application/json' \
  --header 'x-api-key: YOUR_API_KEY_VALUE_HERE' \
  --data-raw '{
    "company_data": {
      "company_id": "ci-aaa-001",
      "project_id": "pi-aaa-001"
    },
    "recipient_data": {
      "recipient_tel": "+447588713814",
      "recipient_first_name": "John",
      "recipient_last_name": "Smith",
      "comms_consent": true
    },
    "request_data": {
      "request_id": "$(uuidgen)", 
      "channel_method": "whatsapp",
      "initial_request_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    },
    "project_data": {
       "jobID": "9999",
       "jobRole": "Healthcare Assistant",
       "clarificationPoints": [
         {"point": "CV needs driving licence clarification.", "pointConfirmed": "false"}
       ]
    }
  }'
```
*Note: `$(uuidgen)` and `$(date ...)` are shell commands to generate values dynamically in Linux/macOS.* 

## 10. Testing & Deployment (Development Context)

-   **Unit Testing:** Test individual Lambda modules where feasible.
-   **Integration Testing:** Send test requests via `curl`, Postman, Insomnia, or a test frontend.
    -   Verify API Gateway returns success (200 OK) or appropriate errors (400, 401, 403, 429).
    -   Check CloudWatch Logs for the Channel Router Lambda (`channel-router-dev`) to confirm successful processing or identify errors.
    -   Check the target SQS queue (e.g., `ai-multi-comms-whatsapp-queue-dev`) to ensure messages arrive with the correct context object.
    -   (If testing further) Check downstream Lambda logs (e.g., `whatsapp-sender-dev`) and final message delivery.

## 11. Monitoring & Operations (Development Context)

-   Primary monitoring in `dev` is via **CloudWatch Logs** for the API Gateway and Lambda functions.
-   Check logs for successful execution, warnings (e.g., missing env vars), and errors.
-   Review SQS queue metrics (e.g., `ApproximateNumberOfMessagesVisible`) in the AWS console to verify message queuing.

## 12. Documentation & Handover (Development Context)

-   Ensure the test **API Key value** is securely provided to the developer/tester.
-   Confirm the `company_id` and `project_id` used in the setup.
-   Provide the API Gateway invoke URL for the `dev` stage. 