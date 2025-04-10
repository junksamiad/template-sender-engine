# AI Multi-Comms Engine - Unit Test Plan

## 1. Introduction

This document outlines the unit testing strategy for the AI Multi-Comms Engine. Unit tests focus on verifying the smallest testable parts of the application (individual functions, methods, or classes) in isolation, mocking external dependencies like AWS services and third-party APIs.

**Goal:** Ensure individual code components function correctly according to their specifications and catch bugs early in the development cycle.
**Tools:** `pytest`, `moto`, `unittest.mock`

## 2. Scope & Test Cases

### 2.1. Channel Router Lambda (`src_dev/channel-router/lambda/`)

*   **`utils/request_parser.py`**
    *   [ ] Test parsing valid API Gateway proxy event structures.
    *   [ ] Test parsing events with missing/malformed bodies.
    *   [ ] Test handling different `Content-Type` headers (if relevant).
    *   [ ] Test extraction of `x-api-key` header.
*   **`utils/validators.py`**
    *   [ ] Test validation against the expected request payload schema.
    *   [ ] Test with payloads missing required fields.
    *   [ ] Test with payloads having fields with incorrect data types.
    *   [ ] Test with extra, unexpected fields in the payload.
*   **`core/context_builder.py`**
    *   [ ] Test `create_conversation_id` for WhatsApp (strips '+').
    *   [ ] Test `create_conversation_id` for other hypothetical channels (e.g., Email).
    *   [ ] Test `generate_conversation_data_dict` structure and content.
    *   [ ] Test `build_context_object` with various inputs, verify correct structure and inclusion of metadata (like `VERSION`).
*   **`services/dynamodb_service.py` (Mock `boto3.client('dynamodb')`)**
    *   [ ] Test successful fetching of a company config item.
    *   [ ] Test handling `ItemNotFound` when a config item doesn't exist.
    *   [ ] Test correct handling of DynamoDB specific types (e.g., Decimals to Python floats/ints).
    *   [ ] Test error handling for potential Boto3 exceptions during `get_item`.
*   **`services/sqs_service.py` (Mock `boto3.client('sqs')`)**
    *   [ ] Test `send_message_to_queue` builds the correct SQS message body (serialized JSON Context Object).
    *   [ ] Test `send_message_to_queue` includes correct `MessageAttributes` (e.g., `company_id`, `project_id`).
    *   [ ] Test error handling for potential Boto3 exceptions during `send_message`.
    *   [ ] Test retry logic implementation (if applicable within the unit).
*   **`utils/response_builder.py`**
    *   [ ] Test `create_success_response` generates correct HTTP status code (200) and body structure.
    *   [ ] Test `create_error_response` generates correct HTTP status codes (4xx, 5xx) and error message format.
*   **`index.py` (Main Handler - Mock all services)**
    *   [ ] Test successful flow: valid request -> parse -> validate -> fetch config -> build context -> send SQS -> return success response.
    *   [ ] Test flow where request parsing fails.
    *   [ ] Test flow where request validation fails.
    *   [ ] Test flow where config fetch from DynamoDB fails or returns no item.
    *   [ ] Test flow where project status is inactive or channel is not allowed based on config.
    *   [ ] Test flow where SQS send fails.
    *   [ ] Test correct logging for different scenarios (info, error, warning).
    *   [ ] Test correct handling of environment variables.

### 2.2. WhatsApp Channel Processor Lambda (`src_dev/channel-processor/whatsapp/lambda/`)

*   **`utils/context_utils.py`**
    *   [ ] Test parsing valid SQS message event structure.
    *   [ ] Test extracting and deserializing the Context Object from the SQS message body.
    *   [ ] Test validation of the deserialized Context Object schema.
    *   [ ] Test handling malformed SQS events or message bodies.
*   **`utils/sqs_heartbeat.py` (Mock `boto3.client('sqs').change_message_visibility`)**
    *   [ ] Test `start` method correctly calculates initial delay.
    *   [ ] Test heartbeat thread sends `change_message_visibility` calls periodically.
    *   [ ] Test `stop` method terminates the heartbeat thread correctly.
    *   [ ] Test handling Boto3 errors during `change_message_visibility`.
*   **`services/dynamodb_service.py` (Mock `boto3.client('dynamodb')`)**
    *   [ ] Test `create_initial_conversation_record`:
        *   [ ] Successful creation of a new record.
        *   [ ] Correct item structure based on Context Object.
        *   [ ] Idempotency: Test that calling it again with the same `conversation_id` does not overwrite (handles `ConditionalCheckFailedException` gracefully).
        *   [ ] Error handling for other Boto3 exceptions.
    *   [ ] Test `update_conversation_after_send`:
        *   [ ] Successful update of status, timestamp, thread ID, etc.
        *   [ ] Correct use of `list_append` for message history.
        *   [ ] Correct calculation of processing time.
        *   [ ] Error handling for Boto3 exceptions.
*   **`services/secrets_manager_service.py` (Mock `boto3.client('secretsmanager')`)**
    *   [ ] Test successful fetching and JSON parsing of a secret string.
    *   [ ] Test handling `ResourceNotFoundException` when a secret doesn't exist.
    *   [ ] Test handling non-JSON secret strings (if applicable).
    *   [ ] Test error handling for other Boto3 exceptions.
*   **`services/openai_service.py` (Mock `openai` client)**
    *   [ ] Test `process_message_with_ai`:
        *   [ ] Correct initialization of the OpenAI client.
        *   [ ] Correct creation of a new thread.
        *   [ ] Correct building of the initial message content.
        *   [ ] Correct creation and polling of an Assistant run.
        *   [ ] Successful retrieval and parsing of the assistant's JSON response.
        *   [ ] Handling of OpenAI API errors during thread/message/run operations.
        *   [ ] Handling of run timeouts.
        *   [ ] Handling of invalid/non-JSON responses from the assistant.
        *   [ ] Correct extraction of `content_variables`, `thread_id`, and token usage.
*   **`services/twilio_service.py` (Mock `twilio.rest.Client`)**
    *   [ ] Test `send_whatsapp_template_message`:
        *   [ ] Correct initialization of the Twilio client.
        *   [ ] Correct parameters passed to Twilio's `messages.create` (to, from, content_sid, content_variables).
        *   [ ] Handling of Twilio API errors.
*   **`index.py` (Main Handler - Mock all services)**
    *   [ ] Test successful flow: parse SQS -> start heartbeat -> create initial DB record -> fetch secrets -> process with AI -> send Twilio message -> update final DB record -> stop heartbeat.
    *   [ ] Test flow where SQS parsing fails.
    *   [ ] Test flow where initial DB write fails (including idempotency check).
    *   [ ] Test flow where Secrets Manager fetch fails for OpenAI key.
    *   [ ] Test flow where Secrets Manager fetch fails for Twilio creds.
    *   [ ] Test flow where OpenAI processing fails (API error, timeout, bad response).
    *   [ ] Test flow where Twilio send fails.
    *   [ ] Test flow where final DB update fails (**ensure critical error is logged**).
    *   [ ] Test correct handling of the SQS heartbeat lifecycle in success and failure scenarios.
    *   [ ] Test correct logging throughout the process.
    *   [ ] Test correct handling of environment variables.

## 3. Execution & Reporting

*   Unit tests should be runnable locally without requiring AWS credentials or network access (due to mocking).
*   Tests should be integrated into a CI/CD pipeline to run automatically on code changes.
*   Test results and code coverage reports should be generated and reviewed. 