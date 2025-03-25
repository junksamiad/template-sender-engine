# WhatsApp Processing Engine - SQS Integration

> **Part 2 of 10 in the WhatsApp Processing Engine documentation series**

## 1. Introduction

This document outlines how the WhatsApp Processing Engine consumes messages from the SQS queue and implements the heartbeat pattern for handling long-running operations. These mechanisms are essential for ensuring reliable message processing and preventing premature timeout during API calls.

## 2. SQS Queue Configuration

The WhatsApp engine consumes messages from a dedicated WhatsApp SQS queue with the following configuration:

| Configuration Parameter | Value | Rationale |
|------------------------|-------|-----------|
| Visibility Timeout | 600 seconds (10 minutes) | Provides sufficient time for initial processing while ensuring messages aren't lost if processing fails |
| Batch Size | 1 | Ensures reliable processing of one message at a time, preventing cascading failures |
| Batch Window | 0 seconds | Processes messages immediately without artificial delay |
| Maximum Receives | 3 | After 3 failed attempts, messages are moved to the Dead Letter Queue |
| DLQ Retention Period | 14 days | Provides sufficient time for investigation of failed messages |

## 3. Message Consumption Process

### 3.1 Lambda Trigger

The Lambda function is triggered by new messages in the WhatsApp SQS queue:

```javascript
// In CDK stack
const whatsappLambda = new lambda.Function(this, 'WhatsAppProcessingFunction', {
  // Lambda configuration
});

// Set up the SQS trigger
whatsappLambda.addEventSource(new SqsEventSource(whatsappQueue, {
  batchSize: 1,
  maxBatchingWindow: Duration.seconds(0)
}));
```

### 3.2 Message Handling

When triggered, the Lambda receives the SQS message and begins processing:

```javascript
exports.handler = async (event) => {
  // Get the SQS message (batch size is 1, so there's only one record)
  const message = event.Records[0];
  const receiptHandle = message.receiptHandle;
  
  // Parse the message body (contains the context object)
  const contextObject = JSON.parse(message.body);
  
  // Set up heartbeat timer immediately to prevent timeout
  const heartbeatInterval = setupHeartbeat(receiptHandle);
  
  try {
    // Process the message (implementation details in other sections)
    // ...
    
    // Clean up and delete message on success
    clearInterval(heartbeatInterval);
    await deleteMessage(receiptHandle);
    
    return { statusCode: 200 };
  } catch (error) {
    // Clean up heartbeat timer
    clearInterval(heartbeatInterval);
    
    // Log the error for monitoring
    console.error('Processing error:', error);
    
    // Rethrow to let SQS retry based on visibility timeout
    throw error;
  }
};
```

## 4. Heartbeat Pattern Implementation

The heartbeat pattern is crucial for handling long-running OpenAI operations, which can take several minutes to complete. This pattern extends the SQS message visibility timeout periodically to prevent the message from becoming visible again while processing continues.

### 4.1 Heartbeat Timer Setup

```javascript
function setupHeartbeat(receiptHandle) {
  return setInterval(async () => {
    try {
      await sqs.changeMessageVisibility({
        QueueUrl: process.env.WHATSAPP_QUEUE_URL,
        ReceiptHandle: receiptHandle,
        VisibilityTimeout: 600 // 10 minutes
      }).promise();
      console.log('Extended visibility timeout');
    } catch (error) {
      console.error('Failed to extend visibility timeout', error);
    }
  }, 300000); // 5 minutes (300,000 ms)
}
```

### 4.2 Heartbeat Timing Strategy

The heartbeat timing was carefully chosen with these considerations:

1. **Interval**: 5 minutes (300,000 ms)
   - Extends the visibility timeout well before expiration
   - Provides buffer against potential AWS SDK call failures
   - Balances resource usage with reliable extension

2. **Extension Amount**: 10 minutes (600 seconds)
   - Matches the initial visibility timeout
   - Provides sufficient processing time for subsequent steps
   - Maintains consistency with queue configuration

3. **Considerations**:
   - Each extension resets the visibility timeout to the full value
   - The lambda timeout (15 minutes) exceeds the visibility timeout (10 minutes)
   - Exponential backoff isn't needed since these are scheduled extensions

### 4.3 Cleanup

To prevent resource leaks, the heartbeat interval is always cleared:

```javascript
// On success
clearInterval(heartbeatInterval);
await deleteMessage(receiptHandle);

// On error
clearInterval(heartbeatInterval);
throw error; // Re-throw to allow SQS retry
```

## 5. Message Deletion

Upon successful processing, the message is deleted from the queue:

```javascript
async function deleteMessage(receiptHandle) {
  try {
    await sqs.deleteMessage({
      QueueUrl: process.env.WHATSAPP_QUEUE_URL,
      ReceiptHandle: receiptHandle
    }).promise();
    console.log('Message deleted from queue');
  } catch (error) {
    console.error('Failed to delete message', error);
    throw error;
  }
}
```

