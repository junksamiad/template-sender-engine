# WhatsApp Processing Engine - Monitoring and Observability

> **Part 9 of 10 in the WhatsApp Processing Engine documentation series**

## 1. Introduction

This document details the monitoring and observability strategy implemented in the WhatsApp Processing Engine. Comprehensive monitoring is critical for ensuring system reliability, identifying performance bottlenecks, detecting anomalies, and providing visibility into the system's operational state.

## 2. Monitoring Architecture

The monitoring architecture follows these key principles:

1. **Multi-Dimensional**: Metrics capture multiple facets of system behavior
2. **Granular**: Provides detailed visibility into specific components
3. **Contextual**: Metrics are correlated with relevant business context
4. **Actionable**: Thresholds and alerts designed for quick response
5. **Comprehensive**: Covers all system layers from infrastructure to business logic

## 3. CloudWatch Metrics

### 3.1 Core Service Metrics

The following core metrics are tracked:

| Metric Name | Description | Unit | Dimensions | Notes |
|-------------|-------------|------|------------|-------|
| `MessageProcessingTime` | Time to process a message | Milliseconds | `CompanyId`, `ProjectId` | P50, P90, P99 percentiles |
| `MessageVolume` | Number of messages processed | Count | `CompanyId`, `ProjectId`, `Status` | Status: received, processed, failed |
| `OpenAILatency` | Time for OpenAI API calls | Milliseconds | `OperationType` | Create thread, generate response |
| `TwilioLatency` | Time for Twilio API calls | Milliseconds | `OperationType` | Send message, get templates |
| `DynamoDBOperations` | Number of DynamoDB operations | Count | `TableName`, `OperationType` | Get, put, update, query |
| `LambdaInvocations` | Number of Lambda invocations | Count | `FunctionName`, `Type` | Direct, SQS-triggered |
| `QueueDepth` | Number of messages in SQS queue | Count | `QueueName` | Main queue, DLQ |
| `TokenUsage` | Number of tokens used with OpenAI | Count | `CompanyId`, `ProjectId`, `TokenType` | Prompt, completion, total |

### 3.2 Implementation

Metrics are published using the CloudWatch API:

```javascript
/**
 * Publishes metrics to CloudWatch
 * @param {string} metricName - Name of the metric
 * @param {number} value - Metric value
 * @param {object} dimensions - Metric dimensions
 * @param {string} unit - Metric unit
 */
async function publishMetric(metricName, value, dimensions, unit = 'Count') {
  try {
    const cloudwatch = new AWS.CloudWatch();
    const dimensionsArray = Object.entries(dimensions).map(([name, value]) => ({
      Name: name,
      Value: value
    }));
    
    await cloudwatch.putMetricData({
      Namespace: 'ChannelRouter/WhatsAppProcessingEngine',
      MetricData: [
        {
          MetricName: metricName,
          Dimensions: dimensionsArray,
          Value: value,
          Unit: unit,
          Timestamp: new Date()
        }
      ]
    }).promise();
  } catch (error) {
    console.error('Error publishing metric:', error);
    // Don't let metric publishing failures affect the main flow
  }
}
```

Example metric calls throughout the code:

```javascript
// Track message processing time
const startTime = Date.now();
// ... processing logic ...
const processingTime = Date.now() - startTime;

await publishMetric(
  'MessageProcessingTime',
  processingTime,
  {
    CompanyId: message.company_id,
    ProjectId: message.project_id
  },
  'Milliseconds'
);

// Track OpenAI token usage
await publishMetric(
  'TokenUsage',
  response.usage.total_tokens,
  {
    CompanyId: message.company_id,
    ProjectId: message.project_id,
    TokenType: 'Total'
  },
  'Count'
);
```

## 4. Custom Metrics

The WhatsApp Processing Engine emits custom CloudWatch metrics to provide detailed visibility into operations:

### 4.1 Operational Metrics

