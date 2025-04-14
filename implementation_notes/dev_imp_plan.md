# Development Implementation Roadmap
This document outlines the key steps for implementing the `src_dev` environment.

## Part 1: CHANNEL ROUTER

### Phase 1: Infrastructure Setup (AWS CLI/Console)

1.  **API Gateway Setup & Key Validation**
    *   **Status:** Done. ✅
    *   **Details:** Configure API Gateway (`ai-multi-comms-dev-api`) for API Key validation using Usage Plans (`dev-usage-plan`). Frontend applications must send the API key in the `x-api-key` header.
    *   **Reference:** `src_dev/docs & setup/lld/api_gateway.md`

2.  **Create Company Config DynamoDB Table (`company-data-dev`)**
    *   **Status:** Done. ✅
    *   **Details:** Define the table schema based on `src_dev/docs & setup/lld/company-data-db-dev.md`, ensuring `company_id` (Partition Key) and `project_id` (Sort Key). Use On-Demand capacity mode. Add test data.
    *   **Reference:** `src_dev/docs & setup/lld/company-data-db-dev.md`

3.  **Create SQS Queues & DLQs**
    *   **Status:** Done. ✅
    *   **Details:** Create Standard SQS queues for `whatsapp` channel (`ai-multi-comms-whatsapp-queue-dev`) and corresponding DLQ (`ai-multi-comms-whatsapp-dlq-dev`). Configure according to LLD (Visibility Timeout: 600s, Max Receive Count: 3, DLQ Retention: 14 days). Email/SMS queues deferred.
    *   **Reference:** `src_dev/docs & setup/lld/whatsapp-sqs-dlq-dev.md`

4.  **Define IAM Role (Channel Router Lambda)**
    *   **Status:** Done. ✅
    *   **Details:** Create `ai-multi-comms-channel-router-dev-role`. Grant permissions: `dynamodb:GetItem` on `company-data-dev`, `sqs:SendMessage` to `ai-multi-comms-whatsapp-queue-dev`, `AWSLambdaBasicExecutionRole`.

### Phase 2: Lambda Development (`src_dev/channel_router`)

5.  **Create Channel Router Lambda (Basic Structure)**
    *   **Status:** Done. ✅
    *   **Location:** `src_dev/channel-router/lambda/`
    *   **Details:** Created `channel-router-dev` function, handler `index.py`. IAM role assigned.

6.  **Implement Lambda Logic**
    *   **Status:** Done. ✅
    *   **Details:** Implemented request parsing, validation, config fetching, context building (`context_builder.py`), SQS sending (`sqs_service.py`), and response formatting (`response_builder.py`).

### Phase 3: Integration & Testing (Channel Router)

7.  **Update API Gateway (Switch to Lambda Integration)**
    *   **Status:** Done. ✅
    *   **Details:** Updated `/initiate-conversation` POST method to `AWS_PROXY` integration pointing to `channel-router-dev` Lambda.

8.  **End-to-End Testing (Channel Router)**
    *   **Status:** Partially Done (Initial Success Verified). ✅
    *   **Details:** Send test payloads via `curl`.
    *   **Verify:**
        *   [x] Correct HTTP responses (200 OK).
        *   [x] API key validation.
        *   [ ] Payload validation (needs more cases).
        *   [x] Message appears in SQS queue.
        *   [x] Message body contains correct Context Object.
        *   [x] CloudWatch Logs checked.

## Part 2: CHANNEL PROCESSOR

### Phase 4: Infrastructure & Configuration Setup (Channel Processor)

9.  **Define & Create Conversation DynamoDB Table (`conversations-dev`)**
    *   **Status:** Done ✅
    *   **Details:** Defined the schema (PK: `primary_channel`, SK: `conversation_id`), created the `conversations-dev` table via AWS CLI. Includes GSI (`company-id-project-id-index`) and 4 LSIs (`created-at-index`, `task-complete-index`, `conversation-status-index`, `channel-method-index`). Uses On-Demand capacity.
    *   **Reference:** `src_dev/docs & setup/lld/conversations-dev.md`, `lld/db/conversations-db-schema-v1.0.md`, `lld/processing-engines/whatsapp/03-conversation-management.md`

