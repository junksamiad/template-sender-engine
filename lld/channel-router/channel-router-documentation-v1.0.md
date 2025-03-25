# Channel Router - Low-Level Design Documentation

## 1. Introduction

This document provides a detailed description of the Channel Router component of the WhatsApp AI chatbot system. The Channel Router serves as the entry point for all frontend applications, validating incoming requests and routing them to the appropriate channel-specific message queue based on the specified channel method. This design enables a modular architecture that can support multiple communication channels while maintaining separation of concerns and providing resilience through asynchronous processing.

## 2. Architecture Overview

### 2.1 Component Purpose

The Channel Router is responsible for:

- Receiving incoming payloads from various frontend applications
- Validating the request structure and authenticating the API key
- Providing immediate acknowledgment to the frontend
- Routing requests to the appropriate channel-specific message queue
- Ensuring reliable message delivery even during service disruptions
- Providing a consistent interface for all frontend applications regardless of channel

### 2.2 Position in System Architecture

The Channel Router sits between:
- **Upstream**: Various frontend applications (recruitment agency, IVA company, etc.)
- **Downstream**: Channel-specific message queues and processing engines

```
Frontend Applications → Channel Router → Channel-Specific Message Queues → Channel Processing Engines
```

### 2.3 Technical Implementation

The Channel Router will be implemented as:

- **API Gateway**: Serves as the entry point for all requests
- **Lambda Function**: Performs validation, authentication, and queue routing logic
- **SQS Queues**: Channel-specific queues for asynchronous processing
- **Dead Letter Queues (DLQs)**: For handling failed message processing
- **IAM Roles**: Provides necessary permissions to access other AWS services
- **CloudWatch**: Monitors and logs router operations
- **AWS Secrets Manager**: Securely stores and manages API keys

## 3. Detailed Design

### 3.1 API Specification

#### 3.1.1 Endpoint

```
POST https://api.example.com/v1/router
```

#### 3.1.2 Headers

```
Content-Type: application/json
Authorization: Bearer {API_KEY}
```

#### 3.1.3 Request Body

The router accepts the payload structure as defined in the frontend documentation:

```json
{
  "company_data": {
    "company_id": "string",
    "project_id": "string",
    "api_key": "string"
  },
  "recipient_data": {
    "recipient_first_name": "string",
    "recipient_last_name": "string",
    "recipient_tel": "string",
    "recipient_email": "string"
  },
  "project_data": {
    // Varies by use case
  },
  "request_data": {
    "request_id": "string", // UUID v4 for idempotency and tracing
    "channel_method": "whatsapp|email|sms",
    "initial_request_timestamp": "string" // ISO 8601 format
  }
}
```

#### 3.1.4 Response Format

The router provides an immediate acknowledgment response:

```json
{
  "status": "success",
  "request_id": "same-as-sent-request-id",
  "message": "Request accepted and queued for processing",
  "queue_timestamp": "2023-06-15T14:30:45.789Z"
}
```

For error responses:

```json
{
  "status": "error",
  "error_code": "ERROR_CODE",
  "message": "Error message description",
  "request_id": "same-as-sent-request-id-if-available"
}
```

### 3.2 Routing Logic

The router implements the following logic flow:

1. **Validate Request**: Ensure the payload contains all required fields and structures
   - Validate top-level structure (company_data, recipient_data, project_data, request_data)
   - Verify request_id is a valid UUID v4
   - Verify initial_request_timestamp is a valid ISO 8601 timestamp
   - Check that timestamp is within acceptable time window (e.g., not older than 5 minutes)
   - Validate channel-specific requirements (e.g., recipient_tel for WhatsApp)
   - Check payload size limits
   
2. **Authenticate Request**: Validate the API key against company_id and project_id
   - Extract API key from Authorization header
   - Query DynamoDB for company/project record
   - Retrieve the API key reference from DynamoDB
   - Fetch the actual API key from AWS Secrets Manager
   - Compare the provided key with the stored key
   - Validate additional constraints (allowed channels, rate limits, project_status)

3. **Extract Channel Method**: Get the channel_method from request_data

4. **Place in Queue**: Send the payload to the appropriate channel-specific SQS queue

5. **Return Immediate Response**: Provide immediate acknowledgment to the frontend

#### 3.2.1 Channel Queue Mapping

| Channel Method | SQS Queue |
|----------------|-----------|
| whatsapp | WhatsAppQueue |
| email | EmailQueue |
| sms | SMSQueue |

### 3.3 Error Handling