## 6. Retry Mechanism

SQS provides built-in retry capabilities:

1. **Transient Failures**: If the Lambda function throws an error, the message becomes visible again after the visibility timeout expires, allowing another Lambda invocation to process it.

2. **Maximum Retries**: After the configured maximum receives (3), the message is automatically moved to the Dead Letter Queue.

3. **Benefit**: This approach leverages AWS's built-in retry mechanisms rather than implementing custom retry logic, simplifying the code and improving reliability.

## 7. Lambda Concurrency Considerations

The SQS queue can trigger multiple concurrent Lambda invocations, which requires careful configuration:

```javascript
// In CDK stack
const whatsappLambda = new lambda.Function(this, 'WhatsAppProcessingFunction', {
  // Other configuration
  reservedConcurrentExecutions: 25,  // Limit concurrent executions
});
```

This reserved concurrency setting:
- Prevents overloading downstream services (OpenAI, Twilio)
- Ensures predictable resource usage
- Protects against throttling and rate limits
- Prevents Lambda invocation saturation in case of processing backlog

## 8. Dead Letter Queue Integration

Messages that fail processing after the maximum retry attempts are moved to a dedicated Dead Letter Queue:

```javascript
// In CDK stack
// Create DLQ
const whatsappDlq = new sqs.Queue(this, 'WhatsAppDLQ', {
  retentionPeriod: cdk.Duration.days(14)
});

// Create main queue with DLQ configuration
const whatsappQueue = new sqs.Queue(this, 'WhatsAppQueue', {
  visibilityTimeout: cdk.Duration.seconds(600),
  deadLetterQueue: {
    queue: whatsappDlq,
    maxReceiveCount: 3
  }
});
```

The DLQ serves several purposes:
- Prevents message loss when processing repeatedly fails
- Provides visibility into persistent failures
- Enables manual review and reprocessing
- Triggers alerts for operations team

## 9. Execution Flow Diagram

```
┌────────────────┐     ┌───────────────┐     ┌─────────────────────────┐
│                │     │               │     │                         │
│  SQS Queue     │────▶│  Lambda       │────▶│  Process Message        │
│                │     │  Function     │     │                         │
└────────────────┘     └───────────────┘     └─────────────┬───────────┘
                                                           │
                                                           ▼
                                             ┌─────────────────────────┐
                                             │                         │
                                             │  Start Heartbeat Timer  │
                                             │                         │
                                             └─────────────┬───────────┘
                                                           │
                                                           ▼
                                             ┌─────────────────────────┐
                                             │  Process OpenAI         │
                                             │  (Long-running)         │
                                             └─────────────┬───────────┘
                                                           │
                              ┌────────────────────────────┴───────────────────────┐
                              │                                                    │
                              ▼                                                    ▼
              ┌─────────────────────────┐                           ┌─────────────────────────┐
              │  Every 5 minutes:       │                           │                         │
              │  Extend Visibility      │                           │  Continue Processing    │
              │  Timeout                │                           │                         │
              └─────────────────────────┘                           └─────────────┬───────────┘
                                                                                  │
                                                                                  ▼
                                                                    ┌─────────────────────────┐
                                                                    │                         │
                                                                    │  Success?               │
                                                                    │                         │
                                                                    └─────────────┬───────────┘
                                                                                  │
                                             ┌────────────────────────────────────┴───────────────────────┐
                                             │                                                            │
                                             ▼                                                            ▼
                                ┌─────────────────────────┐                           ┌─────────────────────────┐
                                │                         │                           │                         │
                                │  Clear Heartbeat        │                           │  Clear Heartbeat        │
                                │  Delete Message         │                           │  Re-throw Error         │
                                │                         │                           │  (SQS will retry)       │
                                └─────────────────────────┘                           └─────────────────────────┘
```

## 10. Implementation Considerations

1. **Logging**: All SQS operations (receives, visibility extensions, deletes) are logged with correlation IDs.

2. **Timeout Coordination**: The Lambda timeout (15 minutes) exceeds the visibility timeout (10 minutes) to ensure proper cleanup.

3. **CloudWatch Metrics**: Custom metrics track visibility timeout extensions to monitor long-running operations.

4. **Error Handling**: SQS-specific errors (e.g., invalid receipt handle) are handled separately from business logic errors.

5. **Idempotency**: The processing logic is designed to be idempotent, safely handling potential duplicate message deliveries.

## 11. Related Documentation

- [Overview and Architecture](./01-overview-architecture.md)
- [Error Handling Strategy](./08-error-handling-strategy.md)
- [Monitoring and Observability](./09-monitoring-observability.md) 