10. **Define IAM Role (WhatsApp Channel Processor Lambda)**
    *   **Status:** Done ✅
    *   **Details:** Created the IAM role `ai-multi-comms-whatsapp-channel-processor-dev-role` with a custom policy named `ai-multi-comms-whatsapp-channel-processor-dev-policy`. Grant necessary permissions:
        *   `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes`, `sqs:ChangeMessageVisibility` **specifically** on `ai-multi-comms-whatsapp-queue-dev`.
        *   `dynamodb:PutItem`, `dynamodb:GetItem`, `dynamodb:UpdateItem`, `dynamodb:Query` on the `conversations-dev` table and its indexes (`table/conversations-dev/index/*`).
    *   **Note:** SQS Heartbeat is implemented in code; the `sqs:ChangeMessageVisibility` permission enables it. Similar roles/policies will be needed for Email/SMS processors later.
    *   **Reference:** `src_dev/docs & setup/lld/iam-role-whatsapp-channel-processor-dev.md`

11. **Setup AWS Secrets Manager**
    *   **Status:** Done ✅
    *   **Details:** Created placeholder secrets in AWS Secrets Manager (`eu-north-1`) for dev environment using name convention `{credential_type}/{company_name}/{project_name}/{provider}` for channels (Twilio WhatsApp/SMS, SendGrid Email) and `ai-api-key/global` for OpenAI. Actual credentials to be updated later. Updated WhatsApp Processor IAM policy (`v2`) to grant specific access to `whatsapp-credentials/*/*/twilio-*` and `ai-api-key/global-*`.
    *   **Reference:** `src_dev/docs & setup/lld/aws-secrets-manager-dev.md`

12. **Configure OpenAI Platform**
    *   **Status:** Done ✅
    *   **Details:** Set up the necessary components on the OpenAI platform:
        *   Manually created required OpenAI Assistants via OpenAI Platform dashboard.
        *   Manually updated `company-data-dev` DynamoDB table with Assistant IDs for test company.
        *   Manually stored actual channel-specific API Keys in AWS Secrets Manager (`openai-api-key/whatsapp`, etc.) via console.
        *   Defined and configured the Assistant's instructions/prompts (as part of manual creation).
        *   Defined any required function calling schemas or structured output requirements (as part of manual creation).
    *   **Action:** Completed manually for dev setup. Script `create_openai_assistant.py` available for future use/automation.

13. **Configure Twilio Platform**
    *   **Status:** Done ✅
    *   **Details:** Configure the Twilio account for WhatsApp communication:
        *   Manually retrieved Twilio Account SID and Auth Token.
        *   Manually provisioned/configured the WhatsApp Sender phone number.
        *   Manually created and approved necessary WhatsApp message templates for testing.
    *   **Action:** Stored Account SID and Auth Token in Secrets Manager (under relevant `whatsapp-credentials/...` secret name). Recorded the sender number in the `company-data-dev` table (`channel_config.whatsapp.company_whatsapp_number`).

### Phase 5: Lambda Development (`src_dev/channel-processor/whatsapp`)

14. **Create WhatsApp Channel Processor Lambda (Basic Structure)**
    *   **Status:** Done ✅
    *   **Location:** `src_dev/channel-processor/whatsapp/lambda/`
    *   **Details:** Develop the initial Lambda function code (`index.py`) for the **WhatsApp processor** (`whatsapp-channel-processor-dev`). Include basic handler, required imports, environment variable handling, and AWS client initializations.
    *   **Planned Structure:**
        ```
        src_dev/channel-processor/
        ├── whatsapp/
        │   └── lambda/
        │       ├── index.py
        │       ├── core/
        │       ├── services/
        │       ├── utils/
        │       └── requirements.txt
        ├── email/
        │   └── lambda/  # For future Email Processor
        └── sms/
            └── lambda/    # For future SMS Processor
        ```

