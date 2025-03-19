# WhatsApp Processing Engine - Low-Level Design Documentation

> **Channel Integration Decisions**:
> - **WhatsApp**: Twilio WhatsApp API
> - **SMS**: Twilio SMS API
> - **Email**: SendGrid API

## 1. Introduction

This document provides a detailed description of the WhatsApp Processing Engine component of the WhatsApp AI chatbot system. It is part of a series of low-level design documents, with similar documents existing for each channel processing engine (SMS, Email, Whatsapp). Each processing engine operates independently but follows the similar architectural patterns.

### 1.1 Channel Routing Process

The Channel Router, which sits upstream of all processing engines, determines which channel queue a request is routed to based on the `channel_method` field in the incoming payload's `request_data` object. When a frontend application sends a request, it specifies the desired communication channel (e.g., "whatsapp", "email", "sms") in this field.

The routing process works as follows:

1. Frontend applications send a standardized payload to the Channel Router's API endpoint
2. The Channel Router validates the request structure and authenticates the API key
3. The Router examines the `channel_method` value in the `request_data` object
4. Based on this value, the Router creates a context object with all necessary processing information
5. This context object is then placed in the corresponding channel-specific SQS queue (WhatsApp, SMS, or Email)
6. The appropriate channel processing engine retrieves the message from its designated queue

The WhatsApp Processing Engine specifically is responsible for consuming messages from the WhatsApp SQS queue (populated by the Channel Router), processing them through the OpenAI API, and delivering responses to end users via the Twilio WhatsApp API. This design enables a modular architecture that separates concerns between routing and processing while providing resilience through asynchronous processing.

## 2. Architecture Overview

### 2.1 Component Purpose

The WhatsApp Processing Engine is responsible for:

- Consuming messages from the WhatsApp SQS queue
- Implementing the heartbeat pattern for long-running operations
- Creating and managing conversations in DynamoDB
- Retrieving credentials from AWS Secrets Manager using references provided in the context object
- Processing messages using the OpenAI Assistants API
- Delivering messages to end users via Twilio
- Handling failures and retries appropriately
- Providing detailed logging and monitoring

### 2.2 Position in System Architecture

The WhatsApp Processing Engine sits between:
- **Upstream**: Channel Router (via WhatsApp SQS queue)
- **Downstream**: OpenAI API and Twilio WhatsApp API

```
Channel Router → WhatsApp SQS Queue → WhatsApp Processing Engine → OpenAI API → Twilio API → End User
```

### 2.3 Technical Implementation

The WhatsApp Processing Engine will be implemented as:

- **Lambda Function**: Triggered by messages in the WhatsApp SQS queue
- **SQS Event Source**: Configured with batch size 1 for reliable processing
- **DynamoDB Access**: For conversation record creation and management
- **OpenAI Integration**: For AI-powered message processing
- **Twilio Integration**: For WhatsApp message delivery
- **Heartbeat Pattern**: For extending visibility timeout during long-running operations
- **CloudWatch**: For monitoring and logging operations
- **AWS Secrets Manager**: For securely accessing API keys

## 3. Detailed Design

### 3.1 Processing Flow

1. **SQS Message Consumption**:
   - Lambda is triggered by a new message in the WhatsApp SQS queue
   - Message becomes invisible for the configured visibility timeout (600s)
   - Only one message is processed at a time (batch size: 1)
   - Lambda immediately sets up the heartbeat pattern to extend visibility timeout every 5 minutes

2. **Context Object Parsing**:
   - Lambda parses the context object which contains:
     - `frontend_payload`: Original request from the frontend
     - `db_payload`: Company/project data from DynamoDB 
     - `channel_config`: Channel-specific configurations
     - `ai_config`: OpenAI assistant configurations
     - `metadata`: Additional context information including:
        - `context_creation_timestamp`: When the context object was created
        - `router_version`: Version of the Channel Router that created the context
        - `request_id`: Same as the request_id in the frontend_payload (for easy access)
     - `project_rate_limits`: Rate limiting configuration for the project

