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

## 4. Custom Metrics Dashboard

A custom CloudWatch dashboard provides a holistic view of the system:

```javascript
// CDK code to create dashboard
const dashboard = new cloudwatch.Dashboard(this, 'WhatsAppProcessingDashboard', {
  dashboardName: 'WhatsAppProcessingEngine-Metrics'
});

// Add widgets
dashboard.addWidgets(
  new cloudwatch.GraphWidget({
    title: 'Message Processing Volume',
    left: [
      new cloudwatch.Metric({
        namespace: 'ChannelRouter/WhatsAppProcessingEngine',
        metricName: 'MessageVolume',
        statistic: 'Sum',
        dimensions: { Status: 'received' },
        period: Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'ChannelRouter/WhatsAppProcessingEngine',
        metricName: 'MessageVolume',
        statistic: 'Sum',
        dimensions: { Status: 'processed' },
        period: Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'ChannelRouter/WhatsAppProcessingEngine',
        metricName: 'MessageVolume',
        statistic: 'Sum',
        dimensions: { Status: 'failed' },
        period: Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  }),
  
  new cloudwatch.GraphWidget({
    title: 'Message Processing Time',
    left: [
      new cloudwatch.Metric({
        namespace: 'ChannelRouter/WhatsAppProcessingEngine',
        metricName: 'MessageProcessingTime',
        statistic: 'p50',
        period: Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'ChannelRouter/WhatsAppProcessingEngine',
        metricName: 'MessageProcessingTime',
        statistic: 'p90',
        period: Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'ChannelRouter/WhatsAppProcessingEngine',
        metricName: 'MessageProcessingTime',
        statistic: 'p99',
        period: Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  })
);
```

## 5. Alarms and Alerting

### 5.1 Operational Alarms

Alarms are configured to alert on operational issues:

```javascript
// Example alarms
const highErrorRateAlarm = new cloudwatch.Alarm(this, 'HighErrorRateAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'ChannelRouter/WhatsAppProcessingEngine',
    metricName: 'MessageVolume',
    dimensions: { Status: 'failed' },
    statistic: 'Sum',
    period: Duration.minutes(5)
  }),
  evaluationPeriods: 1,
  threshold: 5, // More than 5 failures in 5 minutes
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
  actionsEnabled: true
});

const dlqMessagesAlarm = new cloudwatch.Alarm(this, 'DLQMessagesAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'AWS/SQS',
    metricName: 'ApproximateNumberOfMessagesVisible',
    dimensions: { QueueName: this.dlq.queueName },
    statistic: 'Maximum',
    period: Duration.minutes(5)
  }),
  evaluationPeriods: 1,
  threshold: 1, // Any message in DLQ
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
  actionsEnabled: true
});

// Add notification actions to alarms
const alertTopic = new sns.Topic(this, 'WhatsAppProcessingAlertTopic');
highErrorRateAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));
dlqMessagesAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));
```

### 5.2 Business Metrics Alarms

Alarms for business-relevant thresholds:

```javascript
// Alert on high token usage
const highTokenUsageAlarm = new cloudwatch.Alarm(this, 'HighTokenUsageAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'ChannelRouter/WhatsAppProcessingEngine',
    metricName: 'TokenUsage',
    dimensions: { TokenType: 'Total' },
    statistic: 'Sum',
    period: Duration.hours(24)
  }),
  evaluationPeriods: 1,
  threshold: 1000000, // 1 million tokens per day
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
});

// Alert on processing delays
const processingDelayAlarm = new cloudwatch.Alarm(this, 'ProcessingDelayAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'ChannelRouter/WhatsAppProcessingEngine',
    metricName: 'MessageProcessingTime',
    statistic: 'p95',
    period: Duration.minutes(15)
  }),
  evaluationPeriods: 3,
  threshold: 30000, // 30 seconds at p95
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
});
```

## 6. Structured Logging

### 6.1 Log Format

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

### 6.2 Example Usage

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

## 7. CloudWatch Logs Insights

### 7.1 Common Queries

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

### 7.2 Log Retention and Exports

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

## 8. Distributed Tracing

### 8.1 X-Ray Integration

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

### 8.2 Trace Analysis

X-Ray traces help identify performance bottlenecks:

1. **Service Maps**: Visualize dependencies between services
2. **Trace Timeline**: Analyze time spent in each component
3. **Error Correlation**: Link errors across distributed components
4. **Cold Start Analysis**: Identify Lambda cold starts

## 9. Business Metrics

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

## 10. Operational Dashboard

A central operational dashboard combines metrics, logs, and traces:

1. **Service Health**: Overall system status indicators
2. **Performance Metrics**: Response times, queue depths, processing times
3. **Error Tracking**: Error rates and categories
4. **Business Metrics**: Message volumes, template usage, token consumption
5. **Resource Utilization**: Lambda concurrency, DynamoDB capacity

## 11. Related Documentation

- [Overview and Architecture](./01-overview-architecture.md)
- [Error Handling Strategy](./08-error-handling-strategy.md)
- [Operations Playbook](./10-operations-playbook.md) 