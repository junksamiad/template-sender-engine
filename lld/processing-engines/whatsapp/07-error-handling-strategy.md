# WhatsApp Processing Engine - Error Handling Strategy

> **Part 7 of 9 in the WhatsApp Processing Engine documentation series**

## 1. Introduction

This document details the comprehensive error handling strategy implemented in the WhatsApp Processing Engine. The system is designed to be resilient and fault-tolerant, with a multi-tiered approach to error handling that ensures robustness in production environments.

## 2. Error Handling Architecture

The error handling architecture follows these key principles:

1. **Categorization**: Errors are categorized by type, source, and severity
2. **Isolation**: Errors are isolated to prevent cascading failures
3. **Recovery**: Automated recovery mechanisms are implemented where possible
4. **Visibility**: Errors are logged with appropriate detail for debugging
5. **Notification**: Critical errors trigger alerts to operations teams

## 3. Error Categories

Errors are categorized into the following types:

### 3.1 Transient Errors

Temporary failures that may resolve automatically with retries:

| Error Type | Examples | Handling Strategy |
|------------|----------|-------------------|
| Network Errors | Connection timeouts, temporary disconnects | Exponential backoff retry |
| Service Throttling | API rate limits (AWS, OpenAI, Twilio) | Retry with backoff, circuit breaking |
| Resource Contention | Database contention, Lambda concurrency | Retry with jitter |

### 3.2 Permanent Errors

Failures that will not resolve with retries alone:

| Error Type | Examples | Handling Strategy |
|------------|----------|-------------------|
| Authentication | Invalid credentials, expired tokens | Fail immediately, alert operations |
| Authorization | Insufficient permissions | Fail immediately, log details |
| Resource Not Found | Missing DynamoDB records, templates | Fail operation, record specific error |
| Validation | Invalid input, schema violations | Fail operation, return specific error |

### 3.3 System Errors

Failures in the system's infrastructure:

| Error Type | Examples | Handling Strategy |
|------------|----------|-------------------|
| Lambda Failures | Out of memory, timeout | Use SQS DLQ, monitor CloudWatch |
| Database Failures | DynamoDB unavailable, capacity exceeded | Circuit breaker, fallback patterns |
| Dependency Failures | AWS services unavailable | Graceful degradation |

### 3.4 Integration Errors

Failures in integrated third-party services:

| Error Type | Examples | Handling Strategy |
|------------|----------|-------------------|
| OpenAI Errors | API errors, rate limits, invalid responses | Categorize, retry with backoff |
| Twilio Errors | Messaging failures, template rejections | Record in DynamoDB, alert if critical |

### 3.3 OpenAI Integration Errors

| Error Type | Error Code | Description | Retry Strategy | Example |
|------------|------------|-------------|----------------|---------|
| Authentication | OPENAI_AUTH_ERROR | API key is invalid or revoked | No retry, send to DLQ | "Invalid API key" |
| Rate Limiting | OPENAI_RATE_LIMIT | API rate limit exceeded | Retry with backoff | "Rate limit exceeded" |
| Timeout | OPENAI_TIMEOUT | API request timed out | Retry with backoff | "Request timed out" |
| Server Error | OPENAI_SERVER_ERROR | 5xx server error from OpenAI | Retry with backoff | "Internal server error" |
| Invalid Request | OPENAI_INVALID_REQUEST | Invalid request format or parameters | No retry, send to DLQ | "Invalid request parameters" |
| JSON Parsing Error | OPENAI_JSON_PARSE_ERROR | Failed to parse JSON from assistant response | No retry, send to DLQ | "Failed to parse JSON: Unexpected token at line 2" |
| Missing Variables | OPENAI_MISSING_VARIABLES | JSON response missing required content variables | No retry, send to DLQ | "Missing content_variables in assistant response" |

In addition to standard API errors, the system tracks and handles specific OpenAI assistant configuration issues:

| Error Code | Description | Handling Strategy |
|------------|-------------|-------------------|
| INVALID_JSON_RESPONSE | Assistant did not return valid JSON | 1. Log detailed error with message content<br>2. Emit CloudWatch metric<br>3. Send to DLQ |
| MISSING_CONTENT_VARIABLES | Assistant returned JSON without content_variables | 1. Log detailed error with parsed response<br>2. Emit CloudWatch metric<br>3. Send to DLQ |
| EMPTY_CONTENT_VARIABLES | Assistant returned empty content_variables object | 1. Log detailed error<br>2. Emit CloudWatch metric<br>3. Send to DLQ |

## 4. Implementation of Error Handling

### 4.1 Try-Catch Pattern

All operations use try-catch blocks with appropriate error handling:

```javascript
/**
 * Example of try-catch pattern in a Lambda function
 */
exports.handler = async (event) => {
  try {
    // Process messages
    const result = await processMessages(event);
    
    // Return success response
    return {
      statusCode: 200,
      body: JSON.stringify(result)
    };
  } catch (error) {
    // Log the error with context for debugging
    console.error('Error processing message:', {
      error_message: error.message,
      error_name: error.name,
      error_stack: error.stack,
      error_code: error.code || 'unknown',
      event_source: event.source
    });
    
    // Categorize error for response handling
    const errorCategory = categorizeError(error);
    
    // Determine if operation should be retried
    const shouldRetry = isRetryableError(error);
    
    // If Lambda invoked by SQS and error is retryable, throw to trigger retry
    if (event.Records && event.Records[0]?.eventSource === 'aws:sqs' && shouldRetry) {
      throw error; // SQS will retry based on queue settings
    }
    
    // Handle API Gateway responses
    if (event.httpMethod) {
      return {
        statusCode: getStatusCodeForError(error),
        body: JSON.stringify({
          error: true,
          message: getSanitizedErrorMessage(error),
          code: errorCategory
        })
      };
    }
    
    // Default error response
    throw error;
  }
};
```

### 4.2 Error Categorization

Errors are categorized to enable appropriate handling:

```javascript
/**
 * Categorizes an error by examining properties
 * @param {Error} error - The error to categorize
 * @returns {string} - Error category
 */
function categorizeError(error) {
  if (!error) return 'unknown';
  
  // Check for specific error types
  if (error.name === 'TimeoutError' || error.message.includes('timed out')) {
    return 'timeout';
  }
  
  if (error.code === 'ThrottlingException' || error.status === 429) {
    return 'throttling';
  }
  
  if (error.code === 'ValidationException' || error.name === 'ValidationError') {
    return 'validation';
  }
  
  if (error.code === 'ResourceNotFoundException' || error.status === 404) {
    return 'not_found';
  }
  
  if (error.code === 'ConditionalCheckFailedException') {
    return 'condition_check_failed';
  }
  
  if (error.code === 'AccessDeniedException' || error.status === 403) {
    return 'access_denied';
  }
  
  if (error.code === 'UnauthorizedException' || error.status === 401) {
    return 'unauthorized';
  }
  
  if (error.code === 'InternalServerError' || error.status === 500) {
    return 'server_error';
  }
  
  // Default to generic error category
  return 'application_error';
}
```

### 4.3 Retry Strategy

The system implements a robust retry strategy with exponential backoff:

```javascript
/**
 * Executes a function with retry logic
 * @param {Function} fn - Function to execute
 * @param {Array} args - Arguments to pass to the function
 * @param {object} options - Retry options
 * @returns {Promise<any>} - Result from the function
 */
async function withRetry(fn, args = [], options = {}) {
  const {
    maxRetries = 3,
    initialDelayMs = 1000,
    maxDelayMs = 10000,
    retryableErrors = ['throttling', 'timeout', 'server_error']
  } = options;
  
  let attempt = 0;
  
  while (true) {
    try {
      return await fn(...args);
    } catch (error) {
      attempt++;
      
      // Categorize the error
      const errorCategory = categorizeError(error);
      
      // Check if we should retry
      const shouldRetry = retryableErrors.includes(errorCategory) && attempt < maxRetries;
      
      // Log the error and retry info
      console.log('Operation error', {
        error_message: error.message,
        error_category: errorCategory,
        retry_attempt: attempt,
        will_retry: shouldRetry
      });
      
      if (shouldRetry) {
        // Calculate backoff with jitter
        const backoff = Math.min(
          initialDelayMs * Math.pow(2, attempt - 1),
          maxDelayMs
        );
        const jitter = backoff * 0.2 * (Math.random() - 0.5);
        const delay = Math.floor(backoff + jitter);
        
        console.log(`Retrying after ${delay}ms (attempt ${attempt}/${maxRetries})`);
        
        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, delay));
      } else {
        // Rethrow if no more retries
        throw error;
      }
    }
  }
}
```

### 4.4 Circuit Breaker Pattern

For external services, the system implements a circuit breaker pattern:

```javascript
/**
 * Circuit breaker implementation for external service calls
 */
class CircuitBreaker {
  constructor(options = {}) {
    this.options = {
      failureThreshold: 5, // Number of failures before opening circuit
      resetTimeout: 30000, // Time to wait before trying again (30 seconds)
      monitorInterval: 5000, // Check circuit status every 5 seconds
      ...options
    };
    
    this.state = {
      status: 'CLOSED', // CLOSED, OPEN, HALF_OPEN
      failures: 0,
      lastFailure: null,
      lastSuccess: null
    };
    
    // Start monitoring
    this.startMonitoring();
  }
  
  /**
   * Execute a function with circuit breaker protection
   * @param {Function} fn - Function to execute
   * @param {Array} args - Arguments to pass to the function
   * @returns {Promise<any>} - Result from the function
   */
  async execute(fn, ...args) {
    // Check if circuit is open
    if (this.state.status === 'OPEN') {
      const timeSinceLastFailure = Date.now() - this.state.lastFailure;
      
      // Circuit is open, throw exception
      if (timeSinceLastFailure < this.options.resetTimeout) {
        throw new Error('Circuit is OPEN, service unavailable');
      }
      
      // Reset timeout has elapsed, try again in HALF_OPEN state
      this.state.status = 'HALF_OPEN';
      console.log('Circuit changed to HALF_OPEN state');
    }
    
    try {
      // Execute the function
      const result = await fn(...args);
      
      // Reset on success if in HALF_OPEN state
      if (this.state.status === 'HALF_OPEN') {
        this.reset();
      }
      
      // Update last success timestamp
      this.state.lastSuccess = Date.now();
      
      return result;
    } catch (error) {
      // Record failure
      this.recordFailure();
      
      // Check if circuit should be opened
      if (this.state.status === 'CLOSED' && 
          this.state.failures >= this.options.failureThreshold) {
        this.state.status = 'OPEN';
        this.state.lastFailure = Date.now();
        console.log('Circuit OPENED due to too many failures');
      }
      
      throw error;
    }
  }
  
  /**
   * Record a failure
   */
  recordFailure() {
    this.state.failures++;
    this.state.lastFailure = Date.now();
  }
  
  /**
   * Reset the circuit breaker
   */
  reset() {
    this.state.status = 'CLOSED';
    this.state.failures = 0;
    console.log('Circuit RESET to CLOSED state');
  }
  
  /**
   * Start monitoring circuit state
   */
  startMonitoring() {
    setInterval(() => {
      // Check if circuit has been open for longer than resetTimeout
      if (this.state.status === 'OPEN') {
        const timeSinceLastFailure = Date.now() - this.state.lastFailure;
        
        if (timeSinceLastFailure >= this.options.resetTimeout) {
          this.state.status = 'HALF_OPEN';
          console.log('Circuit changed to HALF_OPEN state (monitoring)');
        }
      }
      
      // Log current state for monitoring
      console.log('Circuit state:', {
        status: this.state.status,
        failures: this.state.failures,
        last_failure: this.state.lastFailure 
          ? new Date(this.state.lastFailure).toISOString() 
          : null
      });
    }, this.options.monitorInterval);
  }
}

// Example usage
const openAICircuitBreaker = new CircuitBreaker();

// Using the circuit breaker
try {
  const result = await openAICircuitBreaker.execute(
    processWithOpenAI, openai, contextObject
  );
  return result;
} catch (error) {
  console.error('OpenAI processing failed with circuit breaker:', error);
  throw error;
}
```