| Metric Name | Description | Dimensions | Unit | Statistics |
|-------------|-------------|------------|------|-----------|
| `MessageProcessingTime` | Time to process a message end-to-end | `CompanyId`, `ProjectId` | Milliseconds | Average, P90, P99 |
| `OpenAICallDuration` | Duration of OpenAI API calls | `Operation` (createThread, createRun, etc.) | Milliseconds | Average, P90, P99 |
| `OpenAIRetryCount` | Number of retries for OpenAI API calls | `Operation` | Count | Sum, Average |
| `TwilioCallDuration` | Duration of Twilio API calls | `Operation` (sendMessage, etc.) | Milliseconds | Average, P90, P99 |
| `FunctionExecutionTime` | Time to execute OpenAI functions | `FunctionName` | Milliseconds | Average, P90, P99 |
| `DynamoDBOperationTime` | Duration of DynamoDB operations | `Operation`, `TableName` | Milliseconds | Average, P90, P99 |
| `TotalTokenUsage` | Total tokens used in OpenAI calls | `CompanyId`, `ProjectId` | Count | Sum |
| `PromptTokenUsage` | Prompt tokens used in OpenAI calls | `CompanyId`, `ProjectId` | Count | Sum |
| `CompletionTokenUsage` | Completion tokens used in OpenAI calls | `CompanyId`, `ProjectId` | Count | Sum |
| `AssistantConfigurationIssue` | Count of assistant configuration issues | `ConversationId`, `AssistantId`, `ProcessingStage`, `IssueType`, `Environment` | Count | Sum |

### 4.2 SQS Metrics

| Metric Name | Description | Dimensions | Unit | Statistics |
|-------------|-------------|------------|------|-----------|
| `HeartbeatExtensions` | Number of visibility timeout extensions | None | Count | Sum |
| `VisibilityTimeoutTotal` | Total processing time with extensions | None | Seconds | Average, Max |
| `MessagesProcessed` | Count of successfully processed messages | None | Count | Sum |
| `MessagesFailed` | Count of failed messages sent to DLQ | `ErrorCategory` | Count | Sum |

## 5. CloudWatch Dashboards

The system includes pre-configured CloudWatch dashboards for monitoring:

### 5.1 Main Operational Dashboard

The main dashboard provides a holistic view of the system:

![Main Dashboard](../../diagrams/monitoring-main-dashboard.png)

#### Widgets:
- **System Health**: Error rates, DLQ message counts, system uptime
- **Performance Metrics**: Processing times, API latencies, queue depths
- **Message Flow**: Messages processed per minute, success rates, failure rates
- **External Dependencies**: OpenAI and Twilio API health and performance

### 5.2 WhatsApp Processing Dashboard

This dashboard focuses specifically on WhatsApp processing:

![WhatsApp Dashboard](../../diagrams/monitoring-whatsapp-dashboard.png)

#### Widgets:
- **Message Processing**: Volumes, success rates, processing times
- **OpenAI Integration**: Thread creation, run times, token usage
- **Function Execution**: Execution counts, durations, success rates
- **Twilio Integration**: Message sending latency, delivery rates
- **Assistant Configuration Issues**: Configuration errors by type and assistant

### 5.3 Error Investigation Dashboard

This dashboard aids in diagnosing and resolving errors:

![Error Dashboard](../../diagrams/monitoring-error-dashboard.png)

#### Widgets:
- **DLQ Message Counts**: By queue and error type
- **Error Rates**: Breakdowns by category and source
- **Error Timelines**: Error occurrence patterns
- **Retry Statistics**: Success rates after retries
- **Assistant Configuration Issues**: Detailed breakdown with conversation and assistant IDs

#### 5.1.3 Assistant Configuration Metrics

| Metric Name | Description | Dimensions | Statistics |
|-------------|-------------|------------|------------|
| `AssistantConfigurationIssue` | Count of assistant configuration issues | AssistantId, IssueType, ConversationId | Sum, Maximum |

The `IssueType` dimension can have the following values:
- `InvalidJSONResponse`: The assistant did not return valid JSON.
- `MissingVariables`: The assistant returned JSON without the required variables.

These metrics allow operational teams to quickly identify if there are issues with the AI assistant configuration that need to be addressed.

#### 5.1.4 JSON Parsing Error Metrics

| Metric Name | Description | Dimensions | Statistics |
|-------------|-------------|------------|------------|
| `JSONParsingError` | Count of JSON parsing errors | AssistantId, ErrorType, TemplateName | Sum, Maximum |
| `VariableValidationError` | Count of variable validation errors | AssistantId, TemplateName, VariableName | Sum, Maximum |

The `ErrorType` dimension for JSON parsing errors can have values like:
- `SyntaxError`: Invalid JSON syntax in the response.
- `MissingVariables`: JSON parsed but variables object is missing.
- `MalformedVariables`: Variables don't follow the expected format.

These metrics help track issues with the new JSON-based template variable approach.

## 6. CloudWatch Alarms

The system includes the following alarms for critical conditions:

### 6.1 Critical Alarms