| Error Scenario | HTTP Status | Error Code | Error Message |
|----------------|-------------|------------|---------------|
| Missing request_id | 400 | MISSING_REQUEST_ID | "request_id is required in request_data" |
| Invalid request_id format | 400 | INVALID_REQUEST_ID | "request_id must be a valid UUID v4" |
| Missing channel_method | 400 | MISSING_CHANNEL | "channel_method is required in request_data" |
| Unsupported channel | 400 | UNSUPPORTED_CHANNEL | "Channel method '{method}' is not supported" |
| Missing/invalid timestamp | 400 | INVALID_TIMESTAMP | "initial_request_timestamp must be a valid ISO 8601 timestamp" |
| Timestamp too old | 400 | TIMESTAMP_EXPIRED | "Request timestamp is too old (>5 minutes)" |
| Missing recipient_tel for WhatsApp | 400 | MISSING_RECIPIENT_TEL | "WhatsApp channel requires recipient_tel" |
| Missing recipient_email for Email | 400 | MISSING_RECIPIENT_EMAIL | "Email channel requires recipient_email" |
| Payload too large | 400 | PAYLOAD_TOO_LARGE | "Payload size exceeds maximum allowed (100KB)" |
| Project not active | 403 | PROJECT_INACTIVE | "Project is not active. Current status: {status}" |
| Channel not allowed | 403 | CHANNEL_NOT_ALLOWED | "Channel method '{method}' is not allowed for this project" |
| Authentication failure | 401 | UNAUTHORIZED | "Invalid or missing API key" |
| Rate limit exceeded | 429 | RATE_LIMIT_EXCEEDED | "Rate limit exceeded. Try again later." |
| Queue service unavailable | 503 | QUEUE_UNAVAILABLE | "Message queue service is currently unavailable" |
| Internal error | 500 | INTERNAL_ERROR | "An internal error occurred" |

### 3.4 Logging and Monitoring

The Channel Router logs the following information for each request:

- Request timestamp
- Company ID and Project ID
- Channel method
- Request ID (for tracing)
- Response status
- Queue placement success/failure
- Processing time
- Error details (if applicable)

### 3.5 Rate Limiting & Concurrency

> **Note: Current Implementation Status**
> While per-client rate limits are defined in the `wa_company_data` table and included in the context object, they are **not currently enforced** in the Channel Router implementation. The system currently relies only on the API Gateway rate limits described below. Per-client rate limiting is planned for future implementation as noted in the Future Enhancements section (9.12).

#### 3.5.1 API Gateway Settings

1. **Rate Limit**: 
   - Set to 10 requests per second
   - This provides protection against potential attacks while allowing normal usage
   - Sufficient for our current business scale with a small number of clients

2. **Burst Limit**: 
   - Set to 20 concurrent requests
   - Allows handling of occasional traffic spikes
   - Provides flexibility for legitimate concurrent usage

#### 3.5.2 Lambda Function Settings

1. **Channel Router Lambda Settings**:
   - **Timeout**: Set to 30 seconds
   - Sufficient for validation, authentication, and queue placement operations
   - No concurrency limit needed as we rely on API Gateway rate limiting
   - Quick operations that don't involve waiting for external APIs

2. **Processing Engine Lambda Settings** (for reference, implemented in separate services):
   - **Concurrency Limit**: 20-30 concurrent executions
   - **Timeout**: 900 seconds (15 minutes, the maximum allowed)
   - **Heartbeat Pattern**: Extend visibility timeout every 300 seconds
   - Configured for long-running operations with external APIs like OpenAI

#### 3.5.3 Basic CloudWatch Alarms

- Set up simple alarms for API Gateway throttling events
- Monitor Lambda concurrent executions
- Alert if either exceeds expected thresholds

### 3.6 Context Object Creation

The Channel Router not only routes messages to the appropriate queue but also enriches the payload with additional context information retrieved from the `wa_company_data` DynamoDB table. This context object contains all the necessary information for downstream processing, eliminating the need for subsequent services to query the database again.

#### 3.6.1 Data Retrieval from DynamoDB

When a request is received, the Channel Router retrieves the following information from the `wa_company_data` table using the `company_id` and `project_id` from the incoming payload:

1. **Company Information**:
   - Company name
   - Project name
   - Project status (to verify the project is active)
   - Allowed channels (to validate the requested channel is permitted)

2. **Channel-Specific Configuration**:
   - For WhatsApp: Reference to WhatsApp credentials in Secrets Manager and company WhatsApp phone number
   - For Email: Reference to Email credentials in Secrets Manager
   - For SMS: Reference to SMS credentials in Secrets Manager

3. **OpenAI Configuration**:
   - Multiple Assistant IDs (template sender, replies, and additional assistants)
   - Project ID
   - API key reference

4. **Project Rate Limiting Information**:
   - Requests per minute/day limits
   - Concurrent conversation limits
   - Message length limits

#### 3.6.2 Secret Retrieval

For secure handling of sensitive credentials:

1. **No Sensitive Credentials in Context Object**:
   - Sensitive credentials are no longer included in the context object
   - Only credential identifiers are included, which are used by downstream services to retrieve credentials when needed
   - This follows security best practices by reducing the exposure of sensitive information

2. **Authentication at Router Level**:
   - The Channel Router still retrieves and validates the API key during request authentication
   - API keys are verified against references stored in Secrets Manager 
   - After validation, only the reference identifiers are passed in the context object

#### 3.6.3 Context Object Structure

The Channel Router constructs a comprehensive context object by combining:
1. The original request payload
2. Company and project configuration from DynamoDB (excluding sensitive information)
3. References to secrets in AWS Secrets Manager (not the actual secrets)

The resulting context object has the following structure:

```json
{
  "frontend_payload": {
    "company_data": {
      "company_id": "cucumber-recruitment",
      "company_name": "Cucumber Recruitment Ltd"
    },
    "recipient_data": {
      "recipient_tel": "+447123456789",
      "recipient_email": "candidate@example.com"
    },
    "project_data": {
      "project_id": "cv-analysis",
      "project_name": "CV Analysis Bot"
    },
    "request_data": {
      "initial_request_timestamp": "2023-06-15T14:30:45.123Z",
      "request_id": "req_123456789"
    }
  },
  "wa_company_data_payload": {
    "company_name": "Cucumber Recruitment Ltd",
    "project_name": "CV Analysis Bot",
    "project_status": "active",
    "allowed_channels": ["whatsapp", "email", "sms"],
    "company_rep": {
      "company_rep_1": "Carol",
      "company_rep_2": "Mark",
      "company_rep_3": null,
      "company_rep_4": null,
      "company_rep_5": null
    },
    "rate_limits": {
      "requests_per_minute": 100,
      "requests_per_day": 10000,
      "concurrent_conversations": 50,
      "max_message_length": 4096
    }
  },
  "project_rate_limits": {
    "requests_per_minute": 100,
    "requests_per_day": 10000,
    "concurrent_conversations": 50,
    "max_message_length": 4096
  },
  "channel_config": {
    "whatsapp": {
      "whatsapp_credentials_id": "whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio",
      "company_whatsapp_number": "+14155238886"
    },
    "sms": {
      "sms_credentials_id": "sms-credentials/cucumber-recruitment/cv-analysis/twilio",
      "company_sms_number": "+14155238887"
    },
    "email": {
      "email_credentials_id": "email-credentials/cucumber-recruitment/cv-analysis/sendgrid",
      "company_email": "jobs@cucumber-recruitment.com"
    }
  },
  "ai_config": {
    "assistant_id_template_sender": "asst_Ds59ylP35Pn84pasJQVglC2Q",
    "assistant_id_replies": "asst_Ds59ylP35Pn84pesJQVglC2Q",
    "assistant_id_3": "",
    "assistant_id_4": "",
    "assistant_id_5": "",
    "ai_api_key_reference": "secret/api-keys/cucumber-recruitment/cv-analysis/openai"
  },
  "metadata": {
    "router_version": "1.0.0"
  }
}
```

#### 3.6.4 Context Object Handling

The complete context object is:

1. **Serialized**: Converted to JSON format
2. **Placed in Queue**: Sent to the appropriate channel-specific SQS queue
3. **Secured**: Sensitive information is protected through SQS encryption at rest and in transit

This approach provides several benefits:

- **Efficiency**: Downstream services don't need to query DynamoDB again
- **Consistency**: All services work with the same configuration data
- **Resilience**: Even if DynamoDB becomes temporarily unavailable, processing can continue with queued messages
- **Simplicity**: Processing services have all required context in one place
- **Security**: Sensitive credentials are only resolved when needed and transmitted securely
- **Traceability**: The request_id from the frontend payload is preserved throughout the processing pipeline for tracking and debugging

#### 3.6.5 Implementation in Lambda Function