## 5. Error Logging and Monitoring

### 5.1 Structured Logging

All errors are logged using a structured format for better analysis:

```javascript
/**
 * Logs an error with structured context
 * @param {Error} error - The error to log
 * @param {object} context - Additional context information
 */
function logError(error, context = {}) {
  console.error('Error:', {
    message: error.message,
    stack: error.stack,
    code: error.code || 'unknown',
    status: error.status,
    category: categorizeError(error),
    context: sanitizeContext(context)
  });
}

/**
 * Sanitizes context to remove sensitive information
 * @param {object} context - Context object
 * @returns {object} - Sanitized context
 */
function sanitizeContext(context) {
  const sanitized = { ...context };
  
  // Remove sensitive fields
  const sensitiveFields = [
    'api_key', 'auth_token', 'password', 'secret',
    'credential', 'token', 'key'
  ];
  
  // Recursive sanitization
  function sanitizeObject(obj) {
    if (!obj || typeof obj !== 'object') return obj;
    
    // Handle arrays
    if (Array.isArray(obj)) {
      return obj.map(item => sanitizeObject(item));
    }
    
    // Handle objects
    const result = {};
    for (const [key, value] of Object.entries(obj)) {
      // Check for sensitive field
      const isSensitive = sensitiveFields.some(field => 
        key.toLowerCase().includes(field)
      );
      
      if (isSensitive) {
        result[key] = '[REDACTED]';
      } else if (typeof value === 'object' && value !== null) {
        result[key] = sanitizeObject(value);
      } else {
        result[key] = value;
      }
    }
    
    return result;
  }
  
  return sanitizeObject(sanitized);
}
```

### 5.2 CloudWatch Metrics

Key error metrics are published to CloudWatch for monitoring:

```javascript
/**
 * Publishes error metrics to CloudWatch
 * @param {string} errorCategory - Error category
 * @param {object} context - Additional context
 */
async function publishErrorMetrics(errorCategory, context = {}) {
  try {
    const cloudwatch = new AWS.CloudWatch();
    
    const metricData = [
      {
        MetricName: 'Errors',
        Dimensions: [
          {
            Name: 'Service',
            Value: 'WhatsAppProcessingEngine'
          },
          {
            Name: 'ErrorCategory',
            Value: errorCategory
          }
        ],
        Unit: 'Count',
        Value: 1
      }
    ];
    
    // Add specific metrics for service errors
    if (context.service) {
      metricData.push({
        MetricName: 'ServiceErrors',
        Dimensions: [
          {
            Name: 'Service',
            Value: 'WhatsAppProcessingEngine'
          },
          {
            Name: 'ExternalService',
            Value: context.service
          }
        ],
        Unit: 'Count',
        Value: 1
      });
    }
    
    await cloudwatch.putMetricData({
      Namespace: 'ChannelRouter',
      MetricData: metricData
    }).promise();
  } catch (metricError) {
    // Don't fail the main process for metrics errors
    console.error('Failed to publish error metrics:', metricError);
  }
}
```

### 5.3 Error Alarms

CloudWatch alarms are configured to alert on critical errors:

```javascript
// Example CDK alarm configuration
const criticalErrorAlarm = new cloudwatch.Alarm(this, 'CriticalErrorAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'ChannelRouter',
    metricName: 'Errors',
    dimensions: {
      Service: 'WhatsAppProcessingEngine',
      ErrorCategory: 'authentication'
    },
    statistic: 'Sum',
    period: Duration.minutes(5)
  }),
  threshold: 1,
  evaluationPeriods: 1,
  alarmDescription: 'Alert on critical authentication errors in WhatsApp Processing Engine',
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
});

// Add SNS notification
criticalErrorAlarm.addAlarmAction(
  new cloudwatchActions.SnsAction(alertTopic)
);
```

## 6. SQS Dead Letter Queues

### 6.1 DLQ Configuration

The system uses Dead Letter Queues (DLQs) to handle persistent failures:

```javascript
// Example CDK configuration for SQS with DLQ
const deadLetterQueue = new sqs.Queue(this, 'WhatsAppProcessingDLQ', {
  retentionPeriod: Duration.days(14),
  visibilityTimeout: Duration.minutes(5)
});

const processingQueue = new sqs.Queue(this, 'WhatsAppProcessingQueue', {
  visibilityTimeout: Duration.minutes(10),
  deadLetterQueue: {
    queue: deadLetterQueue,
    maxReceiveCount: 3
  }
});
```

### 6.2 DLQ Processing

A separate Lambda processes messages that end up in the DLQ:

```javascript
/**
 * Lambda handler for processing DLQ messages
 */
exports.dlqHandler = async (event) => {
  // Process each record in the batch
  for (const record of event.Records) {
    try {
      // Parse the original message
      const originalMessage = JSON.parse(record.body);
      
      console.log('Processing DLQ message', {
        message_id: record.messageId,
        original_message_id: originalMessage.messageId || 'unknown'
      });
      
      // Extract metadata about the failure
      const approximateReceiveCount = record.attributes.ApproximateReceiveCount;
      const sentTimestamp = new Date(Number(record.attributes.SentTimestamp));
      const failureReason = extractFailureReason(originalMessage);
      
      // Store failure in DynamoDB for manual review
      await recordFailedMessage(
        originalMessage,
        failureReason,
        approximateReceiveCount,
        sentTimestamp
      );
      
      // Update conversation if applicable
      if (originalMessage.conversationId) {
        await updateConversationStatus(
          originalMessage.conversationId,
          'failed',
          `Message processing failed and sent to DLQ: ${failureReason}`
        );
      }
      
      // Send notification for critical failures
      if (isCriticalFailure(failureReason)) {
        await sendFailureNotification(originalMessage, failureReason);
      }
    } catch (error) {
      console.error('Error processing DLQ message:', error);
      // Continue processing other messages
    }
  }
  
  return { 
    processed: event.Records.length,
    status: 'completed'
  };
};
```

## 7. API Gateway Error Responses

API Gateway responses are standardized for consistent client handling:

```javascript
/**
 * Gets HTTP status code for an error
 * @param {Error} error - The error
 * @returns {number} - HTTP status code
 */
function getStatusCodeForError(error) {
  const category = categorizeError(error);
  
  // Map error categories to status codes
  const statusCodeMap = {
    'validation': 400,
    'not_found': 404,
    'access_denied': 403,
    'unauthorized': 401,
    'throttling': 429,
    'timeout': 504,
    'server_error': 500
  };
  
  return statusCodeMap[category] || 500;
}

/**
 * Sanitizes error message for client response
 * @param {Error} error - The error
 * @returns {string} - Sanitized error message
 */
function getSanitizedErrorMessage(error) {
  // For security, don't expose internal details in 5xx errors
  const category = categorizeError(error);
  
  if (category === 'server_error' || category === 'timeout') {
    return 'The server encountered an error processing your request';
  }
  
  // For client errors, return the actual message
  return error.message;
}
```

## 8. Lambda Timeout Handling

The system handles Lambda timeouts gracefully:

```javascript
/**
 * Sets up timeout safety for a Lambda function
 * @param {object} context - Lambda context object
 * @param {number} safetyMarginMs - Safety margin in milliseconds
 * @returns {object} - Timeout monitoring handlers
 */
function setupTimeoutSafety(context, safetyMarginMs = 1000) {
  const deadline = new Date(context.getRemainingTimeInMillis() - safetyMarginMs);
  
  // Set timeout for graceful shutdown
  const timeoutId = setTimeout(() => {
    console.log('Lambda approaching timeout, performing graceful shutdown');
    
    // Perform cleanup
    cleanupResources();
    
    // Log impending timeout
    console.warn('Lambda timed out after graceful shutdown');
  }, context.getRemainingTimeInMillis() - safetyMarginMs);
  
  return {
    // Clear timeout if function completes normally
    clearTimeoutSafety: () => clearTimeout(timeoutId),
    
    // Check if we're about to time out
    isTimeoutImminent: () => {
      return context.getRemainingTimeInMillis() < safetyMarginMs * 2;
    }
  };
}

// Example usage in Lambda handler
exports.handler = async (event, context) => {
  const { clearTimeoutSafety, isTimeoutImminent } = setupTimeoutSafety(context);
  
  try {
    // Process SQS messages
    const result = await processMessages(event);
    
    // Periodically check for timeout during long processing
    if (isTimeoutImminent()) {
      // Abandon non-critical work
      console.log('Timeout imminent, skipping non-critical operations');
    }
    
    // Clear the timeout safety
    clearTimeoutSafety();
    
    return result;
  } catch (error) {
    // Handle error
    console.error('Processing error:', error);
    
    // Clear the timeout safety
    clearTimeoutSafety();
    
    throw error;
  }
};
```

## 9. Resource Cleanup

The system ensures resources are properly cleaned up after errors:

```javascript
/**
 * Cleans up resources
 */
function cleanupResources() {
  // Clear any intervals
  for (const interval of activeIntervals) {
    clearInterval(interval);
  }
  
  // Clean up database connections
  if (dbConnection) {
    dbConnection.end();
  }
  
  // Release any locks
  if (activeLocks.length > 0) {
    Promise.all(activeLocks.map(lock => releaseLock(lock)))
      .catch(error => console.error('Error releasing locks:', error));
  }
  
  console.log('Resources cleaned up');
}

// Ensure cleanup on unhandled rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  cleanupResources();
});
```

## 10. Related Documentation

- [Overview and Architecture](./01-overview-architecture.md)
- [SQS Integration and Heartbeat Pattern](./02-sqs-integration.md)
- [Monitoring and Observability](./09-monitoring-observability.md)

## 2. Error Categorization

Errors are categorized into distinct types to enable appropriate handling:

| Error Category | Source | Description | Retry Strategy |
|----------------|--------|-------------|---------------|
| `validation_error` | Input validation | Invalid or missing required parameters | No retry (business error) |
| `authentication_error` | Credentials | Invalid API keys or authentication tokens | No retry (needs human intervention) |
| `authorization_error` | Permissions | Valid credentials but insufficient permissions | No retry (needs human intervention) |
| `resource_not_found` | Resources | Requested resource doesn't exist | No retry (business error) |
| `rate_limit_error` | External APIs | API rate limits exceeded | Exponential backoff retry |
| `timeout_error` | External APIs | API call or operation timeout | Exponential backoff retry |
| `service_unavailable` | External APIs | Temporary service disruption | Exponential backoff retry |
| `network_error` | Connectivity | Network connectivity issues | Exponential backoff retry |
| `internal_error` | System | Unexpected internal system error | Limited retry (3 attempts) |
| `data_inconsistency` | Database | Database or state inconsistency detected | No retry (needs investigation) |
| `configuration_error` | System | System misconfiguration detected | No retry (needs human intervention) |
| `assistant_configuration_error` | OpenAI assistant | Assistant prompt or configuration issue | No retry (needs human intervention) |

### 2.1 Error Subcategories

Some error categories have important subcategories:

#### Authentication Errors
- Missing credentials
- Invalid API key
- Expired credentials
- Malformed token

#### Network Errors
- Connection timeout
- Connection reset
- DNS resolution failure
- Socket hang up

#### Assistant Configuration Errors
- Missing function call - Assistant did not call a function when expected to
- Unexpected function call - Assistant called additional functions when it should have completed

### 2.2 Error Context and Metadata

All errors include context metadata to facilitate troubleshooting:

```javascript
// Example of well-structured error with metadata
const error = new Error('Failed to process message');
error.code = 'OPENAI_RATE_LIMIT';
error.category = 'rate_limit_error';
error.retryable = true;
error.metadata = {
  conversation_id: 'conv_123456',
  thread_id: 'thread_abcdef',
  processing_stage: 'initial',
  operation: 'createRun',
  httpStatus: 429
};
throw error;
```

## 5. Error Handling by Source

The system implements specific handling strategies based on error source:

### 5.1 SQS Processing Errors

SQS message processing errors are handled according to their type:

| Error Type | Handling Strategy | DLQ | Effect |
|------------|-------------------|-----|--------|
| Validation errors | No retry | Yes | Message sent to DLQ immediately |
| Transient errors | Automatic SQS retry | After max retries | Message becomes visible again up to 3 times, then DLQ |
| Message format errors | No retry | Yes | Message sent to DLQ immediately |
| Processing timeout | Lambda retry via SQS | After max retries | New Lambda instance attempts to process message |

### 5.2 OpenAI API Errors

OpenAI API errors are handled with specialized strategies:

| Error Type | Handling Strategy | DLQ | Effect |
|------------|-------------------|-----|--------|
| Rate limit (429) | Exponential backoff | After max attempts | Retry with increasing delays up to 5 times |
| Server errors (5xx) | Exponential backoff | After max attempts | Retry with increasing delays up to 5 times |
| Authentication errors | No retry | Yes | Message sent to DLQ immediately |
| Invalid requests | No retry | Yes | Message sent to DLQ immediately |
| Timeout errors | Retry with longer timeout | After max attempts | Retry with increasing timeouts up to 3 times |
| Network errors | Exponential backoff | After max attempts | Retry with increasing delays up to 5 times |
| Assistant configuration errors | No retry | Yes | Message sent to DLQ immediately with clear error message |

### 5.3 Twilio API Errors

Twilio API errors follow similar patterns:

| Error Type | Handling Strategy | DLQ | Effect |
|------------|-------------------|-----|--------|
| Rate limit errors | Exponential backoff | After max attempts | Retry with increasing delays up to 5 times |
| Authentication errors | No retry | Yes | Message sent to DLQ immediately |
| Invalid request errors | No retry | Yes | Message sent to DLQ immediately |
| Server errors | Exponential backoff | After max attempts | Retry with increasing delays up to 5 times |
| Message content errors | No retry | Yes | Message sent to DLQ immediately |

## 8. DLQ Processing and Investigation

### 8.1 DLQ Message Structure

DLQ messages contain rich error context to facilitate investigation:

```json
{
  "messageId": "123e4567-e89b-12d3-a456-426614174000",
  "receiptHandle": "AQEBwJnKyrHigUMZj6rYigCgxiXzY...",
  "body": "{\"original_payload\": {...}, \"error\": {\"message\": \"Error message\", \"code\": \"ERROR_CODE\", \"category\": \"error_category\", \"metadata\": {\"conversation_id\": \"conv_123\", \"thread_id\": \"thread_abc\", \"processing_stage\": \"initial\"}}}",
  "attributes": {
    "ApproximateReceiveCount": "1",
    "SentTimestamp": "1580815939997",
    "SenderId": "AROAEXAMPLE:lambda-function-name",
    "ApproximateFirstReceiveTimestamp": "1580815940017"
  },
  "messageAttributes": {},
  "md5OfBody": "3cafe40d0b946c856817bb77fe1ada97"
}
```

### 8.2 DLQ Investigation Process

1. **Classify Error Type**: Determine error category from message metadata
2. **Assess Retry Potential**: Determine if the error is retryable or requires human intervention
3. **Check for Patterns**: Look for similar errors affecting multiple messages
4. **Analyze Root Cause**: Investigate underlying issue using error metadata
5. **Resolution Strategy**: Develop appropriate resolution based on error type

#### 8.2.1 Assistant Configuration Errors

When investigating assistant configuration errors:

1. Check the assistant ID in the error metadata
2. Verify the OpenAI assistant configuration in the OpenAI dashboard
3. Review the system prompt for clear instructions about function calling behavior
4. Ensure the assistant has the correct functions available
5. Test the assistant directly in the OpenAI playground with similar inputs
6. Update the assistant configuration as needed
7. Requeue messages for processing after fixing the configuration

### 8.3 DLQ Message Reprocessing

For retryable errors, messages can be reprocessed:

```javascript
// Example DLQ reprocessing function
async function reprocessDLQMessage(dlqMessage) {
  try {
    // Parse original message
    const originalMessage = JSON.parse(dlqMessage.body);
    const errorMetadata = JSON.parse(originalMessage.error || "{}").metadata || {};
    
    // Check if error is retryable
    if (errorMetadata.category === 'assistant_configuration_error') {
      console.log('Assistant configuration error detected - manual intervention required', {
        error_code: errorMetadata.code,
        assistant_id: errorMetadata.assistant_id,
        conversation_id: errorMetadata.conversation_id
      });
      
      // Log detailed guidance
      console.log('Please check the assistant configuration in the OpenAI dashboard');
      return false; // Not automatically retryable
    }
    
    // For retryable errors
    if (isRetryableError(errorMetadata.category)) {
      // Send back to original queue
      await sendToOriginalQueue(originalMessage.original_payload);
      return true;
    }
    
    return false;
  } catch (error) {
    console.error('Error reprocessing DLQ message', error);
    return false;
  }
}
```

### 5.2 OpenAI Assistant Configuration Issues

The OpenAI integration includes specialized handling for assistant configuration issues:

```javascript
/**
 * Handles assistant configuration issues by emitting metrics and providing detailed logging
 * @param {string} issueType - Type of configuration issue (e.g., 'InvalidJSONResponse')
 * @param {object} contextObject - Context object with conversation data
 * @param {string} assistantId - OpenAI assistant ID
 * @param {object} details - Additional details about the issue
 */
async function handleAssistantConfigurationIssue(issueType, contextObject, assistantId, details = {}) {
  try {
    // Log detailed information about the issue
    console.error(`Assistant configuration issue: ${issueType}`, {
      assistant_id: assistantId,
      conversation_id: contextObject.conversation_data?.conversation_id,
      company_id: contextObject.company_data?.company_id,
      thread_id: contextObject.thread_id,
      ...details
    });
    
    // Emit metric for monitoring
    await emitConfigurationIssueMetric(issueType, {
      conversation_id: contextObject.conversation_data?.conversation_id,
      assistant_id: assistantId,
      environment: process.env.ENVIRONMENT || 'dev'
    });
    
    // Update conversation record with error information
    await updateConversationError(
      contextObject.conversation_data,
      {
        error_type: 'assistant_configuration',
        error_category: issueType,
        error_message: `Assistant configuration issue: ${issueType}`,
        error_timestamp: new Date().toISOString(),
        error_details: JSON.stringify(details)
      }
    );
    
    // Update conversation status to failed
    await updateConversationStatus(
      contextObject.conversation_data,
      'failed'
    );
    
    // Create a structured error for the DLQ with metadata
    const error = new Error(`Assistant configuration issue: ${issueType}`);
    error.name = 'AssistantConfigurationError';
    error.code = `ASSISTANT_CONFIG_${issueType.toUpperCase()}`;
    error.metadata = {
      assistant_id: assistantId,
      conversation_id: contextObject.conversation_data?.conversation_id,
      thread_id: contextObject.thread_id,
      issue_type: issueType,
      ...details
    };
    
    return error;
  } catch (metricError) {
    // If there's an error in the error handling, log but continue with the original error
    console.error('Error handling assistant configuration issue:', metricError);
    
    // Create a basic error if the full handling fails
    const error = new Error(`Assistant configuration issue: ${issueType}`);
    error.name = 'AssistantConfigurationError';
    
    return error;
  }
}
```

