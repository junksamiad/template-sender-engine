# Error Tracking Strategies for Channel Engines

This document outlines industry-standard approaches for tracking errors in channel engines while maintaining a clean separation of concerns in a distributed system architecture.

## 1. Comprehensive Logging

### Implementation:
- Use structured logging with consistent formats across all channel engines
- Include request_id in all logs for correlation
- Log at appropriate levels (ERROR, WARN, INFO, DEBUG)
- Include contextual information like company_id, channel_method, and timestamps

### Tools:
- CloudWatch Logs for AWS-based components
- Centralized logging solutions like ELK Stack (Elasticsearch, Logstash, Kibana) or Datadog
- Log aggregation to combine logs from all channel engines

### Example Log Format:
```json
{
  "timestamp": "2023-03-16T12:34:56.789Z",
  "level": "ERROR",
  "request_id": "req-123456",
  "company_id": "cucumber-recruitment",
  "project_id": "cv-analysis",
  "channel_method": "whatsapp",
  "message": "Failed to send WhatsApp message",
  "error": {
    "code": "TWILIO_ERROR",
    "message": "Rate limit exceeded",
    "service": "Twilio"
  },
  "context": {
    "recipient": "+447700900123",
    "template_id": "template_abc123"
  }
}
```

## 2. Error Monitoring and Alerting

### Implementation:
- Set up alerts for critical errors and error rate thresholds
- Create dashboards showing error rates by channel, company, and error type
- Implement dead letter queues (DLQs) for failed processing attempts
- Use anomaly detection to identify unusual error patterns

### Tools:
- CloudWatch Alarms
- PagerDuty or OpsGenie for on-call notifications
- Sentry or Rollbar for error tracking
- Custom dashboards in Grafana or CloudWatch

### Alert Configuration Example:
```yaml
# CloudWatch Alarm configuration
Alarms:
  CriticalErrors:
    Metric: ErrorCount
    Threshold: 10
    Period: 5m
    EvaluationPeriods: 1
    ComparisonOperator: GreaterThanThreshold
    TreatMissingData: notBreaching
    Dimensions:
      - Name: ChannelMethod
        Value: whatsapp
      - Name: ErrorSeverity
        Value: critical
    AlarmActions:
      - arn:aws:sns:region:account-id:critical-errors-topic
```

## 3. Distributed Tracing

### Implementation:
- Implement trace IDs that flow through all components
- Record timing information for each processing step
- Visualize request flows across services
- Identify bottlenecks and failure points

### Tools:
- AWS X-Ray
- Jaeger or Zipkin
- OpenTelemetry for standardized instrumentation

### X-Ray Configuration Example:
```javascript
// AWS X-Ray setup for Lambda function
const AWSXRay = require('aws-xray-sdk');
const AWS = AWSXRay.captureAWS(require('aws-sdk'));

exports.handler = async (event) => {
  // Create subsegment for processing step
  const segment = AWSXRay.getSegment();
  const subsegment = segment.addNewSubsegment('process-message');
  
  try {
    // Process message
    const result = await processMessage(event);
    subsegment.addAnnotation('company_id', event.company_data.company_id);
    subsegment.addAnnotation('channel_method', event.channel_data.channel_method);
    subsegment.close();
    return result;
  } catch (error) {
    subsegment.addError(error);
    subsegment.close();
    throw error;
  }
};
```

## 4. Health Check Endpoints

### Implementation:
- Create internal health check endpoints in each channel engine
- Report operational status and basic metrics
- Include in infrastructure monitoring
- Use for automated recovery processes

### Example Health Check Response:
```json
{
  "status": "healthy",
  "version": "1.2.3",
  "uptime": "3d 4h 12m",
  "metrics": {
    "requests_processed_1h": 1250,
    "error_rate_1h": 0.02,
    "avg_processing_time_ms": 345
  },
  "dependencies": {
    "twilio": {
      "status": "healthy",
      "latency_ms": 120
    },
    "openai": {
      "status": "degraded",
      "latency_ms": 450
    },
    "dynamodb": {
      "status": "healthy",
      "latency_ms": 15
    }
  }
}
```