| Alarm Name | Condition | Threshold | Period | Evaluation Periods | Actions |
|------------|-----------|-----------|--------|-------------------|---------|
| HighErrorRate | Error rate exceeds threshold | >5% | 5 minutes | 3 | SNS notification to operations team |
| DLQMessageCount | Messages in DLQ | >0 | 5 minutes | 1 | SNS notification to operations team |
| APITimeout | OpenAI API timeouts | >3 | 15 minutes | 1 | SNS notification to operations team |
| HighLatency | Processing time | >30 seconds | 5 minutes | 3 | SNS notification to operations team |
| AssistantConfigurationIssues | Configuration errors detected | >0 | 5 minutes | 1 | SNS notification to operations team |

### 6.2 Warning Alarms

| Alarm Name | Condition | Threshold | Period | Evaluation Periods | Actions |
|------------|-----------|-----------|--------|-------------------|---------|
| ElevatedErrorRate | Error rate exceeds threshold | >2% | 15 minutes | 3 | Email to development team |
| HighTokenUsage | Token usage spike | >200% of baseline | 1 hour | 1 | Email to development team |
| IncreasedLatency | Processing time | >15 seconds | 15 minutes | 3 | Email to development team |
| OpenAIRateLimiting | Rate limit errors | >0 | 15 minutes | 3 | Email to development team |

### 6.3 Assistant Configuration Issue Alarms

| Alarm Name | Condition | Threshold | Period | Evaluation Periods | Actions |
|------------|-----------|-----------|--------|-------------------|---------|
| MissingFunctionCallIssue | Missing function call errors | >0 | 5 minutes | 1 | SNS high-priority notification |
| UnexpectedFunctionCallIssue | Unexpected function call errors | >0 | 5 minutes | 1 | SNS high-priority notification |
| RecurringConfigurationIssues | Configuration issues on same assistant | >3 | 1 hour | 1 | SNS + ticketing system |

## 7. Structured Logging

### 7.1 Log Format

All logs follow a consistent structured format:

```javascript
/**
 * Structured logger for the WhatsApp Processing Engine
 */
class Logger {
  constructor(context = {}) {
    this.context = context;
  }
  
  /**
   * Log at info level
   * @param {string} message - Log message
   * @param {object} data - Additional data to log
   */
  info(message, data = {}) {
    this._log('INFO', message, data);
  }
  
  /**
   * Log at warning level
   * @param {string} message - Log message
   * @param {object} data - Additional data to log
   */
  warn(message, data = {}) {
    this._log('WARN', message, data);
  }
  
  /**
   * Log at error level
   * @param {string} message - Log message
   * @param {object} data - Additional data to log
   */
  error(message, data = {}) {
    // Include stack trace for errors
    if (data.error instanceof Error) {
      data.error_stack = data.error.stack;
      data.error_message = data.error.message;
      data.error = undefined; // Remove circular references
    }
    
    this._log('ERROR', message, data);
  }
  
  /**
   * Internal logging method
   * @param {string} level - Log level
   * @param {string} message - Log message
   * @param {object} data - Additional data to log
   * @private
   */
  _log(level, message, data) {
    const timestamp = new Date().toISOString();
    const logEntry = {
      timestamp,
      level,
      message,
      ...this.context,
      ...data
    };
    
    // Sanitize sensitive information
    this._sanitizeSensitiveInfo(logEntry);
    
    // Output as JSON
    console.log(JSON.stringify(logEntry));
  }
  
  /**
   * Sanitize sensitive information in logs
   * @param {object} obj - Object to sanitize
   * @private
   */
  _sanitizeSensitiveInfo(obj) {
    const sensitiveKeys = [
      'api_key', 'auth_token', 'password', 'secret',
      'access_key', 'twilio_auth_token', 'openai_api_key'
    ];
    
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        // Check if current key is sensitive
        if (sensitiveKeys.some(sk => key.toLowerCase().includes(sk))) {
          obj[key] = '[REDACTED]';
        } else if (typeof obj[key] === 'object' && obj[key] !== null) {
          // Recursively sanitize nested objects
          this._sanitizeSensitiveInfo(obj[key]);
        }
      }
    }
  }
}
```

### 7.2 Example Usage

```javascript
// Initialize logger with context
const logger = new Logger({
  service: 'WhatsAppProcessingEngine',
  function_name: context.functionName,
  aws_request_id: context.awsRequestId,
  company_id: message.company_id,
  conversation_id: message.conversation_id
});

// Log different events
logger.info('Processing message', {
  message_type: message.type,
  recipient: message.recipient_tel
});

try {
  // Business logic...
} catch (error) {
  logger.error('Failed to process message', {
    error,
    message_id: message.id
  });
  throw error;
}

logger.info('Successfully processed message', {
  processing_time_ms: Date.now() - startTime,
  ai_tokens_used: response.tokens
});
```

## 8. CloudWatch Logs Insights

### 8.1 Common Queries

