# AI Multi-Comms Engine - End-to-End (E2E) Test Plan

## 1. Introduction

This document outlines the end-to-end (E2E) testing strategy for the AI Multi-Comms Engine. E2E tests verify the complete application flow from the perspective of an external client, interacting with the fully deployed system on AWS. These tests simulate real user scenarios.

**Goal:** Validate the entire system functionality, data flow, and integration of all components, including external services (OpenAI, Twilio), in a production-like environment.
**Tools:** `curl`, Scripting languages (`Python` with `requests`, `boto3`), Test automation frameworks, AWS Console/CLI (for verification).

## 2. Prerequisites

*   The entire application (API Gateway, Lambdas, DynamoDB tables, SQS queues, Secrets Manager secrets, IAM roles, etc.) must be deployed to the target AWS environment (e.g., `dev`).
*   Valid API Key associated with a Usage Plan for the deployed API Gateway stage.
*   Test data configured in `company-data-dev` DynamoDB table for various scenarios.
*   Valid (potentially test-specific) credentials stored in Secrets Manager for OpenAI and Twilio.
*   Configured OpenAI Assistant(s) on the OpenAI platform.
*   Configured and approved Twilio WhatsApp sender and template(s).
*   A target phone number accessible for receiving test WhatsApp messages.
*   Access to CloudWatch Logs for verification.
*   Access to SQS queues (including DLQs) for verification.
*   Access to DynamoDB tables for verification.

## 3. Scope & Test Cases

**Note:** These tests interact with live external services and may incur costs.

### 3.1. Happy Path Scenarios

*   [ ] **Basic WhatsApp Success:**
    *   Send a valid POST request to `/initiate-conversation` using `curl` with a valid API key and payload targeting the WhatsApp channel for a configured company/project.
    *   **Verify:**
        *   [ ] API Gateway returns 200 OK.
        *   [ ] Message appears briefly in `ai-multi-comms-whatsapp-queue-dev`.
        *   [ ] `whatsapp-channel-processor-dev` Lambda logs show successful execution (parsing, DB create, secrets fetch, AI call, Twilio call, DB update).
        *   [ ] Record created in `conversations-dev` initially, then updated to `initial_message_sent`.
        *   [ ] **Actual WhatsApp message received on the target phone number with expected content.**
        *   [ ] Message is deleted from the SQS queue.
*   [ ] **Variations:**
    *   [ ] Test with different valid company/project configurations.
    *   [ ] Test with different valid recipient phone numbers.
    *   [ ] Test with payloads containing maximum allowed field lengths (if defined).

### 3.2. API Gateway Error Handling

*   [ ] **Invalid API Key:** Send request with an incorrect/missing `x-api-key` header. Verify 403 Forbidden response.
*   [ ] **Invalid Path:** Send request to a non-existent path (e.g., `/initiate`). Verify 403/404 response.
*   [ ] **Invalid Method:** Send GET request to `/initiate-conversation`. Verify 403/405 response.
*   [ ] **Malformed Payload:** Send request with invalid JSON in the body. Verify 400 Bad Request (or similar error from API Gateway/Lambda integration).

### 3.3. Channel Router Logic Errors

*   [ ] **Payload Validation Failure:** Send request with missing required fields in the JSON body. Verify 400 Bad Request response from Channel Router Lambda.
*   [ ] **Company/Project Not Found:** Send request referencing `company_id`/`project_id` not present in `company-data-dev`. Verify 404 Not Found (or similar) response.
*   [ ] **Project Inactive:** Send request for a project marked as inactive in `company-data-dev`. Verify appropriate error response (e.g., 400 Bad Request).
*   [ ] **Channel Not Allowed:** Send request for a channel (e.g., `email`) not listed in `allowed_channels` for the project in `company-data-dev`. Verify appropriate error response.
*   **Verify:** In all Channel Router error scenarios, ensure *no message* is sent to any SQS queue.