```javascript
// Pseudo-code for context object creation in the Channel Router Lambda

exports.handler = async (event) => {
  try {
    // Parse request body
    const payload = JSON.parse(event.body);
    
    // Validate request
    validateRequest(payload);
    
    // Authentication module (separate concern within Lambda)
    const authResult = await authenticationModule.authenticate(event.headers, payload);
    if (!authResult.isAuthenticated) {
      return formatErrorResponse(authResult.error, payload?.request_data?.request_id);
    }
    
    // Validated company/project data is returned from auth module
    const { companyData } = authResult;
    
    // Create the context object with all necessary information (but no sensitive credentials)
    const contextObject = await contextModule.createContextObject(payload, companyData);
    
    // Extract channel method
    const channelMethod = payload.request_data.channel_method;
    const requestId = payload.request_data.request_id;
    
    // Get appropriate SQS queue URL
    const queueUrl = getChannelQueueUrl(channelMethod);
    
    // Place context object in queue
    await sendToQueue(queueUrl, contextObject);
    
    // Return immediate success response
    return formatSuccessResponse(requestId);
  } catch (error) {
    // Handle errors
    return formatErrorResponse(error, payload?.request_data?.request_id);
  }
};

// Validation module
function validateRequest(payload) {
  // 1. Validate top-level structure
  validateTopLevelStructure(payload);
  
  // 2. Validate critical fields
  validateCriticalFields(payload);
  
  // 3. Validate channel-specific requirements
  validateChannelRequirements(payload);
  
  // 4. Validate payload size
  validatePayloadSize(payload);
}

// Authentication module
const authenticationModule = {
  async authenticate(headers, payload) {
    // Extract API key from Authorization header
    const apiKey = extractApiKey(headers);
    
    // Query DynamoDB for company/project record
    const companyData = await getCompanyData(payload.company_data.company_id, payload.company_data.project_id);
    
    // Get API key reference from company data
    const apiKeyReference = companyData.api_key_reference;
    
    // Fetch actual API key from Secrets Manager
    const storedApiKey = await getSecretValue(apiKeyReference);
    
    // Compare provided key with stored key
    const isKeyValid = compareApiKeys(apiKey, storedApiKey);
    
    // Validate additional constraints
    validateConstraints(companyData, payload);
    
    return {
      isAuthenticated: isKeyValid,
      companyData,
      error: isKeyValid ? null : { code: 'UNAUTHORIZED', message: 'Invalid API key' }
    };
  }
};

// Secrets module only used for API key validation during authentication
const secretsModule = {
  async getRequiredSecrets(companyData) {
    const secrets = {};
    
    // Get API key for authentication
    if (companyData.api_key_reference) {
      secrets.api_key = await getSecretValue(companyData.api_key_reference);
    }
    
    return secrets;
  }
};

// Context module
const contextModule = {
  async createContextObject(payload, companyData) {
    // Extract channel method to determine which configuration to include
    const channelMethod = payload.request_data.channel_method;
    
    // Create a deep copy of the payload to avoid mutating the original
    const sanitizedPayload = JSON.parse(JSON.stringify(payload));
    
    // Remove API key from the frontend payload for security reasons
    // This ensures sensitive credentials aren't passed through the processing pipeline
    if (sanitizedPayload.company_data && sanitizedPayload.company_data.api_key) {
      delete sanitizedPayload.company_data.api_key;
    }
    
    // Create base context structure
    const context = {
      frontend_payload: sanitizedPayload,
      wa_company_data_payload: {
        company_name: companyData.company_name,
        project_name: companyData.project_name,
        project_status: companyData.project_status,
        allowed_channels: companyData.allowed_channels,
        company_rep: companyData.company_rep || {
          company_rep_1: null,
          company_rep_2: null,
          company_rep_3: null,
          company_rep_4: null,
          company_rep_5: null
        }
      },
      project_rate_limits: companyData.rate_limits,
      channel_config: {},
      ai_config: {},
      metadata: {
        router_version: process.env.VERSION || '1.0.0'
      }
    };
    
    // Add channel-specific configuration (only credential references, not the credentials themselves)
    if (companyData.channel_config) {
      context.channel_config = companyData.channel_config;
    }
    
    // Add AI configuration (only the assistant IDs, not the API key)
    if (companyData.ai_config) {
      context.ai_config = {
        assistant_id_template_sender: companyData.ai_config.assistant_id_template_sender,
        assistant_id_replies: companyData.ai_config.assistant_id_replies,
        assistant_id_3: companyData.ai_config.assistant_id_3 || "",
        assistant_id_4: companyData.ai_config.assistant_id_4 || "",
        assistant_id_5: companyData.ai_config.assistant_id_5 || "",
        ai_api_key_reference: companyData.ai_config.ai_api_key_reference
      };
    }
    
    return context;
  }
};

function getChannelQueueUrl(channelMethod) {
  // Channel queue mapping logic
  const queueMap = {
    'whatsapp': process.env.WHATSAPP_QUEUE_URL,
    'email': process.env.EMAIL_QUEUE_URL,
    'sms': process.env.SMS_QUEUE_URL
  };
  
  if (!queueMap[channelMethod]) {
    throw new Error(`Unsupported channel: ${channelMethod}`);
  }
  
  return queueMap[channelMethod];
}

async function sendToQueue(queueUrl, contextObject) {
  // SQS message sending logic
  const params = {
    QueueUrl: queueUrl,
    MessageBody: JSON.stringify(contextObject),
    MessageDeduplicationId: contextObject.frontend_payload.request_data.request_id, // For FIFO queues
    MessageGroupId: contextObject.frontend_payload.company_data.company_id // For FIFO queues
  };
  
  return await sqs.sendMessage(params).promise();
}

function formatSuccessResponse(requestId) {
  // Success response formatting
  return {
    statusCode: 200,
    body: JSON.stringify({
      status: 'success',
      request_id: requestId,
      message: 'Request accepted and queued for processing',
      queue_timestamp: new Date().toISOString()
    })
  };
}

function formatErrorResponse(error, requestId) {
  // Error response formatting
  // Map different error types to appropriate status codes and messages
}

// Function to validate project constraints
function validateConstraints(companyData, payload) {
  const channelMethod = payload.request_data.channel_method;
  
  // Check if project is active
  if (companyData.project_status !== 'active') {
    throw new Error(`Project is not active. Current status: ${companyData.project_status}`);
  }
  
  // Check if requested channel is in allowed channels
  if (!companyData.allowed_channels.includes(channelMethod)) {
    throw new Error(`Channel method ${channelMethod} is not allowed for this project`);
  }
  
  // Note: Rate limits from companyData.rate_limits are not currently enforced
  // They are included in the context object for future implementation
}

### 3.6.6 Router Version Management

The `router_version` field included in the context object's metadata section identifies which version of the Channel Router processed each request. This information is stored in conversation records for debugging and tracing purposes.

The router version should follow the documentation versioning convention, matching the suffix of the Channel Router documentation file (e.g., "1.0" from "channel-router-documentation-v1.0.md").

```javascript
// In the context creation function
const context = {
  // ...other context fields
  metadata: {
    router_version: process.env.VERSION || '1.0.0'
  }
};
```

This approach provides a simple, straightforward way to track router versions while minimizing management overhead. The VERSION environment variable should be updated whenever the documentation version changes, with a fallback to "1.0.0" if not specified.

### 4.2 API Key Security Implementation

We implement a hybrid approach using both DynamoDB and AWS Secrets Manager for API key security:

1. **DynamoDB Table Structure (`wa_company_data`)**:
   ```json
   {
     "company_id": "company-123",           // Partition key
     "project_id": "project-456",           // Sort key
     "company_name": "Example Corp",
     "project_name": "Recruitment Bot",
     "api_key_reference": "secret/api-keys/company-123/project-456",  // Reference to Secrets Manager
     "allowed_channels": ["whatsapp", "email"],
     "rate_limits": {
       "requests_per_minute": 100,
       "requests_per_day": 10000
     },
     "status": "active",
     "channel_config": {
       "whatsapp": {
         "whatsapp_credentials_id": "twilio/company-123/project-456/whatsapp-credentials",
         "company_whatsapp_number": "+14155238886"
       },
       "sms": {
         "sms_credentials_id": "twilio/company-123/project-456/sms-credentials"
       },
       "email": {
         "email_credentials_id": "sendgrid/company-123/project-456/email-credentials"
       }
     },
     "created_at": "2023-06-15T14:30:45.123Z",
     "updated_at": "2023-06-15T14:30:45.123Z"
   }
   ```

2. **AWS Secrets Manager**:
   - Store the actual API keys in Secrets Manager using the reference path
   - Example secret path: `secret/api-keys/company-123/project-456`
   - Secret content: `{"api_key": "ak_c7d4e8f9a2b1..."}`
   - Configure automatic rotation policies (e.g., every 90 days)
   - Enable detailed audit logging for all access attempts

3. **Security Benefits**:
   - Actual API keys never stored in application database
   - Fine-grained access controls and audit logs for key access
   - Automatic key rotation without changing application code
   - Reduced blast radius if DynamoDB table is compromised
   - Separation of metadata from sensitive credentials

4. **Implementation Considerations**:
   - Cache API key validations briefly (1-5 minutes) to reduce Secrets Manager calls
   - Implement proper error handling for Secrets Manager service disruptions
   - Set up appropriate IAM roles with least privilege for the Lambda function
   - Configure alerts for suspicious access patterns

### 4.3 Message Queue Configuration

Each channel will have its own SQS queue with the following configuration:

#### 4.3.1 Queue Structure

- **Standard SQS Queue**: For each channel (WhatsApp, Email, SMS)
- **Visibility Timeout**: 
  - Set to 600 seconds (10 minutes) for all queues
  - Provides ample time for external API processing, even with delays
  - Works with the heartbeat pattern for handling exceptionally long processing times

- **Dead Letter Queue (DLQ)**: 
  - Create a dedicated DLQ for each channel queue (WhatsApp, SMS, Email)
  - Set Max Receive Count to 3 attempts
    - Provides sufficient retry opportunities for transient failures
    - Balances retry attempts with timely failure handling
    - Appropriate for external API dependencies like OpenAI
  - Set Retention Period to 14 days (maximum allowed)
    - Provides ample time for investigation and troubleshooting
    - Allows for manual reprocessing even after weekends or holidays
    - Ensures no messages are lost before they can be analyzed

#### 4.3.2 Processing Configuration

1. **Batch Size**:
   - Set to 1 message per Lambda invocation
   - Prioritizes reliability over cost efficiency
   - Prevents cascading delays when OpenAI API experiences latency
   - Reduces risk of Lambda timeouts during external API calls
   - Appropriate for our current scale with low message volume

2. **Batch Window**:
   - Set to 0 seconds (default)
   - Ensures immediate processing of messages without artificial delay
   - Prioritizes timely message delivery over minor cost savings
   - Provides consistent, predictable processing behavior
   - Appropriate for time-sensitive WhatsApp communications

3. **Heartbeat Pattern Implementation**:
   - Implement code to extend visibility timeout periodically during long-running operations
   - Run the heartbeat every 300 seconds (5 minutes)
   - Extend visibility timeout by another 600 seconds (10 minutes) each time
   - Provides protection against exceptionally long OpenAI processing times
   - Ensures messages don't become visible to other consumers while still being processed

#### 4.3.3 DLQ Monitoring and Management

1. **DLQ Monitoring Dashboard**:
   - Create a dedicated CloudWatch dashboard for DLQ monitoring
   - Include the following metrics:
     - Number of messages in each DLQ
     - Age of oldest message in DLQ
     - Trend of messages sent to DLQ over time
     - Related Lambda errors and throttling events
   - Add quick links to logs and investigation tools
   - Make dashboard accessible to operations and development teams

2. **DLQ Investigation Procedure**:
   - Develop and document a formal procedure for investigating DLQ messages
   - Include steps for:
     - Viewing message contents and metadata
     - Accessing related CloudWatch logs
     - Identifying common failure patterns
     - Determining if failure is due to code, configuration, or external dependencies
     - Decision tree for appropriate remediation actions
   - Create tools for reprocessing messages from DLQ to main queue when appropriate
   - Establish regular review process for DLQ messages to identify patterns
   - Document common failure scenarios and their solutions for knowledge sharing

3. **DLQ Alarms**:
   - Implement CloudWatch alarms for any messages appearing in DLQs
   - Set threshold to 1 message (alert on any failures)
   - Configure notifications to operations team

### 4.4 API Gateway Configuration

The API Gateway for the Channel Router will be configured with:

- **CORS**: Enabled for frontend domains
- **Authentication**: API key validation
- **Rate Limiting**: 10 requests per second with burst limit of 20
- **Request Validation**: JSON schema validation for incoming payloads
- **Response Templates**: For consistent response formatting

### 4.5 DynamoDB Configuration

1. **Capacity Mode**:
   - Use On-Demand capacity mode
   - Simplifies management and automatically scales with your traffic
   - No need to predict capacity requirements
   - Cost-effective for your current scale with low, unpredictable traffic
   - Eliminates the need to monitor and adjust capacity
   - Automatically handles any traffic spikes without throttling

2. **Data Protection**:
   - Enable Point-in-Time Recovery for all tables
   - Provides continuous backups of your table data
   - Allows restoration to any point in the last 35 days
   - Critical for configuration data like API keys and company information
   - Small additional cost is worth the data protection

3. **Basic Monitoring Setup**:
   - Create a CloudWatch dashboard for DynamoDB monitoring with:
     - Read and write capacity consumption trends
     - Operation latency metrics
     - Error counts (system errors, user errors, throttled requests)
     - Table size and item count growth
   - Set up CloudWatch alarms for:
     - Any system errors (threshold > 0 for 5 minutes)
     - Unusually high consumption (e.g., > 100 units sustained for 15 minutes)
     - Increased latency (e.g., > 50ms for GetItem operations)
   - Configure notifications for these alarms

4. **Access Pattern Optimization**:
   - Design queries to use the partition key whenever possible
   - Avoid table scans, especially as data grows
   - Use sparse indexes for queries on attributes not present in all items
   - Implement efficient key design based on access patterns

5. **Regular Review Process**:
   - Weekly review of monitoring dashboard for unusual patterns
   - Monthly cost analysis and comparison to previous periods
   - Quarterly evaluation of access patterns and potential optimizations
   - Reevaluate capacity mode when usage becomes more predictable or costs increase

### 4.6 IAM Role Permissions

The Lambda function will require the following permissions, all of which will be automatically configured through CDK:

1. **SQS SendMessage**
   - **Purpose**: To place messages in channel-specific queues (WhatsAppQueue, EmailQueue, SMSQueue)
   - **Scope**: Limited to only the specific queues used by the router
   - **Implementation**: `whatsappQueue.grantSendMessages(routerFunction)`

2. **DynamoDB GetItem**
   - **Purpose**: To query the `wa_company_data` table for API key validation and company/project permissions
   - **Scope**: Read-only access to the company data table
   - **Implementation**: `companyTable.grantReadData(routerFunction)`
3. **Secrets Manager GetSecretValue**
   - **Purpose**: To retrieve API keys referenced in the DynamoDB table
   - **Scope**: Limited to specific secrets used for API key storage
   - **Implementation**: Custom policy statement with `secretsmanager:GetSecretValue` action

4. **CloudWatch Logs**
   - **Purpose**: For logging request details, errors, and performance metrics
   - **Scope**: Create log groups, streams, and put log events
   - **Implementation**: Automatically added by CDK when creating Lambda functions

5. **X-Ray (optional)**
   - **Purpose**: For distributed tracing to analyze request flows
   - **Scope**: Send trace data to X-Ray
   - **Implementation**: Enabled via `tracing: lambda.Tracing.ACTIVE` and appropriate policy

6. **Systems Manager Parameter Store**
   - **Purpose**: For accessing configuration parameters (queue URLs, timeouts, etc.)
   - **Scope**: Read-only access to specific parameters
   - **Implementation**: Custom policy statement with `ssm:GetParameter` action

## 5. Deployment Strategy

### 5.1 Infrastructure as Code

The Channel Router will be deployed using AWS CDK with the following components:

```typescript
// Pseudo-code for CDK deployment