Usage in JSON response processing:

```javascript
// Extract JSON content from message
try {
  const jsonMatch = messageContent.match(/```json\n([\s\S]*?)\n```/) || 
                    messageContent.match(/\{[\s\S]*\}/);
                     
  const jsonContent = jsonMatch ? jsonMatch[1] || jsonMatch[0] : messageContent;
  const parsedContent = JSON.parse(jsonContent);
  
  // Validate the parsed content has content_variables
  if (!parsedContent.content_variables) {
    const error = await handleAssistantConfigurationIssue(
      'MissingContentVariables',
      contextObject,
      assistantId,
      { parsed_content: JSON.stringify(parsedContent) }
    );
    throw error;
  }
  
  if (Object.keys(parsedContent.content_variables).length === 0) {
    const error = await handleAssistantConfigurationIssue(
      'EmptyContentVariables',
      contextObject,
      assistantId,
      { parsed_content: JSON.stringify(parsedContent) }
    );
    throw error;
  }
  
  contentVariables = parsedContent.content_variables;
} catch (parseError) {
  if (parseError.name === 'AssistantConfigurationError') {
    // Already handled, just rethrow
    throw parseError;
  }
  
  // Handle JSON parsing errors
  const error = await handleAssistantConfigurationIssue(
    'InvalidJSONResponse',
    contextObject,
    assistantId,
    { 
      parse_error: parseError.message,
      message_content: messageContent.substring(0, 500) // Limit for logging
    }
  );
  throw error;
} 
```

## 9. Concurrency and Robustness Considerations

### 9.1 Asynchronous Processing Model

The WhatsApp Processing Engine implements a sophisticated asynchronous processing model to handle long-running operations efficiently:

```javascript
/**
 * Main asynchronous processing flow
 * Uses Promise chaining to handle sequential operations with proper error propagation
 * @param {object} message - SQS message
 * @returns {Promise<object>} - Processing result
 */
async function processMessageAsync(message) {
  // Create heartbeat for SQS visibility extension
  const { heartbeatInterval, clearHeartbeat } = setupSQSHeartbeat(message.receiptHandle);
  
  try {
    // Stage 1: Parse and validate message
    const contextObject = await parseAndValidateMessage(message.body);
    
    // Stage 2: Create conversation record
    const conversationRecord = await createConversationRecord(contextObject);
    contextObject.conversation_data = conversationRecord;
    
    // Stage 3: Process with OpenAI (long-running operation)
    const openAIResult = await Promise.race([
      processWithOpenAI(contextObject),
      createTimeoutPromise('OpenAI processing', 300000) // 5-minute timeout
    ]);
    
    // Stage 4: Send template message via Twilio
    const twilioResult = await sendWhatsAppTemplateMessage(
      contextObject,
      contextObject.conversation_data.content_variables
    );
    
    // Stage 5: Update conversation with results
    await finalizeConversation(contextObject, twilioResult);
    
    // Clean up resources
    clearHeartbeat();
    return { success: true, conversationId: conversationRecord.conversation_id };
  } catch (error) {
    // Ensure heartbeat is cleared even on error
    clearHeartbeat();
    
    // Handle error appropriately
    await handleProcessingError(error, message);
    throw error; // Re-throw for SQS retry mechanism if needed
  }
}

/**
 * Creates a timeout promise that rejects after specified duration
 * @param {string} operation - Name of the operation
 * @param {number} timeoutMs - Timeout in milliseconds
 * @returns {Promise<never>} - Promise that rejects on timeout
 */
function createTimeoutPromise(operation, timeoutMs) {
  return new Promise((_, reject) => {
    setTimeout(() => {
      reject(new Error(`${operation} timed out after ${timeoutMs}ms`));
    }, timeoutMs);
  });
}
```

The asynchronous processing model provides several important benefits:

1. **Resource Efficiency**: Allows the Lambda function to handle I/O-bound operations efficiently
2. **Graceful Timeouts**: Implements timeout safety for long-running operations
3. **Progressive Processing**: Enables step-by-step processing with appropriate error handling at each stage
4. **Clean Resource Management**: Ensures resources are properly released even on failure
5. **Non-blocking Operations**: Maximizes throughput by avoiding blocking on I/O operations

### 9.2 Managing Long-Running Operations

The WhatsApp Processing Engine handles long-running operations with a combination of techniques:

#### 9.2.1 SQS Visibility Extension

For operations that exceed the default SQS visibility timeout, the system implements an automatic heartbeat:

```javascript
/**
 * Sets up a heartbeat to extend SQS message visibility
 * @param {string} receiptHandle - SQS message receipt handle
 * @returns {object} - Heartbeat control functions
 */
function setupSQSHeartbeat(receiptHandle) {
  // Start with a 5-minute interval (300,000ms)
  // This is shorter than the 10-minute visibility timeout
  const heartbeatInterval = setInterval(async () => {
    try {
      console.log('Extending message visibility timeout');
      
      await sqs.changeMessageVisibility({
        QueueUrl: process.env.WHATSAPP_QUEUE_URL,
        ReceiptHandle: receiptHandle,
        VisibilityTimeout: 600 // 10 minutes in seconds
      }).promise();
      
      console.log('Successfully extended message visibility timeout');
    } catch (error) {
      console.error('Failed to extend message visibility timeout', error);
      // We don't clear the interval here, as it may succeed on the next attempt
    }
  }, 300000); // Every 5 minutes
  
  // Return functions to control the heartbeat
  return {
    heartbeatInterval,
    clearHeartbeat: () => clearInterval(heartbeatInterval)
  };
}
```

#### 9.2.2 OpenAI Polling with Backoff

When waiting for OpenAI runs to complete, the system uses adaptive polling with backoff:

```javascript
/**
 * Polls OpenAI run status with adaptive backoff
 * @param {object} openai - OpenAI client
 * @param {string} threadId - Thread ID
 * @param {string} runId - Run ID
 * @returns {Promise<object>} - Final run status
 */
async function pollRunWithAdaptiveBackoff(openai, threadId, runId) {
  const MAX_POLL_DURATION = 600000; // 10 minutes total
  const startTime = Date.now();
  let pollInterval = 1000; // Start with 1 second
  const MAX_POLL_INTERVAL = 5000; // Cap at 5 seconds
  
  let run = await openai.beta.threads.runs.retrieve(threadId, runId);
  
  while (isRunInProgress(run.status)) {
    // Check for timeout
    if (Date.now() - startTime > MAX_POLL_DURATION) {
      throw new Error(`Run polling exceeded maximum duration (${MAX_POLL_DURATION}ms)`);
    }
    
    // Wait before next poll with backoff
    await new Promise(resolve => setTimeout(resolve, pollInterval));
    
    // Increase poll interval with a cap
    pollInterval = Math.min(pollInterval * 1.5, MAX_POLL_INTERVAL);
    
    // Get updated status
    run = await openai.beta.threads.runs.retrieve(threadId, runId);
    
    // Emit metrics for monitoring
    await emitRunStatusMetric(run.status, {
      thread_id: threadId,
      run_id: runId,
      company_id: contextObject.company_id,
      elapsed_ms: Date.now() - startTime
    });
  }
  
  return run;
}

/**
 * Checks if run status indicates it's still in progress
 * @param {string} status - Run status
 * @returns {boolean} - True if run is still in progress
 */
function isRunInProgress(status) {
  return ['queued', 'in_progress', 'cancelling'].includes(status);
}
```

#### 9.2.3 Lambda Timeout Safety

To prevent abrupt Lambda timeouts, the system implements safety mechanisms:

```javascript
/**
 * Sets up timeout safety for Lambda function
 * @param {object} context - Lambda context
 * @param {number} safetyMarginMs - Safety margin in milliseconds
 * @returns {object} - Timeout safety functions
 */
function setupTimeoutSafety(context, safetyMarginMs = 10000) {
  // Calculate when to trigger safety shutdown
  const safetyTime = context.getRemainingTimeInMillis() - safetyMarginMs;
  
  // Create timeout for graceful shutdown
  const timeoutId = setTimeout(() => {
    console.warn('Lambda approaching timeout, performing graceful shutdown');
    // Perform cleanup operations here
    cleanupResources();
    
    // Log the timeout for monitoring
    console.error('Lambda timed out after graceful shutdown');
  }, safetyTime);
  
  return {
    // Clear the timeout if operation completes normally
    clearTimeoutSafety: () => clearTimeout(timeoutId),
    
    // Check if we're approaching the timeout
    isTimeoutImminent: () => context.getRemainingTimeInMillis() < safetyMarginMs * 2
  };
}

// Example usage in Lambda handler
exports.handler = async (event, context) => {
  const { clearTimeoutSafety, isTimeoutImminent } = setupTimeoutSafety(context);
  
  try {
    // Process message with timeout awareness
    const result = await processMessageAsync(event.Records[0]);
    
    // Check for imminent timeout before additional operations
    if (isTimeoutImminent()) {
      console.log('Skipping non-critical operations due to imminent timeout');
      // Skip non-essential operations
    } else {
      // Perform additional non-critical operations
      await performAdditionalOperations(result);
    }
    
    // Clear timeout safety
    clearTimeoutSafety();
    return result;
  } catch (error) {
    // Clear timeout safety even on error
    clearTimeoutSafety();
    throw error;
  }
};
```

### 9.3 Idempotent Processing

The WhatsApp Processing Engine implements idempotent processing to handle potential duplicate message processing safely:

#### 9.3.1 Idempotent Conversation Creation

```javascript
/**
 * Creates conversation record with idempotency
 * @param {object} contextObject - Context object
 * @returns {Promise<object>} - Created conversation record
 */
async function createConversationRecordIdempotent(contextObject) {
  const conversationId = generateConversationId(contextObject);
  const recipientTel = contextObject.frontend_payload.recipient_data.recipient_tel;
  
  // Check if conversation already exists
  try {
    const existingRecord = await dynamoDB.get({
      TableName: CONVERSATIONS_TABLE,
      Key: {
        recipient_tel: recipientTel,
        conversation_id: conversationId
      }
    }).promise();
    
    if (existingRecord.Item) {
      console.log('Found existing conversation record, using it for idempotency', {
        conversation_id: conversationId,
        recipient_tel: recipientTel
      });
      return existingRecord.Item;
    }
  } catch (error) {
    console.error('Error checking for existing conversation', error);
    // Continue to creation if lookup fails
  }
  
  // Generate new conversation record with processing status
  const conversationRecord = {
    recipient_tel: recipientTel,
    conversation_id: conversationId,
    company_id: contextObject.company_data.company_id,
    project_id: contextObject.company_data.project_id,
    conversation_status: 'processing',
    channel_method: 'whatsapp',
    company_whatsapp_number: contextObject.channel_config.whatsapp.company_whatsapp_number,
    messages: [],
    request_id: contextObject.frontend_payload.request_data.request_id,
    task_complete: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    idempotency_key: contextObject.frontend_payload.request_data.idempotency_key || null
  };
  
  // Use conditional expression to ensure idempotency
  try {
    await dynamoDB.put({
      TableName: CONVERSATIONS_TABLE,
      Item: conversationRecord,
      ConditionExpression: 'attribute_not_exists(conversation_id)'
    }).promise();
    
    console.log('Created new conversation record', {
      conversation_id: conversationId,
      recipient_tel: recipientTel
    });
    
    return conversationRecord;
  } catch (error) {
    if (error.code === 'ConditionalCheckFailedException') {
      // Race condition - record was created between our check and put
      // Retrieve the existing record
      const result = await dynamoDB.get({
        TableName: CONVERSATIONS_TABLE,
        Key: {
          recipient_tel: recipientTel,
          conversation_id: conversationId
        }
      }).promise();
      
      console.log('Conversation record created concurrently, using existing record', {
        conversation_id: conversationId
      });
      
      return result.Item;
    }
    
    // For other errors, rethrow
    throw error;
  }
}
```

