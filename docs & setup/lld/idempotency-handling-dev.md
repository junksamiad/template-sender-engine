# Idempotency Handling in AI Multi-Comms Engine (Dev Environment)

## 1. Introduction

This document outlines the idempotency mechanisms implemented within the AI Multi-Comms Engine, specifically focusing on how duplicate requests are handled by the **WhatsApp Channel Processor Lambda**. Ensuring idempotency is crucial to prevent unintended side effects, such as sending duplicate messages to end-users or creating inconsistent state, which can arise from network retries or message queue redeliveries.

The primary goal is to ensure that processing the same logical request multiple times has the same net effect as processing it exactly once. 

## 2. Scenarios Requiring Idempotency

Two primary scenarios can lead to the WhatsApp Processor Lambda receiving the same logical request multiple times:

### Scenario 1: Frontend/API Retry

*   **Cause:** A client (e.g., the future frontend application) sends an initial request to the `/initiate-conversation` API Gateway endpoint. Due to network issues, timeouts, or transient server-side errors (5xx), the client might not receive a timely success response.
*   **Client Behavior:** Standard client-side retry logic may dictate resending the *exact same request payload*, including the original `request_id` it generated.
*   **Router Behavior:** The Channel Router Lambda (`src_dev/channel_router/app/lambda_pkg/index.py`) receives this duplicate API request. **Crucially, the router currently *does not* implement its own idempotency check based on `request_id`**. Therefore, it processes the duplicate request as if it were new and sends a second, identical message (with the same derived `conversation_id`) to the WhatsApp SQS queue.
*   **Processor Impact:** The WhatsApp Processor Lambda receives two separate SQS messages that represent the same initial user request.

### Scenario 2: SQS Message Redelivery

*   **Cause:** The Channel Router successfully sends a message to the WhatsApp SQS queue exactly once. The WhatsApp Processor Lambda picks up the message and begins processing.
*   **Mid-Processing Failure:** The Lambda fails unexpectedly *after* successfully creating the initial conversation record in DynamoDB but *before* successfully completing all steps and deleting the message from SQS. Failures could occur during secret fetching, AI processing (OpenAI), message sending (Twilio), or due to Lambda timeouts or crashes.
*   **SQS Behavior:** Because the message wasn't successfully processed and deleted, after the SQS message's visibility timeout expires, SQS makes the message available again for delivery.
*   **Processor Impact:** The WhatsApp Processor Lambda receives the *exact same SQS message* for a second (or subsequent) time.

## 3. Processor Implementation Details

Given that duplicate messages can arrive on the SQS queue from either Scenario 1 or Scenario 2, the WhatsApp Processor Lambda (`src_dev/channel_processor/whatsapp/app/lambda_pkg/index.py`) implements idempotency handling at the point of creating the conversation state record.

### 3.1. DynamoDB Conditional Write (`dynamodb_service.py`)

*   The core check occurs within the `create_initial_conversation_record` function in `src_dev/channel_processor/whatsapp/app/lambda_pkg/services/dynamodb_service.py`.
*   When attempting to create the initial record for a conversation, this function uses a DynamoDB `PutItem` operation with a `ConditionExpression="attribute_not_exists(conversation_id)"`.
*   The `conversation_id` (which includes the `request_id` as part of its construction in the router) serves as the idempotency key at this stage.
*   **If the `PutItem` succeeds:** This is the first time this `conversation_id` is being processed. The function returns `True`.
*   **If the `PutItem` fails with `ConditionalCheckFailedException`:** This means a record with this `conversation_id` already exists. The function logs an informational message (`Record already exists...`) and returns `False`.
*   **If `PutItem` fails with other errors:** The function logs the error and returns `False`.

### 3.2. Lambda Handler Logic (`index.py`)

*   The `lambda_handler` in `src_dev/channel_processor/whatsapp/app/lambda_pkg/index.py` calls `db_service.create_initial_conversation_record`.
*   **If `True` is returned:** Processing continues normally (fetch secrets, call AI, call Twilio, update DB).
*   **If `False` is returned:** The handler performs the following steps:
    1.  Retrieves the `ApproximateReceiveCount` attribute from the incoming SQS record.
    2.  **If `ApproximateReceiveCount == 1`:** It logs a warning indicating a likely duplicate request (Scenario 1).
    3.  **If `ApproximateReceiveCount > 1`:** It logs a warning indicating an SQS redelivery after a previous failure (Scenario 2).
    4.  In **both** cases where `False` is returned, it adds the SQS message ID to a list of `successful_record_ids`.
    5.  It stops the SQS heartbeat timer (if active) for this message.
    6.  It executes a `continue` statement, skipping all subsequent processing steps (fetching secrets, AI, Twilio, final DB update) for this specific SQS message and moving to the next message in the batch (if any).
*   **SQS Message Deletion:** Because the message ID was added to `successful_record_ids` (even though processing was halted), the Lambda function returns a success status to the SQS trigger for this specific message. SQS then deletes the message from the queue, preventing further redeliveries of the duplicate/failed message.

### 3.3. Current Limitations

*   **No Resume Logic:** While the current implementation correctly prevents duplicate downstream actions (AI calls, Twilio messages) for both duplicate requests and SQS redeliveries, it **does not** implement logic to resume processing from a failure point in Scenario 2. If a message fails mid-processing, the redelivered message will simply be detected as a duplicate and discarded.
*   **Router Idempotency:** As noted, the Channel Router does not currently have its own idempotency check based on `request_id`. Implementing this would be a potential future enhancement to stop duplicates earlier in the flow. 

## 4. Conclusion

The current idempotency strategy relies on the WhatsApp Processor Lambda using DynamoDB conditional writes (`attribute_not_exists`) on the `conversation_id` to detect duplicate conversation initializations.

The handler distinguishes between initial duplicate requests and SQS redeliveries using `ApproximateReceiveCount` for logging purposes but treats both scenarios by halting processing for the duplicate message and allowing it to be successfully deleted from the SQS queue.

This prevents duplicate downstream actions but does not implement automatic resumption of partially failed processes. 