// Dead Letter Queues
const whatsappDlq = new sqs.Queue(this, 'WhatsAppDLQ', {
  retentionPeriod: cdk.Duration.days(14)
});

const emailDlq = new sqs.Queue(this, 'EmailDLQ', {
  retentionPeriod: cdk.Duration.days(14)
});

const smsDlq = new sqs.Queue(this, 'SMSDLQ', {
  retentionPeriod: cdk.Duration.days(14)
});

// Main processing queues
const whatsappQueue = new sqs.Queue(this, 'WhatsAppQueue', {
  visibilityTimeout: cdk.Duration.seconds(600), // 10 minutes
  deadLetterQueue: {
    queue: whatsappDlq,
    maxReceiveCount: 3
  }
});

const emailQueue = new sqs.Queue(this, 'EmailQueue', {
  visibilityTimeout: cdk.Duration.seconds(600), // 10 minutes
  deadLetterQueue: {
    queue: emailDlq,
    maxReceiveCount: 3
  }
});

const smsQueue = new sqs.Queue(this, 'SMSQueue', {
  visibilityTimeout: cdk.Duration.seconds(600), // 10 minutes
  deadLetterQueue: {
    queue: smsDlq,
    maxReceiveCount: 3
  }
});

// Company data table
const companyTable = new dynamodb.Table(this, 'CompanyTable', {
  partitionKey: { name: 'company_id', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'project_id', type: dynamodb.AttributeType.STRING },
  tableName: 'wa_company_data',
  billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
  pointInTimeRecovery: true // Enable point-in-time recovery
});