15. **Implement Core WhatsApp Lambda Logic**
    *   **Status:** Done ✅
    *   **Details:** Build out the **WhatsApp** Channel Processor Lambda function logic step-by-step:
        *   [x] Parse incoming SQS message body (containing the Context Object). (`index.py`)
        *   [x] Deserialize and validate the Context Object structure. (`utils/context_utils.py`, used in `index.py`)
        *   [x] Implement SQS Heartbeat mechanism (`SQSHeartbeat` class or similar) to manage visibility timeout for long tasks. (`utils/sqs_heartbeat.py`, integrated in `index.py`)
        *   [x] Implement logic to create/update conversation records in the `conversations-dev` DynamoDB table (idempotency checks needed). (`services/dynamodb_service.py`, integrated in `index.py`)
        *   [x] Implement credential fetching from AWS Secrets Manager for Twilio and OpenAI. (`services/secrets_manager_service.py`, integrated in `index.py`)
        *   [x] Implement interaction with OpenAI API (e.g., create/retrieve thread, add message, run assistant, handle responses, structured outputs). (`services/openai_service.py`, integrated in `index.py`)
        *   [x] Implement interaction with Twilio API (send authorised template initial WhatsApp message using fetched credentials). (`services/twilio_service.py`, integrated in `index.py`)
        *   [x] Update the `conversations-dev` record with status, message history, thread ID, processing time, etc. (`services/dynamodb_service.py`, integrated in `index.py`)
        *   [x] Implement robust error handling, logging, and potential retry logic for external API calls and DB operations (Initial version: relies on SQS retries/DLQ, broad exception handling, logging).

16. **Package WhatsApp Lambda for Deployment**
    *   **Status:** Done ✅
    *   **Details:** Create deployment package (`.zip` file) containing the Lambda code (`index.py` and all supporting modules in `core/`, `services/`, `utils/`) and its dependencies (from `requirements.txt`). Ensure the structure is correct for Lambda deployment (e.g., `index.py` at the root of the zip).

17. **Deploy WhatsApp Lambda & Configure SQS Trigger**
    *   **Status:** Done ✅
    *   **Details:**
        *   Deploy the packaged `whatsapp-channel-processor-dev` Lambda function to AWS using the AWS CLI (`aws lambda create-function` or `aws lambda update-function-code`). Configure necessary environment variables (e.g., `CONVERSATIONS_TABLE`, `WHATSAPP_QUEUE_URL`, `SECRETS_MANAGER_REGION`, `LOG_LEVEL`, `VERSION`, `SQS_HEARTBEAT_INTERVAL_MS`). Assign the `ai-multi-comms-whatsapp-channel-processor-dev-role`.
        *   Create the Event Source Mapping using the AWS CLI (`aws lambda create-event-source-mapping`) to link the `ai-multi-comms-whatsapp-queue-dev` SQS queue to the newly deployed `whatsapp-channel-processor-dev` Lambda function. Set the batch size to 1.

18. **Configure CloudWatch Monitoring for Critical Errors**
    *   **Status:** Done ✅
    *   **Details:** Set up monitoring to alert on critical failures, specifically the final DynamoDB update failure after message send:
        *   Identify the exact CloudWatch Log Group name for the `whatsapp-channel-processor-dev` function.
        *   Create an SNS Topic (e.g., `ai-comms-critical-alerts`) for alarm notifications.
        *   Subscribe necessary endpoints (e.g., email) to the SNS Topic.
        *   Create a CloudWatch Logs Metric Filter to match the "final DynamoDB update failed" critical log message.
        *   Configure the Metric Filter to publish to a custom CloudWatch Metric (e.g., `AIComms/WhatsAppProcessor/FinalDbUpdateFailureCount`).
        *   Create a CloudWatch Alarm that monitors the custom metric (e.g., triggers if count >= 1 in 5 minutes).
        *   Configure the Alarm to send notifications to the created SNS Topic.

