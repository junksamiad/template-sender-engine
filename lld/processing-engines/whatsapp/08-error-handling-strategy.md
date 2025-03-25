# WhatsApp Processing Engine - Error Handling Strategy

> **Part 8 of 10 in the WhatsApp Processing Engine documentation series**

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
| Missing Variables | OPENAI_MISSING_VARIABLES | JSON response missing required variables | No retry, send to DLQ | "Missing variables in assistant response" |

In addition to standard API errors, the system tracks and handles specific OpenAI assistant configuration issues:

| Error Code | Description | Handling Strategy |
|------------|-------------|-------------------|
| INVALID_JSON_RESPONSE | Assistant did not return valid JSON | 1. Log detailed error with message content<br>2. Emit CloudWatch metric<br>3. Send to DLQ |
| MISSING_VARIABLES | Assistant returned JSON without variables | 1. Log detailed error with parsed response<br>2. Emit CloudWatch metric<br>3. Send to DLQ |

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