// API Gateway
const api = new apigateway.RestApi(this, 'ChannelRouterApi', {
  // API Gateway configuration with rate limiting
  deployOptions: {
    throttlingRateLimit: 10, // 10 requests per second
    throttlingBurstLimit: 20 // 20 concurrent requests
  }
});

// Router Lambda with X-Ray tracing enabled
const routerFunction = new lambda.Function(this, 'ChannelRouterFunction', {
  runtime: lambda.Runtime.NODEJS_14_X,
  handler: 'index.handler',
  code: lambda.Code.fromAsset('lambda'),
  tracing: lambda.Tracing.ACTIVE,
  timeout: cdk.Duration.seconds(30), // 30 seconds is sufficient for routing operations
  // No concurrency limit as we rely on API Gateway rate limiting
  environment: {
    WHATSAPP_QUEUE_URL: whatsappQueue.queueUrl,
    EMAIL_QUEUE_URL: emailQueue.queueUrl,
    SMS_QUEUE_URL: smsQueue.queueUrl
  }
});

// Grant SQS permissions
whatsappQueue.grantSendMessages(routerFunction);
emailQueue.grantSendMessages(routerFunction);
smsQueue.grantSendMessages(routerFunction);

// Grant DynamoDB permissions
companyTable.grantReadData(routerFunction);