### 3.4. WhatsApp Channel Processor Error Handling & Edge Cases

*   [ ] **Invalid Context Object (Simulated):** Manually send a malformed Context Object message to `ai-multi-comms-whatsapp-queue-dev`. Verify Lambda fails, logs the error, and the message eventually goes to the DLQ after retries.
*   [ ] **Secrets Manager Failure:**
    *   [ ] Temporarily misconfigure the secret reference in `company-data-dev` to point to a non-existent secret. Trigger the flow. Verify Lambda fails during secret fetching, logs the error, and the message goes to the DLQ.
    *   [ ] Temporarily store invalid credentials (e.g., incorrect format) in a secret. Trigger the flow. Verify subsequent service calls (OpenAI/Twilio) fail. (Restore afterwards!).
*   [ ] **OpenAI Failure:**
    *   [ ] Temporarily use an invalid OpenAI API key in Secrets Manager. Trigger the flow. Verify Lambda fails during AI processing, logs the error, and message goes to DLQ.
    *   [ ] (Difficult to force) Attempt to trigger OpenAI rate limits or timeouts if possible. Verify Lambda handles this (e.g., logs timeout, message goes to DLQ).
*   [ ] **Twilio Failure:**
    *   [ ] Temporarily use invalid Twilio credentials in Secrets Manager. Trigger the flow. Verify Lambda fails during Twilio send, logs the error, message goes to DLQ.
    *   [ ] Send request with an invalidly formatted recipient phone number. Verify Twilio send fails, error logged, message to DLQ.
    *   [ ] Send request referencing a non-approved/non-existent Twilio template SID. Verify Twilio send fails, error logged, message to DLQ.
*   [ ] **Final DynamoDB Update Failure (Critical Alert Test):**
    *   [ ] (Difficult to force reliably) If possible, temporarily revoke `dynamodb:UpdateItem` permission *after* the Twilio call succeeds but *before* the final update. Trigger the flow. **Verify:**
        *   [ ] WhatsApp message *is* sent.
        *   [ ] Lambda logs the critical failure for the final DB update.
        *   [ ] Message goes to DLQ (or is potentially lost if error handling prevents SQS deletion).
        *   [ ] **CloudWatch Alarm (`AIComms/WhatsAppProcessor/FinalDbUpdateFailureCount`) enters ALARM state.**
        *   [ ] **SNS notification is received.** (Restore permissions afterwards!).

### 3.5. Idempotency Test

*   [ ] Send the *exact same valid request* (same payload, headers) twice in quick succession.
*   **Verify:**
    *   [ ] Only *one* WhatsApp message is received by the target phone number.
    *   [ ] Only *one* conversation record exists/is updated in `conversations-dev` for that `conversation_id`.
    *   [ ] Check CloudWatch logs for potential signs of the second invocation handling the idempotency check (e.g., logging a conditional check failure before exiting gracefully).

### 3.6. DLQ Verification

*   [ ] After executing tests designed to cause persistent processing failures (e.g., invalid secret reference, bad payload schema causing repeated Lambda errors), verify that the failed messages appear in the `ai-multi-comms-whatsapp-dlq-dev` queue.

### 3.7. SQS Heartbeat Verification (Long Processing Simulation)

*   [ ] (Difficult in pure E2E) If feasible, configure an OpenAI Assistant or scenario known to take a longer time (approaching the Lambda timeout / SQS visibility timeout). Trigger the flow.
*   **Verify:** The message is processed successfully without being re-processed due to visibility timeout expiry, indicating the heartbeat worked. (Monitor logs for signs of multiple invocations for the same message ID if heartbeat failed).

## 4. Execution & Reporting

*   E2E tests should be run against a deployed, stable environment.
*   Maintain a clear record of test case execution (pass/fail) and any observed issues.
*   Automate E2E tests where possible using scripting, but some manual verification (like checking the received WhatsApp message) may be necessary.
*   Clean up test data (e.g., conversation records) after test runs if necessary. 