3. **Conversation Record Creation**:
   - A composite key structure is used for the conversation table
   - Primary key would be `recipient_tel` (recipient's phone number)
   - Sort key would be `conversation_id` (which incorporates the company's WhatsApp number)
   - The `conversation_id` follows this format: `{company_id}#{project_id}#{request_id}#{company_whatsapp_number}`
   - This structure ensures uniqueness across all conversations while facilitating efficient queries
   - Including the `project_id` in the conversation_id is critical for companies with multiple projects
   - The company WhatsApp number is obtained from the `channel_config.whatsapp.company_whatsapp_number` field

4. **Channel Configuration Access**:
   - The company's WhatsApp number is stored in the `channel_config.whatsapp.company_whatsapp_number` object in DynamoDB wa_company_data table rather than in Secrets Manager
   - This makes sense as the phone number itself isn't sensitive credentials (unlike API keys)
   - Makes it easier to create the conversation record without additional Secrets Manager calls
   - The actual Twilio credentials are retrieved from AWS Secrets Manager using the reference `channel_config.whatsapp.whatsapp_credentials_id`

5. **Multi-Channel Support in Conversations Table**:
   - A `channel_method` field is included in every record to indicate the communication channel (whatsapp, sms, email)
   - Each channel requires a different approach to key structure and conversation identification:
   
   **WhatsApp Channel:**
   - Primary Key: `recipient_tel` (recipient's phone number)
   - Sort Key: `conversation_id` with format: `{company_id}#{project_id}#{request_id}#{company_whatsapp_number}`
   - Reply Identification: Match on recipient phone number and company WhatsApp number
   
   **SMS Channel:**
   - Primary Key: `recipient_tel` (recipient's phone number)
   - Sort Key: `conversation_id` with format: `{company_id}#{project_id}#{request_id}#{company_sms_number}`
   - Reply Identification: Match on recipient phone number and company SMS number
   
   **Email Channel:**
   - Primary Key: `recipient_email` (recipient's email address)
   - Sort Key: `conversation_id` with format: `{company_id}#{project_id}#{request_id}#{message_id}`
   - Where `message_id` would be a unique identifier for the email thread (e.g., Message-ID header)
   - Reply Identification: Use of email threading headers (References, In-Reply-To) to match to original message

6. **Status Tracking**:
   - Once the conversation record is created, the status is set to "received"
   - Status is updated to "processing" before initiating the OpenAI API call
   - Additional status updates occur throughout processing (ai_completed, delivery_initiated, etc.)

7. **API Credentials Retrieval**:
   - Get OpenAI and Twilio credentials from AWS Secrets Manager using the credential references from the context object

8. **API Client Initialization**:
   - Create OpenAI and Twilio API client instances with the retrieved credentials

9. **OpenAI Processing**:
   - Create or retrieve OpenAI thread ID
   - Add user message to the thread
   - Run the assistant on the thread
   - Process the assistant's response

10. **Twilio Delivery**:
    - Format the response for WhatsApp
    - Send the message via Twilio API
    - Handle delivery status and errors

11. **Completion**:
    - On success: Delete message from SQS queue, update status to "completed"
    - On transient failure: Allow retry via SQS visibility timeout
    - On permanent failure: Move to Dead Letter Queue after max retries

### 3.2 Lambda Function Configuration

1. **Runtime**: Node.js 14.x
2. **Memory**: 1024 MB (adjustable based on performance testing)
3. **Timeout**: 900 seconds (15 minutes, maximum allowed)
4. **Concurrency Limit**: 20-30 concurrent executions
5. **Environment Variables**:
   ```
   COMPANY_TABLE_NAME=wa_company_data
   CONVERSATION_TABLE_NAME=wa_conversation
   OPENAI_API_KEY_SECRET_NAME=openai/api-key
   TWILIO_ACCOUNT_SID_SECRET_NAME=twilio/account-sid
   TWILIO_AUTH_TOKEN_SECRET_NAME=twilio/auth-token
   WHATSAPP_QUEUE_URL=https://sqs.{region}.amazonaws.com/{account}/WhatsAppQueue
   ```

### 3.3 SQS Event Source Configuration

1. **Batch Size**: 1 message per Lambda invocation
   - Prioritizes reliability over cost efficiency
   - Prevents cascading delays when OpenAI API experiences latency
   - Reduces risk of Lambda timeouts during external API calls

2. **Batch Window**: 0 seconds
   - Ensures immediate processing of messages without artificial delay
   - Prioritizes timely message delivery over minor cost savings

3. **Visibility Timeout Handling**:
   - Initial visibility timeout: 600 seconds (10 minutes)
   - Extended via heartbeat pattern during processing
   - Provides protection against exceptionally long OpenAI processing times

### 3.4 Heartbeat Pattern Implementation

```javascript
// Pseudo-code for heartbeat pattern
exports.handler = async (event) => {
  // Get the SQS message
  const message = event.Records[0];
  const receiptHandle = message.receiptHandle;
  
  // Set up heartbeat timer
  const heartbeatInterval = setInterval(async () => {
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
  }, 300000); // 5 minutes
  
  try {
    // Process the message (company lookup, OpenAI, Twilio, etc.)
    // ...
    
    // Clean up and delete message on success
    clearInterval(heartbeatInterval);
    await sqs.deleteMessage({
      QueueUrl: process.env.WHATSAPP_QUEUE_URL,
      ReceiptHandle: receiptHandle
    }).promise();
    
    return { statusCode: 200 };
  } catch (error) {
    // Clean up heartbeat timer
    clearInterval(heartbeatInterval);
    
    // For permanent errors, we could move to DLQ manually
    // For transient errors, we let the message return to the queue
    console.error('Processing error:', error);
    throw error; // This will cause the Lambda to fail and SQS to retry
  }
};
```

### 3.5 Error Handling Strategy

1. **Transient Errors** (retry-able):
   - OpenAI API rate limiting or temporary unavailability
   - Twilio API temporary issues
   - Network connectivity problems
   - DynamoDB throttling
   - **Handling**: Allow SQS retry mechanism to work (up to 3 attempts)

2. **Permanent Errors** (non-retry-able):
   - Invalid message format
   - Missing required configuration
   - Authentication failures with external APIs
   - Business logic errors
   - **Handling**: Log detailed error information and allow message to move to DLQ after max retries

3. **Partial Success Scenarios**:
   - OpenAI processed but Twilio delivery failed
   - **Handling**: Store the OpenAI response in DynamoDB and retry only the Twilio portion

### 3.6 Conversation Status Tracking Lifecycle

A core feature of the WhatsApp Processing Engine is the detailed tracking of conversation states throughout the processing lifecycle. This hybrid approach creates and updates conversation records at key milestones, providing complete visibility into the processing pipeline and enabling recovery capabilities.

#### 3.6.1 Conversation Status States

The conversation_status field will track the following states:

1. **received**: Initial state when message is first retrieved from the queue
2. **processing**: OpenAI processing has begun
3. **ai_completed**: OpenAI processing completed successfully
4. **delivery_initiated**: Message sent to Twilio for delivery
5. **delivered**: Message successfully delivered to recipient
6. **failed_processing**: Failed during OpenAI processing
7. **failed_delivery**: Failed during Twilio delivery
8. **recovery_pending**: Marked for manual review and potential recovery
9. **completed**: Entire conversation cycle completed successfully

#### 3.6.2 Status Transition Points

| Processing Stage | Status Update | Timing |
|------------------|---------------|--------|
| Message Consumption | received | Immediately after retrieving from SQS and before any processing |
| OpenAI Processing Start | processing | Before making OpenAI API call |
| OpenAI Processing Complete | ai_completed | After successful OpenAI response |
| Twilio Delivery Start | delivery_initiated | Before making Twilio API call |
| Twilio Delivery Complete | delivered | After successful Twilio delivery confirmation |
| OpenAI Processing Error | failed_processing | When OpenAI processing fails |
| Twilio Delivery Error | failed_delivery | When Twilio delivery fails |
| SQS Max Retry Exceeded | recovery_pending | When message is moved to DLQ |
| Complete Success | completed | After all steps completed successfully |

#### 3.6.3 Recovery Process

For conversations that reach failed states:
1. DLQ dashboard alerts operations team
2. Team reviews the conversation record and error details
3. Based on failure point, conversation can be reprocessed from last successful state
4. Manual intervention may be required for specific error types
5. Status is updated to reflect recovery attempt

### 3.7 DynamoDB Schema

#### 3.7.1 Conversation Table

```json
{
  "recipient_tel": "string", // Partition key for WhatsApp/SMS
  "recipient_email": "string", // Partition key for Email (only one of tel/email will be used)
  "conversation_id": "string", // Sort key
  "company_id": "string",
  "project_id": "string",
  "channel_method": "whatsapp|sms|email",
  "company_phone_number": "string", // For WhatsApp/SMS channels
  "company_email": "string", // For Email channel
  "message_id": "string", // For Email - unique message identifier for threading
  "credentials_reference": "string", // Reference to credentials in Secrets Manager
  "thread_id": "string", // OpenAI thread ID
  "request_id": "string", // Original request_id from frontend
  "recipient_first_name": "string",
  "recipient_last_name": "string",
  "messages": [
    {
      "message_id": "string",
      "direction": "inbound|outbound",
      "content": "string",
      "timestamp": "string",
      "status": "string",
      "channel_message_id": "string", // Twilio/SendGrid message ID
      "metadata": {
        // Channel-specific message metadata
      }
    }
  ],
  "processing_metadata": {
    "conversation_status": "received|processing|ai_completed|delivery_initiated|delivered|failed_processing|failed_delivery|recovery_pending|completed",
    "processing_started_at": "string",
    "ai_completed_at": "string",
    "delivery_initiated_at": "string",
    "delivery_completed_at": "string",
    "last_status_change": "string",
    "retry_count": 0,
    "error_details": {
      "error_type": "string",
      "error_message": "string",
      "error_timestamp": "string",
      "component": "string" // Which component failed (openai, twilio, etc.)
    }
  },
  "ai_metadata": {
    "assistant_id": "string",
    "model": "string",
    "completion_tokens": 0,
    "prompt_tokens": 0,
    "total_tokens": 0,
    "processing_time_ms": 0
  },
  "created_at": "string",
  "updated_at": "string"
}
```

## 4. Implementation Details

### 4.1 Lambda Function Structure

```javascript
// Pseudo-code for the WhatsApp Processing Lambda function

// Import dependencies
const AWS = require('aws-sdk');
const { OpenAI } = require('openai');
const twilio = require('twilio');

// Initialize AWS services
const sqs = new AWS.SQS();
const dynamoDB = new AWS.DynamoDB.DocumentClient();
const secretsManager = new AWS.SecretsManager();

// Main handler
exports.handler = async (event) => {
  // Get the SQS message
  const message = event.Records[0];
  const receiptHandle = message.receiptHandle;
  const messageBody = JSON.parse(message.body);
  
  // Set up heartbeat timer
  const heartbeatInterval = setupHeartbeat(receiptHandle);
  
  try {
    // 1. Extract necessary data from context object
    const { frontend_payload, db_payload, channel_config, ai_config, metadata } = messageBody;
    const { company_data, recipient_data, project_data, request_data } = frontend_payload;
    
    // 2. Generate conversation ID based on the channel method
    const conversationId = generateChannelSpecificConversationId(
      company_data.company_id,
      company_data.project_id,
      request_data.request_id,
      channel_config.whatsapp.company_whatsapp_number
    );
    
    // 3. Early write: Create conversation record with "received" status
    const conversation = await createConversationRecord({
      recipient_tel: recipient_data.recipient_tel,
      conversation_id: conversationId,
      company_id: company_data.company_id,
      project_id: company_data.project_id,
      channel_method: 'whatsapp',
      company_phone_number: channel_config.whatsapp.company_whatsapp_number,
      request_id: request_data.request_id,
      credentials_reference: channel_config.whatsapp.whatsapp_credentials_id,
      recipient_data,
      initial_status: 'received'
    });
    
    console.log('Conversation record created', { 
      conversation_id: conversation.conversation_id,
      status: 'received',
      request_id: request_data.request_id
    });
    
    // 4. Get API credentials from Secrets Manager
    const credentials = await getCredentials(channel_config.whatsapp.whatsapp_credentials_id, ai_config);
    
    // 5. Initialize OpenAI and Twilio clients
    const openai = initializeOpenAI(credentials.openaiApiKey);
    const twilioClient = initializeTwilio(credentials.twilioAccountSid, credentials.twilioAuthToken);
    
    // 6. Update status to "processing" before OpenAI processing
    await updateConversationStatus(conversation, 'processing');
    
    // 7. Process with OpenAI
    let aiResponse;
    try {
      aiResponse = await processWithOpenAI(openai, conversation, project_data, ai_config);
      // Update status to "ai_completed" after successful OpenAI processing
      await updateConversationStatus(conversation, 'ai_completed');
    } catch (error) {
      // Update status to "failed_processing" if OpenAI processing fails
      await updateConversationStatus(conversation, 'failed_processing', {
        error_type: error.name,
        error_message: error.message,
        component: 'openai'
      });
      throw error; // Rethrow to trigger retry
    }
    
    // 8. Update status to "delivery_initiated" before Twilio delivery
    await updateConversationStatus(conversation, 'delivery_initiated');
    
    // 9. Send via Twilio
    let deliveryResult;
    try {
      deliveryResult = await sendViaTwilio(twilioClient, recipient_data, aiResponse, channel_config.whatsapp);
      // Update status to "delivered" after successful delivery
      await updateConversationStatus(conversation, 'delivered');
    } catch (error) {
      // Update status to "failed_delivery" if Twilio delivery fails
      await updateConversationStatus(conversation, 'failed_delivery', {
        error_type: error.name,
        error_message: error.message,
        component: 'twilio'
      });
      throw error; // Rethrow to trigger retry
    }
    
    // 10. Final status update to "completed"
    await updateConversationStatus(conversation, 'completed');
    
    // 11. Update conversation with full results
    await updateConversationData(conversation, aiResponse, deliveryResult);
    
    // 12. Clean up and delete message
    clearInterval(heartbeatInterval);
    await deleteMessage(receiptHandle);
    
    return {
      statusCode: 200,
      body: JSON.stringify({
        message: 'Message processed successfully',
        conversation_id: conversation.conversation_id
      })
    };
  } catch (error) {
    // Clean up heartbeat timer
    clearInterval(heartbeatInterval);
    
    // Log error details
    console.error('Processing error:', error);
    
    // Rethrow to trigger SQS retry mechanism
    throw error;
  }
};

// Helper functions

// Set up heartbeat for extending visibility timeout
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
  }, 300000); // 5 minutes
}

// Generate conversation ID based on channel
function generateChannelSpecificConversationId(companyId, projectId, requestId, companyWhatsAppNumber) {
  // Sanitize phone number by removing any non-alphanumeric characters
  const sanitizedCompanyNumber = companyWhatsAppNumber.replace(/\D/g, '');
  
  // Combine into a single string with a delimiter
  return `${companyId}#${projectId}#${requestId}#${sanitizedCompanyNumber}`;
}

// Create new conversation record
async function createConversationRecord({
  recipient_tel,
  conversation_id,
  company_id,
  project_id,
  channel_method,
  company_phone_number,
  request_id,
  credentials_reference,
  recipient_data,
  initial_status
}) {
  const now = new Date().toISOString();
  const newConversation = {
    recipient_tel,
    conversation_id,
    company_id,
    project_id,
    channel_method,
    company_phone_number,
    request_id,
    credentials_reference,
    recipient_first_name: recipient_data.recipient_first_name,
    recipient_last_name: recipient_data.recipient_last_name,
    messages: [],
    processing_metadata: {
      conversation_status: initial_status,
      processing_started_at: now,
      retry_count: 0
    },
    created_at: now,
    updated_at: now
  };
  
  // Save to DynamoDB
  await dynamoDB.put({
    TableName: process.env.CONVERSATION_TABLE_NAME,
    Item: newConversation
  }).promise();
  
  return newConversation;
}

// Update conversation status with appropriate timestamps
async function updateConversationStatus(conversation, status, errorDetails = null) {
  const now = new Date().toISOString();
  const updates = {
    processing_metadata: {
      ...conversation.processing_metadata,
      conversation_status: status,
      last_status_change: now
    },
    updated_at: now
  };
  
  // Add status-specific timestamp
  switch (status) {
    case 'processing':
      updates.processing_metadata.processing_started_at = now;
      break;
    case 'ai_completed':
      updates.processing_metadata.ai_completed_at = now;
      break;
    case 'delivery_initiated':
      updates.processing_metadata.delivery_initiated_at = now;
      break;
    case 'delivered':
      updates.processing_metadata.delivery_completed_at = now;
      break;
  }
  
  // Add error details if provided
  if (errorDetails) {
    updates.processing_metadata.error_details = {
      ...errorDetails,
      error_timestamp: now
    };
    // Increment retry count for failure states
    updates.processing_metadata.retry_count = (conversation.processing_metadata.retry_count || 0) + 1;
  }
  
  // Update in DynamoDB
  await dynamoDB.update({
    TableName: process.env.CONVERSATION_TABLE_NAME,
    Key: {
      recipient_tel: conversation.recipient_tel,
      conversation_id: conversation.conversation_id
    },
    UpdateExpression: 'SET processing_metadata = :metadata, updated_at = :updated',
    ExpressionAttributeValues: {
      ':metadata': updates.processing_metadata,
      ':updated': updates.updated_at
    }
  }).promise();
  
  // Update local conversation object
  conversation.processing_metadata = updates.processing_metadata;
  conversation.updated_at = updates.updated_at;
  
  console.log(`Conversation status updated to ${status}`, {
    conversation_id: conversation.conversation_id,
    status,
    timestamp: now
  });
  
  return conversation;
}

async function getCredentials(channelConfig, aiConfig) {
  // Get API keys from Secrets Manager
}

async function processWithOpenAI(openai, conversation, projectData) {
  // Get or create thread
  let threadId = conversation.thread_id;
  if (!threadId) {
    const thread = await openai.beta.threads.create();
    threadId = thread.id;
  }
  
  // Add message to thread
  await openai.beta.threads.messages.create(threadId, {
    role: 'user',
    content: projectData.message_content
  });
  
  // Run the assistant
  const run = await openai.beta.threads.runs.create(threadId, {
    assistant_id: projectData.assistant_id || conversation.company_data.openai_config.assistant_id
  });
  
  // Poll for completion
  let runStatus = await openai.beta.threads.runs.retrieve(threadId, run.id);
  while (runStatus.status !== 'completed' && runStatus.status !== 'failed') {
    await new Promise(resolve => setTimeout(resolve, 1000));
    runStatus = await openai.beta.threads.runs.retrieve(threadId, run.id);
  }
  
  if (runStatus.status === 'failed') {
    throw new Error(`OpenAI run failed: ${runStatus.last_error}`);
  }
  
  // Get the assistant's response
  const messages = await openai.beta.threads.messages.list(threadId);
  const assistantMessages = messages.data.filter(msg => msg.role === 'assistant');
  const latestMessage = assistantMessages[0];
  
  return {
    thread_id: threadId,
    message_id: latestMessage.id,
    content: latestMessage.content[0].text.value
  };
}

async function sendViaTwilio(twilioClient, recipientData, aiResponse, companyConfig) {
  const twilioConfig = companyConfig.twilio_config;
  
  try {
    const message = await twilioClient.messages.create({
      body: aiResponse.content,
      from: `whatsapp:${twilioConfig.phone_number}`,
      to: `whatsapp:${recipientData.recipient_tel}`
    });
    
    return {
      message_sid: message.sid,
      status: message.status,
      error_code: null,
      error_message: null
    };
  } catch (error) {
    return {
      message_sid: null,
      status: 'failed',
      error_code: error.code,
      error_message: error.message
    };
  }
}

## 5. Infrastructure as Code

### 5.1 CDK Stack

```typescript
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import { SqsEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import { Duration } from 'aws-cdk-lib';

export class WhatsAppEngineStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    
    // Import the WhatsApp queue from the Channel Router stack
    const whatsappQueue = sqs.Queue.fromQueueArn(this, 'ImportedWhatsAppQueue', 
      cdk.Fn.importValue('WhatsAppQueueArn'));
    
    // Import DynamoDB tables
    const companyTable = dynamodb.Table.fromTableName(this, 'ImportedCompanyTable', 'wa_company_data');
    
    // Create conversation table
    const conversationTable = new dynamodb.Table(this, 'ConversationTable', {
      partitionKey: { name: 'phone_number', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'conversation_id', type: dynamodb.AttributeType.STRING },
      tableName: 'wa_conversation',
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true
    });
    
    // Create the WhatsApp processing Lambda
    const whatsappLambda = new lambda.Function(this, 'WhatsAppProcessingFunction', {
      runtime: lambda.Runtime.NODEJS_14_X,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('lambda/whatsapp-engine'),
      timeout: Duration.seconds(900),
      memorySize: 1024,
      reservedConcurrentExecutions: 25,
      environment: {
        COMPANY_TABLE_NAME: companyTable.tableName,
        CONVERSATION_TABLE_NAME: conversationTable.tableName,
        OPENAI_API_KEY_SECRET_NAME: 'openai/api-key',
        TWILIO_ACCOUNT_SID_SECRET_NAME: 'twilio/account-sid',
        TWILIO_AUTH_TOKEN_SECRET_NAME: 'twilio/auth-token',
        WHATSAPP_QUEUE_URL: whatsappQueue.queueUrl
      },
      tracing: lambda.Tracing.ACTIVE
    });
    
    // Set up the SQS trigger
    whatsappLambda.addEventSource(new SqsEventSource(whatsappQueue, {
      batchSize: 1,
      maxBatchingWindow: Duration.seconds(0)
    }));
    
    // Grant permissions
    companyTable.grantReadData(whatsappLambda);
    conversationTable.grantReadWriteData(whatsappLambda);
    whatsappQueue.grantConsumeMessages(whatsappLambda);
    whatsappQueue.grant(whatsappLambda, 'sqs:DeleteMessage', 'sqs:ChangeMessageVisibility');
    
    // Grant Secrets Manager permissions
    whatsappLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['secretsmanager:GetSecretValue'],
      resources: [
        `arn:aws:secretsmanager:${this.region}:${this.account}:secret:openai/*`,
        `arn:aws:secretsmanager:${this.region}:${this.account}:secret:twilio/*`
      ]
    }));
    
    // CloudWatch alarms
    // ...
  }
}
```

## 6. Monitoring and Observability

### 6.1 CloudWatch Metrics

1. **Lambda Metrics**:
   - Invocations
   - Errors
   - Duration
   - Throttles
   - Concurrent executions

2. **SQS Metrics**:
   - ApproximateNumberOfMessagesVisible
   - ApproximateAgeOfOldestMessage
   - NumberOfMessagesSent
   - NumberOfMessagesReceived
   - NumberOfMessagesDeleted

3. **Custom Metrics**:
   - OpenAI API response time
   - Twilio API response time
   - End-to-end processing time
   - Success/failure rates by company

### 6.2 CloudWatch Alarms

1. **Lambda Errors**: Alert if error rate exceeds threshold
2. **Lambda Duration**: Alert if processing time approaches timeout
3. **SQS Message Age**: Alert if messages are not being processed
4. **OpenAI API Failures**: Alert on repeated failures
5. **Twilio API Failures**: Alert on repeated failures

### 6.3 Logging Strategy

1. **Structured Logging**:
   ```javascript
   console.log(JSON.stringify({
     level: 'info',
     message: 'Processing message',
     request_id: requestId,
     company_id: companyId,
     project_id: projectId,
     recipient_tel: recipientTel,
     timestamp: new Date().toISOString()
   }));
   ```

2. **Log Levels**:
   - ERROR: Failures that prevent message processing
   - WARN: Issues that don't prevent processing but require attention
   - INFO: Normal processing events
   - DEBUG: Detailed information for troubleshooting

3. **Key Events to Log**:
   - Message received from SQS
   - Context object parsed
   - Conversation created/updated
   - Secrets retrieved from AWS Secrets Manager
   - OpenAI request/response
   - Twilio request/response
   - Visibility timeout extensions
   - Message deletion
   - Errors and exceptions

## 7. Security Considerations

### 7.1 Data Protection

1. **Encryption**:
   - All data in transit encrypted via HTTPS
   - All data at rest encrypted in DynamoDB and SQS
   - API keys stored in Secrets Manager

2. **Data Minimization**:
   - Store only necessary information in logs
   - Mask sensitive data in logs (phone numbers, etc.)

### 7.2 API Key Management

1. **OpenAI API Key**:
   - Stored in Secrets Manager
   - Rotated regularly
   - Accessed only when needed

2. **Twilio Credentials**:
   - Account SID and Auth Token stored in Secrets Manager
   - Rotated regularly
   - Accessed only when needed

### 7.3 IAM Permissions

1. **Least Privilege Principle**:
   - Lambda has only the permissions it needs
   - Specific resource ARNs in policies
   - No wildcard permissions

## 8. Deployment and Operations

### 8.1 Deployment Pipeline

1. **CI/CD Pipeline**:
   - Source: GitHub repository
   - Build: npm install, test
   - Deploy: CDK deploy

2. **Environment Strategy**:
   - Development: For feature development
   - Staging: For integration testing
   - Production: For live traffic

### 8.2 Operational Procedures

1. **Deployment**:
   - Deploy during low-traffic periods
   - Monitor closely after deployment
   - Have rollback plan ready

2. **Monitoring**:
   - Regular review of CloudWatch dashboards
   - Alert response procedures
   - Performance optimization

3. **Troubleshooting**:
   - Log analysis procedures
   - Common failure scenarios and solutions
   - Escalation path

## 9. Future Enhancements

1. **Performance Optimization**:
   - Caching frequently used company configurations
   - Optimizing OpenAI prompt strategies
   - Fine-tuning Lambda memory allocation

2. **Feature Enhancements**:
   - Media message support (images, audio)
   - Interactive buttons and list messages
   - Location sharing

3. **Scalability Improvements**:
   - Adaptive concurrency limits
   - Regional deployment for global coverage
   - Enhanced rate limiting strategies

4. **Monitoring Enhancements**:
   - Custom CloudWatch dashboard
   - Cost optimization tracking
   - User engagement metrics 