// Add Secrets Manager permissions
routerFunction.addToRolePolicy(new iam.PolicyStatement({
  actions: ['secretsmanager:GetSecretValue'],
  resources: [`arn:aws:secretsmanager:${this.region}:${this.account}:secret:api-keys/*`]
}));

// Add Parameter Store permissions
routerFunction.addToRolePolicy(new iam.PolicyStatement({
  actions: ['ssm:GetParameter', 'ssm:GetParameters'],
  resources: [`arn:aws:ssm:${this.region}:${this.account}:parameter/channel-router/*`]
}));

// API Gateway integration
const routerIntegration = new apigateway.LambdaIntegration(routerFunction);
api.root.addMethod('POST', routerIntegration, {
  // Method configuration
});

// CloudWatch alarms for DLQs
new cloudwatch.Alarm(this, 'WhatsAppDLQAlarm', {
  metric: whatsappDlq.metricApproximateNumberOfMessagesVisible(),
  threshold: 1,
  evaluationPeriods: 1,
  alarmDescription: 'Messages in WhatsApp DLQ'
});

// Similar alarms for other DLQs
new cloudwatch.Alarm(this, 'EmailDLQAlarm', {
  metric: emailDlq.metricApproximateNumberOfMessagesVisible(),
  threshold: 1,
  evaluationPeriods: 1,
  alarmDescription: 'Messages in Email DLQ'
});

new cloudwatch.Alarm(this, 'SMSDLQAlarm', {
  metric: smsDlq.metricApproximateNumberOfMessagesVisible(),
  threshold: 1,
  evaluationPeriods: 1,
  alarmDescription: 'Messages in SMS DLQ'
});