#### 9.3.2 Idempotent Message Sending

```javascript
/**
 * Sends template message with idempotency safeguards
 * @param {object} contextObject - Context object with conversation data
 * @param {object} variables - Template variables
 * @returns {Promise<object>} - Message sending result
 */
async function sendWhatsAppTemplateMessageIdempotent(contextObject, variables) {
  const conversationRecord = contextObject.conversation_data;
  const idempotencyKey = `wamsg_${conversationRecord.conversation_id}`;
  
  // Check if message was already sent
  if (conversationRecord.message_sid) {
    console.log('Message already sent for this conversation, returning existing SID', {
      conversation_id: conversationRecord.conversation_id,
      message_sid: conversationRecord.message_sid
    });
    
    return {
      sid: conversationRecord.message_sid,
      status: 'sent',
      idempotent: true
    };
  }
  
  // If not previously sent, send the message with idempotency key
  try {
    // Get WhatsApp credentials
    const whatsappCredentialsId = contextObject.channel_config.whatsapp.whatsapp_credentials_id;
    const twilioCredentials = await getSecretValue(whatsappCredentialsId);
    
    // Initialize Twilio client
    const twilioClient = twilio(
      twilioCredentials.twilio_account_sid,
      twilioCredentials.twilio_auth_token
    );
    
    // Prepare message options with idempotency key
    const messageOptions = {
      from: `whatsapp:${contextObject.channel_config.whatsapp.company_whatsapp_number}`,
      to: `whatsapp:${contextObject.frontend_payload.recipient_data.recipient_tel}`,
      contentSid: twilioCredentials.twilio_template_sid,
      contentVariables: JSON.stringify(variables),
      pathParams: { idempotencyKey }  // Twilio API idempotency key
    };
    
    // Send the message
    const message = await twilioClient.messages.create(messageOptions);
    
    // Store message SID for future idempotency checks
    await updateConversationMessageSid(
      conversationRecord,
      message.sid
    );
    
    return {
      sid: message.sid,
      status: message.status,
      idempotent: false
    };
  } catch (error) {
    // Handle specific idempotency error from Twilio
    if (error.code === 20056) {  // Duplicate message error
      // Extract SID from error message if possible
      const sidMatch = error.message.match(/SID: (SM[a-f0-9]+)/);
      const messageSid = sidMatch ? sidMatch[1] : null;
      
      if (messageSid) {
        // Update conversation with the extracted SID
        await updateConversationMessageSid(
          conversationRecord,
          messageSid
        );
        
        return {
          sid: messageSid,
          status: 'sent',
          idempotent: true
        };
      }
    }
    
    // Rethrow other errors
    throw error;
  }
}

/**
 * Updates conversation with message SID
 * @param {object} conversationRecord - Conversation record
 * @param {string} messageSid - Message SID
 * @returns {Promise<void>}
 */
async function updateConversationMessageSid(conversationRecord, messageSid) {
  await dynamoDB.update({
    TableName: CONVERSATIONS_TABLE,
    Key: {
      recipient_tel: conversationRecord.recipient_tel,
      conversation_id: conversationRecord.conversation_id
    },
    UpdateExpression: 'SET message_sid = :sid, updated_at = :now',
    ExpressionAttributeValues: {
      ':sid': messageSid,
      ':now': new Date().toISOString()
    }
  }).promise();
}
```

### 9.4 Concurrent Processing Considerations

The WhatsApp Processing Engine carefully manages concurrency to ensure system stability:

```javascript
// CDK configuration with concurrency controls
const whatsappProcessingLambda = new lambda.Function(this, 'WhatsAppProcessingFunction', {
  runtime: lambda.Runtime.NODEJS_16_X,
  code: lambda.Code.fromAsset('lambda'),
  handler: 'whatsapp-processing.handler',
  timeout: cdk.Duration.minutes(15),
  memorySize: 1024,
  environment: {
    CONVERSATIONS_TABLE: conversationsTable.tableName,
    WHATSAPP_QUEUE_URL: whatsappQueue.queueUrl,
    LOG_LEVEL: 'INFO',
    NODE_OPTIONS: '--enable-source-maps'
  },
  tracing: lambda.Tracing.ACTIVE,
  reservedConcurrentExecutions: 25,  // Limit concurrent executions
});

// SQS event source with controlled batch size
whatsappProcessingLambda.addEventSource(new SqsEventSource(whatsappQueue, {
  batchSize: 1,  // Process one message at a time
  maxBatchingWindow: Duration.seconds(0)  // Don't wait to collect messages
}));
```

Key concurrency management strategies include:

1. **Reserved Concurrency**: Limits Lambda to 25 concurrent executions to prevent overwhelming downstream services
2. **Batch Size 1**: Processes one message at a time to ensure clean failure isolation
3. **DynamoDB Capacity Management**: Ensures DynamoDB can handle the concurrent request volume
4. **Adaptive Rate Limiting**: Controls API call rates to external services
5. **Connection Pooling**: Reuses connections to AWS services across invocations
6. **Throttling Awareness**: Handles throttling from downstream services appropriately

These concurrency controls ensure the system remains stable under load and prevents cascading failures across components.

## 10. Resource Cleanup

// ... existing code ...