## 5. Error Handling Patterns

### Retry Logic:
- Implement exponential backoff for transient errors
- Set maximum retry attempts
- Move to DLQ after retry exhaustion

```javascript
async function sendWithRetry(message, maxRetries = 3) {
  let retries = 0;
  while (retries <= maxRetries) {
    try {
      return await sendMessage(message);
    } catch (error) {
      if (!isTransientError(error) || retries === maxRetries) {
        // Move to DLQ if max retries reached or non-transient error
        await sendToDLQ(message, error);
        throw error;
      }
      
      // Exponential backoff
      const delay = Math.pow(2, retries) * 100;
      await new Promise(resolve => setTimeout(resolve, delay));
      retries++;
    }
  }
}
```

### Circuit Breaker Pattern:
- Temporarily disable operations that consistently fail
- Prevent cascading failures
- Automatically test and restore service when appropriate

### Fallback Mechanisms:
- Define fallback behaviors for critical operations
- Gracefully degrade functionality rather than failing completely

## 6. Administrative Interface

### Implementation:
- Build an admin portal for operations team
- Show system health across all channel engines
- Allow searching for specific requests by ID
- Provide ability to retry failed requests manually

### Features:
- Error logs viewer
- Request tracing visualization
- Manual intervention tools
- System health dashboard

### Admin Portal Capabilities:
- View all errors by channel, company, or time period
- Drill down into specific error details
- Manually retry failed messages
- Configure alerting thresholds
- View system health metrics
- Access audit logs of administrative actions

## 7. Error Reporting Workflow

For critical errors, implement a workflow:

1. **Detect:** Error occurs and is logged
2. **Alert:** Notification sent to appropriate team
3. **Diagnose:** Error details available in monitoring tools
4. **Resolve:** Fix applied or manual intervention
5. **Prevent:** Update system to prevent similar errors

## Real-World Example

Consider a WhatsApp message that fails to send:

1. WhatsApp engine logs detailed error with request_id, recipient, error code from Twilio
2. Error is stored in DynamoDB error tracking table
3. If error is critical (e.g., authentication failure), alert is triggered
4. For transient errors (e.g., recipient unavailable), automatic retry is scheduled
5. Admin portal shows failed message with retry option
6. Metrics dashboard shows spike in WhatsApp delivery failures

## Dead Letter Queues (DLQs)

A Dead Letter Queue is a queue where messages that fail processing are sent after multiple unsuccessful attempts.

### Benefits:
- Prevents message loss when processing fails
- Provides visibility into failure rates
- Allows manual review and reprocessing
- Prevents endless retry loops
- Preserves exact message content for debugging

### AWS Implementation:
```typescript
// Create main queue and DLQ
const whatsappDlq = new sqs.Queue(this, 'WhatsAppDLQ');

const whatsappQueue = new sqs.Queue(this, 'WhatsAppQueue', {
  deadLetterQueue: {
    queue: whatsappDlq,
    maxReceiveCount: 3
  }
});

// Create alarm for DLQ
new cloudwatch.Alarm(this, 'DLQAlarm', {
  metric: whatsappDlq.metricApproximateNumberOfMessagesVisible(),
  threshold: 1,
  evaluationPeriods: 1,
  alarmDescription: 'Messages in WhatsApp DLQ'
});
```

### DLQ Processor Lambda

To complete the DLQ error handling flow, a dedicated DLQ Processor Lambda function is implemented:

```typescript
// Create DLQ Processor Lambda
const dlqProcessorFunction = new lambda.Function(this, 'DLQProcessorFunction', {
  runtime: lambda.Runtime.NODEJS_14_X,
  handler: 'dlq-processor.handler',
  code: lambda.Code.fromAsset('lambda/dlq-processor'),
  timeout: cdk.Duration.seconds(60),
  environment: {
    CONVERSATION_TABLE_NAME: conversationTable.tableName
  }
});

// Add DLQ as event source
dlqProcessorFunction.addEventSource(new SqsEventSource(whatsappDlq, {
  batchSize: 10
}));

// Grant permissions to read from DLQ and write to DynamoDB
whatsappDlq.grantConsumeMessages(dlqProcessorFunction);
conversationTable.grantReadWriteData(dlqProcessorFunction);
```

The DLQ Processor Lambda function handles failed messages by:

1. **Reading messages from the DLQ**: Processes messages that failed processing after multiple retries
2. **Parsing the original request**: Extracts the original context from the failed message
3. **Updating conversation status**: Sets the conversation status to "failed" in DynamoDB
4. **Recording error information**: Stores detailed error context for troubleshooting
5. **Emitting metrics**: Publishes custom CloudWatch metrics for monitoring failed messages

Example implementation:

```javascript
// dlq-processor.js
const AWS = require('aws-sdk');
const dynamoDB = new AWS.DynamoDB.DocumentClient();
const cloudwatch = new AWS.CloudWatch();

exports.handler = async (event) => {
  const processedMessages = [];
  const errors = [];
  
  for (const record of event.Records) {
    try {
      // Parse original message from DLQ
      const originalMessage = JSON.parse(record.body);
      const originalBody = JSON.parse(originalMessage.body);
      
      // Extract key information from the original message
      const { frontend_payload, channel_config } = originalBody;
      const { company_data, recipient_data, request_data } = frontend_payload;
      const channelMethod = request_data.channel_method;
      
      // Generate the same conversation ID that was used in the original processing
      const conversationId = generateConversationId(
        company_data.company_id,
        company_data.project_id,
        request_data.request_id,
        channel_config[channelMethod].company_phone_number || 
        channel_config[channelMethod].company_email
      );
      
      // Look up the conversation in DynamoDB
      const conversation = await getConversationRecord(
        channelMethod === 'email' ? recipient_data.recipient_email : recipient_data.recipient_tel,
        conversationId
      );
      
      // Update status to failed
      await updateConversationStatus(conversation, 'failed', {
        error_message: "Message processing failed after maximum retry attempts",
        component: "unknown" // We don't always know which component failed from DLQ
      });
      
      // Emit metrics for monitoring
      await cloudwatch.putMetricData({
        Namespace: 'ChannelRouter',
        MetricData: [
          {
            MetricName: 'StatusUpdatedToFailed',
            Value: 1,
            Unit: 'Count',
            Dimensions: [
              {
                Name: 'Channel',
                Value: channelMethod
              }
            ]
          }
        ]
      }).promise();
      
      processedMessages.push(conversationId);
    } catch (error) {
      console.error('Error processing DLQ message', error);
      errors.push(error.message);
    }
  }
  
  // Report processing results
  return {
    processedCount: processedMessages.length,
    errorCount: errors.length,
    processed: processedMessages,
    errors: errors
  };
};
```

This approach provides several benefits for error handling:

1. **Complete error lifecycle**: Failed messages are properly tracked from initial failure through final status update
2. **Operational visibility**: Operations team can monitor both DLQ message counts and status updates
3. **Error recovery**: The detailed error information stored in DynamoDB enables troubleshooting
4. **Clean separation of concerns**: The processing Lambda focuses on the happy path, while the DLQ processor handles failure cases

## Implementation Priority

For your phased approach:

1. **Phase 1:** Basic structured logging and error tables
2. **Phase 2:** Monitoring dashboards and alerts
3. **Phase 3:** Admin interface for operations
4. **Phase 4:** Advanced patterns like circuit breakers and distributed tracing

This approach gives you visibility into errors without coupling your frontend to the channel engines, maintaining your clean separation of concerns while ensuring operational excellence. 