// API Gateway throttling alarm
new cloudwatch.Alarm(this, 'ApiGatewayThrottlingAlarm', {
  metric: api.metricCount({
    period: cdk.Duration.minutes(1),
    statistic: 'Sum',
    dimensionsMap: {
      'ApiName': 'ChannelRouterApi',
      'Stage': 'prod'
    }
  }),
  threshold: 100,
  evaluationPeriods: 1,
  alarmDescription: 'High throttling events for Channel Router API'
});
```

### 5.2 Implementation Plan

1. Configure API Gateway with the throttling settings (10 req/sec, 20 burst)
2. Configure Channel Router Lambda with 30-second timeout
3. Configure SQS queues with visibility timeout of 600 seconds
4. Set up DLQs with appropriate configuration and monitoring
5. Create DLQ monitoring dashboard and investigation procedures
6. Configure DynamoDB tables with on-demand capacity and point-in-time recovery
7. Create DynamoDB monitoring dashboard and alarms
8. Set up basic CloudWatch alarms for monitoring
9. Keep the DynamoDB schema as is for future flexibility
10. Export queue ARNs for use by separate processing engine services

### 5.3 Deployment Phases

1. **Development**: Deploy to development environment for testing
2. **Staging**: Deploy to staging for integration testing
3. **Production**: Deploy to production with proper monitoring

### 5.4 Rollback Strategy

In case of deployment issues:
- Automated rollback on deployment failure
- Manual rollback capability through CloudFormation
- Blue/Green deployment for zero-downtime updates

## 6. Testing Strategy

### 6.1 Unit Testing

Unit tests will cover:
- Request validation (including UUID and timestamp validation)
- Authentication logic
- Queue selection logic
- Error handling
- Response formatting

### 6.2 Integration Testing

Integration tests will verify:
- End-to-end request flow
- Proper message placement in queues
- Error scenarios
- Authentication and authorization
- Message visibility and processing

### 6.3 Load Testing

Load tests will ensure:
- Performance under expected load
- Queue throughput capabilities
- Scalability for peak traffic
- Response time within acceptable limits

## 7. Security Considerations

### 7.1 Authentication and Authorization

- API key validation for all requests using the hybrid DynamoDB/Secrets Manager approach
- IAM roles with least privilege principle
- Secrets management for sensitive information
- Automatic key rotation policies

### 7.2 Data Protection

- Encryption in transit (HTTPS)
- Encryption at rest for queue messages and secrets
- No persistent storage of sensitive data in the router
- Proper error handling to prevent information leakage

### 7.3 Audit and Compliance

- Comprehensive logging for audit trails
- Regular security reviews
- Compliance with relevant regulations

## 8. Operational Considerations

### 8.1 Monitoring

- CloudWatch dashboards for key metrics:
  - Queue depth by channel
  - Processing latency
  - Error rates
  - DLQ message count
- Alarms for error rates and latency
- Log analysis for troubleshooting
- Dedicated DLQ monitoring dashboard
- DynamoDB monitoring dashboard

### 8.2 Scaling

- Auto-scaling based on request volume
- Throttling to prevent queue overload
- Reserved concurrency for Lambda functions

### 8.3 Disaster Recovery

- Multi-region deployment (optional)
- Regular backup of configuration
- Documented recovery procedures
- DLQ message inspection and reprocessing procedures
- Point-in-time recovery for DynamoDB tables

## 9. Future Enhancements

1. **Dynamic Channel Registration**: Allow new channels to be registered without code changes
2. **Traffic Splitting**: Support for A/B testing between different channel implementations
3. **Enhanced Analytics**: Detailed analytics on channel usage and performance
4. **Circuit Breaker Pattern**: Prevent cascading failures when a channel implementation is unavailable
5. **Webhook Support**: Allow channel implementations to send asynchronous responses via webhooks
6. **Caching Layer**: Add caching for improved performance
7. **GraphQL Interface**: Provide a GraphQL API for more flexible frontend integration
8. **Message Prioritization**: Priority queues for urgent messages
9. **Cost Optimization**: Batch processing for similar messages
10. **Regulatory Compliance**: Enhanced support for channel-specific regulations
11. **Enhanced Usage Tracking**:
    - Create a separate DynamoDB table for tracking usage
    - Implement asynchronous processing of usage data
    - Generate reports and alerts based on usage patterns
12. **Per-Client Rate Limiting**:
    - Enforce the rate limits stored in the DynamoDB schema
    - Implement more granular controls for different clients
    - Add graduated response mechanisms
13. **Advanced Protection**:
    - Implement AWS WAF for additional security
    - Add IP-based rate limiting
    - Create automated incident response mechanisms
14. **SQS Optimization**:
    - Revisit batch size based on performance data
    - Consider increasing to 2-3 if OpenAI response times are consistently good
    - Evaluate batch window settings if message volume increases significantly
    - Implement more sophisticated error handling for different failure types
15. **Processing Time Analytics**:
    - Collect detailed metrics on OpenAI response times
    - Analyze patterns to optimize timeout settings
    - Implement adaptive timeout strategies based on real-world data
16. **Automated DLQ Processing**:
    - Develop intelligent retry mechanisms for DLQ messages
    - Implement automatic categorization of failure types
    - Create self-healing systems for common failure patterns
17. **DynamoDB Capacity Mode Reevaluation**:
    - Switch to provisioned capacity when usage patterns become predictable
    - Implement auto-scaling for provisioned capacity
    - Consider reserved capacity for cost optimization
    - Implement more sophisticated partitioning strategies for high-scale tables

## 10. Appendix

### 10.1 Glossary

- **Channel Method**: The communication method specified in the payload (whatsapp, email, sms)
- **Channel Queue**: SQS queue dedicated to a specific channel
- **Dead Letter Queue (DLQ)**: Queue for messages that fail processing multiple times
- **Router**: The component that directs requests to the appropriate channel queue
- **Payload**: The JSON data sent from the frontend application
- **Visibility Timeout**: How long a message is invisible during processing
- **Request ID**: UUID v4 used for idempotency and tracing
- **API Key Reference**: Path to the actual API key stored in Secrets Manager
- **Heartbeat Pattern**: A technique to extend visibility timeout for long-running operations
- **Burst Limit**: Maximum number of concurrent requests allowed in a short time period
- **Point-in-Time Recovery**: DynamoDB feature that enables continuous backups

### 10.2 References

- AWS Lambda documentation
- AWS API Gateway documentation
- AWS SQS documentation
- AWS Secrets Manager documentation
- Frontend documentation
- System architecture diagrams
- Message Queue Architecture documentation
- AWS DynamoDB documentation
- AWS CloudWatch documentation

