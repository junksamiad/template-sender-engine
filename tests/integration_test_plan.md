# AI Multi-Comms Engine - Integration Test Plan

## 1. Introduction

This document outlines the integration testing strategy for the AI Multi-Comms Engine. Integration tests verify the interactions *between* different components of the system, including interactions with live or simulated AWS services. They focus on the communication paths, data contracts, and permissions between services.

**Goal:** Ensure components work together correctly and interact properly with AWS infrastructure.
**Tools:** `pytest`, `boto3`, AWS CLI, `curl`, potentially `localstack` or AWS SAM CLI (`sam local start-api`, `sam local invoke`).

## 2. Scope & Test Cases

**Note:** These tests typically require deployed AWS resources or reliable local simulations.

### 2.1. API Gateway <-> Channel Router Lambda

*   [ ] **Authentication:**
    *   [ ] Send request with valid API key, expect 2xx response (or eventual SQS message).
    *   [ ] Send request with invalid/missing API key, expect 403 Forbidden.
*   [ ] **Routing:**
    *   [ ] Send POST request to `/initiate-conversation`, expect it to trigger the Channel Router Lambda.
    *   [ ] Send request to an undefined path, expect 403 Missing Authentication Token / 404 Not Found.
    *   [ ] Send request with an incorrect method (e.g., GET), expect 403 Missing Authentication Token / 405 Method Not Allowed.
*   [ ] **CORS:**
    *   [ ] Send OPTIONS preflight request, verify correct CORS headers (`Access-Control-Allow-Origin`, etc.) are returned.
*   [ ] **Payload Forwarding:**
    *   [ ] Verify the full request body sent to API Gateway arrives correctly in the Lambda event object (`event['body']`).

### 2.2. Channel Router Lambda <-> DynamoDB (`company-data-dev`)

*   [ ] **Successful Fetch:**
    *   [ ] Trigger Lambda with input referencing a valid `company_id`/`project_id` existing in the table. Verify Lambda executes successfully (check logs, SQS message).
*   [ ] **Item Not Found:**
    *   [ ] Trigger Lambda with input referencing a non-existent `company_id`/`project_id`. Verify Lambda returns an appropriate error response (e.g., 404 Not Found or 400 Bad Request) and logs the failure.
*   [ ] **Configuration Logic:**
    *   [ ] Test with a config item where `project_status` is inactive. Verify error response.
    *   [ ] Test with a config item where the requested `channel_method` is not in `allowed_channels`. Verify error response.
*   [ ] **IAM Permissions:**
    *   [ ] Verify the Lambda's execution role (`ai-multi-comms-channel-router-dev-role`) has `dynamodb:GetItem` permission on the table. Temporarily remove permission and verify failure. (Use with caution).

### 2.3. Channel Router Lambda <-> SQS (`ai-multi-comms-whatsapp-queue-dev`)

*   [ ] **Successful Send:**
    *   [ ] Trigger Lambda with valid input. Verify a message appears in the target SQS queue.
    *   [ ] Verify the message body contains the correctly structured and serialized Context Object.
    *   [ ] Verify the message attributes (`company_id`, `project_id`, etc.) are present and correct.
*   [ ] **IAM Permissions:**
    *   [ ] Verify the Lambda's execution role has `sqs:SendMessage` permission on the queue. Temporarily remove permission and verify failure. (Use with caution).
*   [ ] **Queue Configuration:**
    *   [ ] Send message to a non-existent queue URL (by misconfiguring env var). Verify Lambda fails gracefully.

### 2.4. SQS <-> WhatsApp Channel Processor Lambda

*   [ ] **Trigger Configuration:**
    *   [ ] Manually send a valid test message (Context Object) to `ai-multi-comms-whatsapp-queue-dev`. Verify the `whatsapp-channel-processor-dev` Lambda is triggered.
    *   [ ] Verify the Lambda receives the message content correctly within the SQS event structure.
*   [ ] **Batch Size:**
    *   [ ] Confirm Event Source Mapping is configured with batch size 1.
*   [ ] **IAM Permissions (Receive/Delete):**
    *   [ ] Verify the Lambda's execution role (`ai-multi-comms-whatsapp-channel-processor-dev-role`) has `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes` permissions. Temporarily remove and verify failure/message retries. (Use with caution).

### 2.5. WhatsApp Processor Lambda <-> DynamoDB (`conversations-dev`)

*   [ ] **Initial Record Creation:**
    *   [ ] Trigger Lambda with a new `conversation_id`. Verify a record is created in `conversations-dev` with the correct initial state (`processing`, etc.).
*   [ ] **Idempotency:**
    *   [ ] Trigger Lambda with the *same* `conversation_id` again. Verify no new record is created and the Lambda potentially logs/handles the condition check failure gracefully (doesn't fail outright).
*   [ ] **Final Record Update:**
    *   [ ] Allow Lambda to process successfully (mock external calls if needed). Verify the corresponding record in `conversations-dev` is updated with the final status (`initial_message_sent`), timestamps, thread ID, message history, etc.
*   [ ] **IAM Permissions:**
    *   [ ] Verify the Lambda's execution role has `dynamodb:PutItem`, `dynamodb:UpdateItem` permissions. Temporarily remove and verify failure. (Use with caution).

### 2.6. WhatsApp Processor Lambda <-> Secrets Manager

*   [ ] **Successful Fetch:**
    *   [ ] Trigger Lambda ensuring it needs to fetch OpenAI and Twilio secrets. Verify successful retrieval (check logs). Ensure secrets have placeholder/test values.
*   [ ] **Secret Not Found:**
    *   [ ] Configure the Context Object/DynamoDB config to reference a non-existent secret name. Verify the Lambda fails gracefully and logs the error.
*   [ ] **IAM Permissions:**
    *   [ ] Verify the Lambda's execution role has `secretsmanager:GetSecretValue` permission on the specific secret ARNs/patterns. Temporarily revoke and verify failure. (Use with caution).

### 2.7. WhatsApp Processor Lambda (Heartbeat) <-> SQS

*   [ ] **Visibility Timeout Extension:**
    *   [ ] Trigger Lambda with a message. Add a significant `time.sleep()` *before* the heartbeat is stopped. Monitor the message in the SQS console/API. Verify its visibility timeout is extended by the heartbeat mechanism before the original timeout expires.
*   [ ] **IAM Permissions:**
    *   [ ] Verify the Lambda's execution role has `sqs:ChangeMessageVisibility` permission. Temporarily revoke and verify heartbeat failure (check logs). (Use with caution).

## 3. Execution & Environment

*   Integration tests may require deploying stacks to a dedicated testing environment in AWS.
*   Alternatively, tools like `localstack` or AWS SAM CLI can simulate AWS services locally, reducing cost and setup time, but may have fidelity limitations.
*   Tests should manage their own test data setup and teardown where possible.
*   Secrets used during testing should contain placeholder or non-production values. 