18.1. **Troubleshoot Lambda Import Error Locally (Using AWS SAM CLI)**
    *   **Status:** Done ✅
    *   **Issue:** Despite multiple attempts to package and deploy the `whatsapp-channel-processor-dev` Lambda using the AWS CLI (including recreating the function and trigger), it consistently fails on invocation with `Runtime.ImportModuleError: Unable to import module 'index': attempted relative import with no known parent package`. This occurred even after ensuring `__init__.py` files exist and verifying the zip structure with `unzip -l` appeared correct on the final attempt.
    *   **Reason for Detour:** The standard remote debugging steps (checking logs, deployment status, package structure) have failed to resolve the issue. This suggests a more subtle packaging problem possibly related to the local environment or zip creation, or an issue best diagnosed with direct code execution visibility.
    *   **Goal:** Use AWS SAM CLI locally to definitively identify and fix the root cause of the import error before attempting AWS deployment again.
    *   **Method:**
        *   [x] Ensure Docker is running locally (required by `sam local invoke`).
        *   [x] Create a `template.yaml` file in the project root to define the `whatsapp-channel-processor-dev` function resource locally.
        *   [x] Use `sam build` to package the Lambda function and its dependencies into the `.aws-sam` directory.
        *   [x] Create a sample SQS event payload (e.g., `events/sqs_event.json`) mimicking the message sent by the Channel Router.
        *   [x] Use `sam local invoke whatsappChannelProcessorFunctionDev -e events/sqs_event.json` to run the function locally within the simulated environment.
        *   [x] Analyze the output/logs from `sam local invoke` to identify the exact point of failure in the import process.
        *   [x] If necessary, add debug print statements to `index.py` and relevant `utils/`, `services/` files and repeat the `sam build` / `sam local invoke` cycle until the error is understood and resolved in the local code.
    *   **Constraint:** Once the import error is fixed locally, the solution will be applied, and the function will be **re-packaged and deployed using the established AWS CLI commands** (`zip`, `aws lambda update-function-code`). **`sam deploy` will NOT be used.**

### Phase 6: Integration & Testing (Channel Processor)

19. **End-to-End Testing (WhatsApp Flow)**
    *   **Status:** To Do
    *   **Details:** Conduct comprehensive end-to-end testing for the full WhatsApp flow:
        *   [ ] Send a request via `curl` to the API Gateway `/initiate-conversation` endpoint.
        *   [ ] Verify the message appears in the `ai-multi-comms-whatsapp-queue-dev` SQS queue.
        *   [ ] Verify the `whatsapp-channel-processor-dev` Lambda is triggered.
        *   [ ] Verify the Lambda successfully processes the message (check CloudWatch Logs).
        *   [ ] Verify a new record is created (or handled idempotently) in the `conversations-dev` DynamoDB table with status `processing` initially.
        *   [ ] Verify credentials are fetched from Secrets Manager (check logs, potentially mock locally).
        *   [ ] Verify interaction with OpenAI (check logs, potentially mock locally, check OpenAI platform if feasible).
        *   [ ] Verify interaction with Twilio (check logs, potentially mock locally, **check if the actual WhatsApp message is received on the target phone number**).
        *   [ ] Verify the `conversations-dev` record is updated with status `initial_message_sent` (or `failed`), message history, thread ID, etc.
        *   [ ] Verify the message is deleted from the SQS queue upon successful processing.
        *   [ ] Test failure scenarios (e.g., invalid context, API failures, permission errors) and verify messages land in the DLQ (`ai-multi-comms-whatsapp-dlq-dev`). 