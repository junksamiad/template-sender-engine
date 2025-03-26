# WhatsApp Processing Engine - Monitoring and Observability

> **Part 8 of 9 in the WhatsApp Processing Engine documentation series**

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

#### AI Response Analytics Widgets:

- **JSON Parser Performance**: Success rates and timings for parsing JSON from AI responses
- **Content Variables Validation**: Success rates for content variable validation with breakdowns by assistant
- **AI Response Structure Issues**: Counts of issues with AI response structure
- **Variable Types**: Analysis of variable types provided by the AI assistant

#### 5.1.3 Assistant Configuration Metrics

| Metric Name | Description | Dimensions | Statistics |
|-------------|-------------|------------|------------|
| `AssistantConfigurationIssue` | Count of assistant configuration issues | AssistantId, IssueType, ConversationId | Sum, Maximum |

The `IssueType` dimension can have the following values:
- `InvalidJSONResponse`: The assistant did not return valid JSON.
- `MissingContentVariables`: The assistant returned JSON without the required content_variables field.
- `EmptyContentVariables`: The assistant returned an empty content_variables object.

These metrics allow operational teams to quickly identify if there are issues with the AI assistant configuration that need to be addressed.

#### 5.1.4 JSON Parsing Error Metrics

| Metric Name | Description | Dimensions | Statistics |
|-------------|-------------|------------|------------|
| `JSONParsingError` | Count of JSON parsing errors | AssistantId, ErrorType, TemplateName | Sum, Maximum |
| `VariableValidationError` | Count of variable validation errors | AssistantId, TemplateName, VariableName | Sum, Maximum |

The `ErrorType` dimension for JSON parsing errors can have values like:
- `SyntaxError`: Invalid JSON syntax in the response.
- `MissingContentVariables`: JSON parsed but content_variables field is missing.
- `EmptyContentVariables`: content_variables object is empty.

These metrics help track issues with the JSON-based content variables approach.

## 6. Advanced Monitoring for OpenAI Integration

### 6.1 OpenAI Response Time Metrics

The system tracks detailed metrics for OpenAI API operations:

```javascript
/**
 * Records timing data for OpenAI API calls
 * @param {string} operation - API operation name
 * @param {number} durationMs - Duration in milliseconds
 * @param {object} dimensions - Additional dimensions
 */
async function recordOpenAITiming(operation, durationMs, dimensions) {
  try {
    await publishMetric(
      'OpenAICallDuration',
      durationMs,
      {
        Operation: operation,
        ...dimensions
      },
      'Milliseconds'
    );
    
    // Record appropriate percentiles for CloudWatch
    if (durationMs > 0) {
      // Track long-running operations specially
      if (durationMs > 5000) {
        await publishMetric(
          'LongRunningOpenAICall',
          1,
          {
            Operation: operation,
            DurationBucket: getLongRunningBucket(durationMs)
          },
          'Count'
        );
      }
    }
  } catch (error) {
    console.error('Failed to record OpenAI timing metric', error);
    // Non-blocking - continue processing
  }
}

/**
 * Gets bucket for long-running operations
 * @param {number} durationMs - Duration in milliseconds
 * @returns {string} - Bucket identifier
 */
function getLongRunningBucket(durationMs) {
  if (durationMs < 10000) return '5s-10s';
  if (durationMs < 30000) return '10s-30s';
  if (durationMs < 60000) return '30s-60s';
  return '60s+';
}

/**
 * Wrapper function to time OpenAI operations
 * @param {Function} func - Function to wrap
 * @param {string} operationName - Name of operation
 * @param {object} dimensions - Additional dimensions
 * @returns {Function} - Wrapped function
 */
function withOpenAITiming(func, operationName, dimensions = {}) {
  return async (...args) => {
    const startTime = Date.now();
    try {
      const result = await func(...args);
      const duration = Date.now() - startTime;
      await recordOpenAITiming(operationName, duration, dimensions);
      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      await recordOpenAITiming(`${operationName}_error`, duration, dimensions);
      throw error;
    }
  };
}

// Example usage
const createThreadWithTiming = withOpenAITiming(
  openai.beta.threads.create,
  'CreateThread',
  { CompanyId: contextObject.company_id }
);

const threadResponse = await createThreadWithTiming();
```