Predefined CloudWatch Logs Insights queries for operational analysis:

```
# Error frequency by category
fields @timestamp, message.error_category, message.error_message
| filter level = 'ERROR'
| stats count(*) as error_count by message.error_category
| sort error_count desc

# Processing time by company
fields @timestamp, message.company_id, message.processing_time_ms
| filter message.processing_time_ms > 0
| stats 
    avg(message.processing_time_ms) as avg_time_ms,
    percentile(message.processing_time_ms, 50) as p50_time_ms,
    percentile(message.processing_time_ms, 90) as p90_time_ms,
    percentile(message.processing_time_ms, 99) as p99_time_ms
  by message.company_id
| sort avg_time_ms desc

# OpenAI token usage
fields @timestamp, message.company_id, message.ai_tokens_used
| filter message.ai_tokens_used > 0
| stats 
    sum(message.ai_tokens_used) as total_tokens,
    avg(message.ai_tokens_used) as avg_tokens_per_request
  by message.company_id
| sort total_tokens desc

# Timeout identification
fields @timestamp, message
| filter message like /timeout/ or message.error_category = 'timeout'
| sort @timestamp desc
```

### 8.2 Log Retention and Exports

Logs are retained and exported for long-term analysis:

```javascript
// Set log retention
new logs.LogRetention(this, 'WhatsAppProcessingLogRetention', {
  logGroupName: '/aws/lambda/WhatsAppProcessingEngine',
  retention: logs.RetentionDays.ONE_MONTH
});

// Export logs to S3 for long-term storage
new logs.SubscriptionFilter(this, 'WhatsAppProcessingLogExport', {
  logGroup: logGroup,
  destination: new logs.LogDestination.LambdaDestination(exportLambda),
  filterPattern: logs.FilterPattern.allEvents()
});
```

## 9. Distributed Tracing

### 9.1 X-Ray Integration

AWS X-Ray is enabled for distributed tracing:

```javascript
// CDK configuration
const lambdaFunction = new lambda.Function(this, 'WhatsAppProcessingFunction', {
  // ... other configuration ...
  tracing: lambda.Tracing.ACTIVE  // Enables X-Ray tracing
});

// In the Lambda code
const AWSXRay = require('aws-xray-sdk');
const AWS = AWSXRay.captureAWS(require('aws-sdk'));

// Create subsegments for key operations
exports.handler = async (event) => {
  // Create custom subsegment for message processing
  const segment = AWSXRay.getSegment();
  const subsegment = segment.addNewSubsegment('ProcessMessage');
  
  try {
    // Process the message
    const result = await processMessage(event);
    
    // Add custom annotations to aid analysis
    subsegment.addAnnotation('CompanyId', event.company_id);
    subsegment.addAnnotation('MessageType', event.type);
    
    if (result.processing_time) {
      subsegment.addMetadata('ProcessingTime', result.processing_time);
    }
    
    subsegment.close();
    return result;
  } catch (error) {
    subsegment.addError(error);
    subsegment.close();
    throw error;
  }
};

// Custom subsegments for external API calls
async function callOpenAI() {
  const segment = AWSXRay.getSegment();
  const subsegment = segment.addNewSubsegment('OpenAIAPI');
  
  try {
    // Make OpenAI API call
    const result = await openaiClient.createCompletion({
      model: 'text-davinci-003',
      prompt: prompt
    });
    
    subsegment.addMetadata('TokensUsed', result.usage.total_tokens);
    subsegment.close();
    return result;
  } catch (error) {
    subsegment.addError(error);
    subsegment.close();
    throw error;
  }
}
```

### 9.2 Trace Analysis

X-Ray traces help identify performance bottlenecks:

1. **Service Maps**: Visualize dependencies between services
2. **Trace Timeline**: Analyze time spent in each component
3. **Error Correlation**: Link errors across distributed components
4. **Cold Start Analysis**: Identify Lambda cold starts

## 10. Business Metrics

In addition to operational metrics, the system tracks business-relevant metrics:

```javascript
// Track conversation metrics
await publishMetric(
  'ConversationCreated',
  1,
  { CompanyId: message.company_id, ProjectId: message.project_id },
  'Count'
);

// Track template usage
await publishMetric(
  'TemplateUsage',
  1,
  {
    CompanyId: message.company_id, 
    ProjectId: message.project_id,
    TemplateName: templateName
  },
  'Count'
);

// Track token usage costs
const tokenCost = calculateTokenCost(completionTokens, promptTokens);
await publishMetric(
  'TokenCost',
  tokenCost,
  { CompanyId: message.company_id, ProjectId: message.project_id },
  'None'  // Cost in USD
);
```