### 6.2 Request Correlation with X-Ray

The system implements AWS X-Ray for distributed tracing:

```javascript
// Initialize X-Ray
const AWSXRay = require('aws-xray-sdk');
const AWS = AWSXRay.captureAWS(require('aws-sdk'));

// Create subsegments for key operations
exports.handler = async (event, context) => {
  // Create a segment for the entire processing flow
  const segment = AWSXRay.getSegment();
  
  // Parse the message
  const subsegment = segment.addNewSubsegment('ParseMessage');
  try {
    const message = JSON.parse(event.Records[0].body);
    subsegment.addAnnotation('company_id', message.company_id);
    subsegment.addAnnotation('project_id', message.project_id);
    subsegment.close();
  } catch (error) {
    subsegment.addError(error);
    subsegment.close();
    throw error;
  }
  
  // Create OpenAI thread subsegment
  const openAISubsegment = segment.addNewSubsegment('OpenAI_CreateThread');
  try {
    // ... OpenAI thread creation logic ...
    openAISubsegment.addAnnotation('thread_id', thread.id);
    openAISubsegment.close();
  } catch (error) {
    openAISubsegment.addError(error);
    openAISubsegment.close();
    throw error;
  }
  
  // Additional processing subsegments...
};
```

### 6.3 Request Correlation IDs

The WhatsApp Processing Engine implements a request correlation system to track requests through all components:

```javascript
/**
 * Generates a correlation ID for tracking requests
 * @returns {string} - Unique correlation ID
 */
function generateCorrelationId() {
  return `cor_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
}

/**
 * Adds correlation ID to logs
 * @param {object} logger - Logger instance
 * @param {string} correlationId - Correlation ID
 * @returns {object} - Enhanced logger
 */
function enhanceLoggerWithCorrelation(logger, correlationId) {
  // Create a wrapper around the logger methods
  return {
    log: (message, params = {}) => {
      logger.log(message, { ...params, correlation_id: correlationId });
    },
    info: (message, params = {}) => {
      logger.info(message, { ...params, correlation_id: correlationId });
    },
    warn: (message, params = {}) => {
      logger.warn(message, { ...params, correlation_id: correlationId });
    },
    error: (message, params = {}) => {
      logger.error(message, { ...params, correlation_id: correlationId });
    }
  };
}

// Example usage in the Lambda handler
exports.handler = async (event, context) => {
  // Generate correlation ID for this request
  const correlationId = generateCorrelationId();
  
  // Enhance the logger
  const logger = enhanceLoggerWithCorrelation(console, correlationId);
  
  // Log the start of processing
  logger.info('Starting WhatsApp processing', {
    event_source: event.Records[0].eventSource,
    aws_request_id: context.awsRequestId
  });
  
  try {
    // Process message with correlation ID
    const result = await processMessage(event.Records[0], {
      logger,
      correlationId
    });
    
    // Log successful completion
    logger.info('WhatsApp processing completed successfully', {
      result_summary: {
        conversation_id: result.conversationId,
        processing_time_ms: result.processingTimeMs
      }
    });
    
    return result;
  } catch (error) {
    // Log failure with correlation ID
    logger.error('WhatsApp processing failed', {
      error_message: error.message,
      error_stack: error.stack
    });
    
    throw error;
  }
};

/**
 * Process the WhatsApp message
 * @param {object} record - SQS record
 * @param {object} options - Processing options
 * @returns {Promise<object>} - Processing result
 */