## 11. Operational Dashboard

A central operational dashboard combines metrics, logs, and traces:

1. **Service Health**: Overall system status indicators
2. **Performance Metrics**: Response times, queue depths, processing times
3. **Error Tracking**: Error rates and categories
4. **Business Metrics**: Message volumes, template usage, token consumption
5. **Resource Utilization**: Lambda concurrency, DynamoDB capacity

## 12. Implementing CloudWatch Alarms

The following provides implementation examples for key alarms:

### 12.1 Error Rate Alarm

```javascript
// CDK implementation for error rate alarm
const highErrorRateAlarm = new cloudwatch.Alarm(this, 'HighErrorRate', {
  metric: new cloudwatch.MathExpression({
    expression: 'errors / invocations * 100',
    usingMetrics: {
      errors: whatsappProcessingLambda.metricErrors(),
      invocations: whatsappProcessingLambda.metricInvocations()
    },
    period: cdk.Duration.minutes(5)
  }),
  threshold: 5,
  evaluationPeriods: 3,
  datapointsToAlarm: 3,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
  alarmDescription: 'High error rate in WhatsApp Processing Lambda'
});

highErrorRateAlarm.addAlarmAction(new cloudwatchActions.SnsAction(operationsAlarmTopic));
```

### 12.2 Assistant Configuration Issue Alarm

```javascript
// CDK implementation for assistant configuration issue alarm
const assistantConfigIssueAlarm = new cloudwatch.Alarm(this, 'AssistantConfigurationIssue', {
  metric: new cloudwatch.Metric({
    namespace: 'WhatsAppProcessingEngine',
    metricName: 'AssistantConfigurationIssue',
    statistic: 'Sum',
    period: cdk.Duration.minutes(5)
  }),
  threshold: 0,
  evaluationPeriods: 1,
  datapointsToAlarm: 1,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
  alarmDescription: 'OpenAI Assistant configuration issue detected'
});

// Add high-priority notification for immediate attention
assistantConfigIssueAlarm.addAlarmAction(new cloudwatchActions.SnsAction(highPriorityAlarmTopic));
```

### 12.3 DLQ Message Alarm

```javascript
// CDK implementation for DLQ message alarm
const dlqMessageAlarm = new cloudwatch.Alarm(this, 'DLQMessageCount', {
  metric: whatsappDLQ.metricApproximateNumberOfMessagesVisible(),
  threshold: 0,
  evaluationPeriods: 1,
  datapointsToAlarm: 1,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
  alarmDescription: 'Messages detected in WhatsApp Processing DLQ'
});

dlqMessageAlarm.addAlarmAction(new cloudwatchActions.SnsAction(operationsAlarmTopic));
```

### 12.4 Specific Assistant Configuration Issue Alarms

```javascript
// CDK implementation for specific assistant configuration issue alarms
const missingFunctionCallAlarm = new cloudwatch.Alarm(this, 'MissingFunctionCallIssue', {
  metric: new cloudwatch.Metric({
    namespace: 'WhatsAppProcessingEngine',
    metricName: 'AssistantConfigurationIssue',
    statistic: 'Sum',
    period: cdk.Duration.minutes(5),
    dimensions: {
      'IssueType': 'MissingFunctionCall'
    }
  }),
  threshold: 0,
  evaluationPeriods: 1,
  datapointsToAlarm: 1,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
  alarmDescription: 'OpenAI Assistant failed to call function when expected'
});

const unexpectedFunctionCallAlarm = new cloudwatch.Alarm(this, 'UnexpectedFunctionCallIssue', {
  metric: new cloudwatch.Metric({
    namespace: 'WhatsAppProcessingEngine',
    metricName: 'AssistantConfigurationIssue',
    statistic: 'Sum',
    period: cdk.Duration.minutes(5),
    dimensions: {
      'IssueType': 'UnexpectedFunctionCall'
    }
  }),
  threshold: 0,
  evaluationPeriods: 1,
  datapointsToAlarm: 1,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
  alarmDescription: 'OpenAI Assistant called additional functions after tool outputs'
});

// Add high-priority notifications for immediate attention
missingFunctionCallAlarm.addAlarmAction(new cloudwatchActions.SnsAction(highPriorityAlarmTopic));
unexpectedFunctionCallAlarm.addAlarmAction(new cloudwatchActions.SnsAction(highPriorityAlarmTopic));
```

## 13. Related Documentation

- [Overview and Architecture](./01-overview-architecture.md)
- [Error Handling Strategy](./08-error-handling-strategy.md)
- [Operations Playbook](./10-operations-playbook.md) 