async function processMessage(record, { logger, correlationId }) {
  // Parse the message
  const message = JSON.parse(record.body);
  
  // Create enhanced context with correlation ID
  const enhancedMessage = {
    ...message,
    metadata: {
      ...message.metadata,
      correlation_id: correlationId
    }
  };
  
  // Log key processing steps with consistent correlation ID
  logger.info('Parsed SQS message', {
    company_id: enhancedMessage.company_id,
    project_id: enhancedMessage.project_id,
    request_id: enhancedMessage.request_id
  });
  
  // Process with consistent correlation ID
  const result = await doProcessing(enhancedMessage, logger);
  
  // Return result with correlation ID included
  return {
    ...result,
    correlationId
  };
}
```

### 6.4 Custom CloudWatch Metrics for AI

The system implements custom CloudWatch metrics specifically for AI processing:

```javascript
/**
 * Publishes AI-specific metrics to CloudWatch
 * @param {object} contextObject - Context object
 * @param {object} metrics - AI metrics object
 */
async function publishAIMetrics(contextObject, metrics) {
  const baseMetricDimensions = {
    CompanyId: contextObject.company_data.company_id,
    ProjectId: contextObject.company_data.project_id,
    AssistantId: contextObject.ai_config.assistant_id_template_sender
  };
  
  // Token usage metrics
  if (metrics.tokens) {
    await publishMetric(
      'PromptTokenUsage',
      metrics.tokens.prompt_tokens || 0,
      baseMetricDimensions,
      'Count'
    );
    
    await publishMetric(
      'CompletionTokenUsage',
      metrics.tokens.completion_tokens || 0,
      baseMetricDimensions,
      'Count'
    );
    
    await publishMetric(
      'TotalTokenUsage',
      metrics.tokens.total_tokens || 0,
      baseMetricDimensions,
      'Count'
    );
  }
  
  // Response time metrics
  if (metrics.timing) {
    await publishMetric(
      'AIResponseTime',
      metrics.timing.total_time_ms || 0,
      baseMetricDimensions,
      'Milliseconds'
    );
    
    await publishMetric(
      'ThreadCreationTime',
      metrics.timing.thread_creation_ms || 0,
      baseMetricDimensions,
      'Milliseconds'
    );
    
    await publishMetric(
      'RunCreationTime',
      metrics.timing.run_creation_ms || 0,
      baseMetricDimensions,
      'Milliseconds'
    );
    
    await publishMetric(
      'RunCompletionTime',
      metrics.timing.run_completion_ms || 0,
      baseMetricDimensions,
      'Milliseconds'
    );
  }
  
  // Structured data validation metrics
  if (metrics.validation) {
    await publishMetric(
      'JSONParsingSuccess',
      metrics.validation.json_parsing_success ? 1 : 0,
      baseMetricDimensions,
      'None'
    );
    
    await publishMetric(
      'ContentVariablesSuccess',
      metrics.validation.content_variables_success ? 1 : 0,
      baseMetricDimensions,
      'None'
    );
    
    if (metrics.validation.variable_count !== undefined) {
      await publishMetric(
        'ContentVariableCount',
        metrics.validation.variable_count,
        baseMetricDimensions,
        'Count'
      );
    }
  }
  
  // Cost metrics
  if (metrics.cost) {
    await publishMetric(
      'EstimatedCost',
      metrics.cost.estimated_cost_usd || 0,
      baseMetricDimensions,
      'None'
    );
  }
}

/**
 * Calculates token cost for monitoring
 * @param {number} completionTokens - Completion tokens used
 * @param {number} promptTokens - Prompt tokens used
 * @returns {number} - Estimated cost in USD
 */
function calculateTokenCost(completionTokens, promptTokens) {
  // GPT-4 Turbo pricing (as of early 2023) - update as needed
  const PROMPT_COST_PER_1K = 0.01;  // $0.01 per 1K tokens
  const COMPLETION_COST_PER_1K = 0.03;  // $0.03 per 1K tokens
  
  const promptCost = (promptTokens / 1000) * PROMPT_COST_PER_1K;
  const completionCost = (completionTokens / 1000) * COMPLETION_COST_PER_1K;
  
  return promptCost + completionCost;
}

// Example usage
const metrics = {
  tokens: {
    prompt_tokens: 250,
    completion_tokens: 50,
    total_tokens: 300
  },
  timing: {
    total_time_ms: 3500,
    thread_creation_ms: 350,
    run_creation_ms: 300,
    run_completion_ms: 2850
  },
  validation: {
    json_parsing_success: true,
    content_variables_success: true,
    variable_count: 5
  },
  cost: {
    estimated_cost_usd: calculateTokenCost(50, 250)
  }
};

await publishAIMetrics(contextObject, metrics);
```

### 6.5 CloudWatch Logs Insights Queries

The system provides pre-configured CloudWatch Logs Insights queries for analyzing AI performance:

#### AI Response Time Analysis

```
fields @timestamp, @message, correlation_id, company_id, 
       ai_response_time_ms, thread_id, run_id
| filter ai_response_time_ms > 0
| sort ai_response_time_ms desc
| limit 100
```

#### AI Processing Errors

```
fields @timestamp, correlation_id, company_id, error_category, error_message
| filter message like /openai/ and error_category not null
| stats count(*) as error_count by error_category, company_id
| sort error_count desc
```

#### AI Token Usage by Company

```
fields @timestamp, correlation_id, company_id, prompt_tokens, completion_tokens, total_tokens
| filter total_tokens > 0
| stats 
    sum(prompt_tokens) as total_prompt_tokens,
    sum(completion_tokens) as total_completion_tokens,
    sum(total_tokens) as total_tokens,
    avg(total_tokens) as avg_tokens_per_request
  by company_id
| sort total_tokens desc
```

## 7. CloudWatch Dashboards

The system includes pre-configured CloudWatch dashboards for monitoring:

### 7.1 Main Operational Dashboard

The main dashboard provides a holistic view of the system:

![Main Dashboard](../../diagrams/monitoring-main-dashboard.png)

#### Widgets:
- **System Health**: Error rates, DLQ message counts, system uptime
- **Performance Metrics**: Processing times, API latencies, queue depths
- **Message Flow**: Messages processed per minute, success rates, failure rates
- **External Dependencies**: OpenAI and Twilio API health and performance

### 7.2 WhatsApp Processing Dashboard

This dashboard focuses specifically on WhatsApp processing:

![WhatsApp Dashboard](../../diagrams/monitoring-whatsapp-dashboard.png)

#### Widgets:
- **Message Processing**: Volumes, success rates, processing times
- **OpenAI Integration**: Thread creation, run times, token usage
- **Function Execution**: Execution counts, durations, success rates
- **Twilio Integration**: Message sending latency, delivery rates
- **Assistant Configuration Issues**: Configuration errors by type and assistant

### 7.3 Error Investigation Dashboard

This dashboard aids in diagnosing and resolving errors:

![Error Dashboard](../../diagrams/monitoring-error-dashboard.png)

#### Widgets:
- **DLQ Message Counts**: By queue and error type
- **Error Rates**: Breakdowns by category and source
- **Error Timelines**: Error occurrence patterns
- **Retry Statistics**: Success rates after retries
- **Assistant Configuration Issues**: Detailed breakdown with conversation and assistant IDs

#### AI Response Analytics Widgets:

- **JSON Parser Performance**: Success rates and timings for parsing JSON from AI responses
- **Content Variables Validation**: Success rates for content variable validation with breakdowns by assistant
- **AI Response Structure Issues**: Counts of issues with AI response structure
- **Variable Types**: Analysis of variable types provided by the AI assistant

#### 7.1.3 Assistant Configuration Metrics

| Metric Name | Description | Dimensions | Statistics |
|-------------|-------------|------------|------------|
| `AssistantConfigurationIssue` | Count of assistant configuration issues | AssistantId, IssueType, ConversationId | Sum, Maximum |

The `IssueType` dimension can have the following values:
- `InvalidJSONResponse`: The assistant did not return valid JSON.
- `MissingContentVariables`: The assistant returned JSON without the required content_variables field.
- `EmptyContentVariables`: The assistant returned an empty content_variables object.

These metrics allow operational teams to quickly identify if there are issues with the AI assistant configuration that need to be addressed.

#### 7.1.4 JSON Parsing Error Metrics

| Metric Name | Description | Dimensions | Statistics |
|-------------|-------------|------------|------------|
| `JSONParsingError` | Count of JSON parsing errors | AssistantId, ErrorType, TemplateName | Sum, Maximum |
| `VariableValidationError` | Count of variable validation errors | AssistantId, TemplateName, VariableName | Sum, Maximum |

The `ErrorType` dimension for JSON parsing errors can have values like:
- `SyntaxError`: Invalid JSON syntax in the response.
- `MissingContentVariables`: JSON parsed but content_variables field is missing.
- `EmptyContentVariables`: content_variables object is empty.

These metrics help track issues with the JSON-based content variables approach.

## 8. CloudWatch Alarms

The system includes the following alarms for critical conditions:

### 8.1 Critical Alarms

| Alarm Name | Condition | Threshold | Period | Evaluation Periods | Actions |
|------------|-----------|-----------|--------|-------------------|---------|
| HighErrorRate | Error rate exceeds threshold | >5% | 5 minutes | 3 | SNS notification to operations team |
| DLQMessageCount | Messages in DLQ | >0 | 5 minutes | 1 | SNS notification to operations team |
| APITimeout | OpenAI API timeouts | >3 | 15 minutes | 1 | SNS notification to operations team |
| HighLatency | Processing time | >30 seconds | 5 minutes | 3 | SNS notification to operations team |
| AssistantConfigurationIssues | Configuration errors detected | >0 | 5 minutes | 1 | SNS notification to operations team |

### 8.2 Warning Alarms

| Alarm Name | Condition | Threshold | Period | Evaluation Periods | Actions |
|------------|-----------|-----------|--------|-------------------|---------|
| ElevatedErrorRate | Error rate exceeds threshold | >2% | 15 minutes | 3 | Email to development team |
| HighTokenUsage | Token usage spike | >200% of baseline | 1 hour | 1 | Email to development team |
| IncreasedLatency | Processing time | >15 seconds | 15 minutes | 3 | Email to development team |
| OpenAIRateLimiting | Rate limit errors | >0 | 15 minutes | 3 | Email to development team |

### 8.3 Assistant Configuration Issue Alarms

| Alarm Name | Condition | Threshold | Period | Evaluation Periods | Actions |
|------------|-----------|-----------|--------|-------------------|---------|
| MissingStructuredJSONResponseIssue | Missing structured JSON response errors | >0 | 5 minutes | 1 | SNS high-priority notification |
| MalformedJSONResponseIssue | Malformed JSON response errors | >0 | 5 minutes | 1 | SNS high-priority notification |
| RecurringConfigurationIssues | Configuration issues on same assistant | >3 | 1 hour | 1 | SNS + ticketing system |

## 9. Structured Logging

### 9.1 Log Format

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

### 9.2 Example Usage

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

## 10. CloudWatch Logs Insights

### 10.1 Common Queries

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

### 10.2 Log Retention and Exports

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

## 11. Distributed Tracing

### 11.1 X-Ray Integration

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

### 11.2 Trace Analysis

X-Ray traces help identify performance bottlenecks:

1. **Service Maps**: Visualize dependencies between services
2. **Trace Timeline**: Analyze time spent in each component
3. **Error Correlation**: Link errors across distributed components
4. **Cold Start Analysis**: Identify Lambda cold starts

## 12. Business Metrics

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

## 13. Operational Dashboard

A central operational dashboard combines metrics, logs, and traces:

1. **Service Health**: Overall system status indicators
2. **Performance Metrics**: Response times, queue depths, processing times
3. **Error Tracking**: Error rates and categories
4. **Business Metrics**: Message volumes, template usage, token consumption
5. **Resource Utilization**: Lambda concurrency, DynamoDB capacity

## 14. Implementing CloudWatch Alarms

The following provides implementation examples for key alarms:

### 14.1 Error Rate Alarm

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

### 14.2 Assistant Configuration Issue Alarm

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

### 14.3 DLQ Message Alarm

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

### 14.4 Specific Assistant Configuration Issue Alarms

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

## 15. Related Documentation

- [Overview and Architecture](./01-overview-architecture.md)
- [Error Handling Strategy](./08-error-handling-strategy.md)
- [Operations Playbook](./10-operations-playbook.md) 