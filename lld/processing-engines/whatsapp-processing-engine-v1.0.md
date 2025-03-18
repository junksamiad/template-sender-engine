# WhatsApp Processing Engine - Low-Level Design Documentation

> **Channel Integration Decisions**:
> - **WhatsApp**: Twilio WhatsApp API
> - **SMS**: Twilio SMS API
> - **Email**: SendGrid API

## 1. Introduction

This document provides a detailed description of the WhatsApp Processing Engine component of the WhatsApp AI chatbot system. The WhatsApp Processing Engine is responsible for consuming messages from the WhatsApp SQS queue (populated by the Channel Router), processing them through the OpenAI API, and delivering responses to end users via the Twilio WhatsApp API. This design enables a modular architecture that separates concerns between routing and processing while providing resilience through asynchronous processing.

## 2. Architecture Overview

### 2.1 Component Purpose

The WhatsApp Processing Engine is responsible for:

- Consuming messages from the WhatsApp SQS queue
- Implementing the heartbeat pattern for long-running operations
- Looking up company configuration from DynamoDB
- Creating and managing conversations in DynamoDB
- Interacting with the OpenAI Assistants API
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
- **DynamoDB Access**: For company configuration and conversation management
- **OpenAI Integration**: For AI-powered message processing
- **Twilio Integration**: For WhatsApp message delivery
- **Heartbeat Pattern**: For extending visibility timeout during long-running operations
- **CloudWatch**: For monitoring and logging operations
- **AWS Secrets Manager**: For securely accessing API keys

## 3. Detailed Design

### 3.1 Processing Flow

1. **Message Consumption**:
   - Lambda is triggered by a new message in the WhatsApp SQS queue
   - Message becomes invisible for the configured visibility timeout (600s)
   - Only one message is processed at a time (batch size: 1)

2. **Heartbeat Setup**:
   - Immediately set up a heartbeat timer to extend visibility timeout
   - Run every 300 seconds (5 minutes)
   - Extend visibility by 600 seconds (10 minutes) each time
   - Ensures message doesn't become visible to other consumers during processing

3. **Company Configuration Lookup**:
   - Extract company_id and project_id from the message
   - Query DynamoDB for company configuration
   - Retrieve OpenAI and Twilio configuration settings

4. **Conversation Management**:
   - Check if conversation exists for the recipient
   - If new conversation, create a new record in DynamoDB
   - If existing conversation, update with new message details

5. **OpenAI Processing**:
   - Create or retrieve OpenAI thread ID
   - Add user message to the thread
   - Run the assistant on the thread
   - Process the assistant's response

6. **Twilio Delivery**:
   - Format the response for WhatsApp
   - Send the message via Twilio API
   - Handle delivery status and errors

7. **Completion**:
   - On success: Delete message from SQS queue
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

### 3.6 DynamoDB Schema

#### 3.6.1 Conversation Table

```json
{
  "phone_number": "string", // Partition key
  "conversation_id": "string", // Sort key
  "company_id": "string",
  "project_id": "string",
  "channel_method": "whatsapp",
  "company_channel_id": "string",
  "account_sid": "string",
  "thread_id": "string", // OpenAI thread ID
  "user_data": {
    "first_name": "string",
    "last_name": "string",
    "email": "string"
  },
  "content_data": {
    // Project-specific content
  },
  "company_data": {
    // Company-specific settings
  },
  "messages": [
    {
      "message_id": "string",
      "direction": "inbound|outbound",
      "content": "string",
      "timestamp": "string",
      "status": "string"
    }
  ],
  "conversation_status": "active|completed|failed",
  "last_user_message_at": "string",
  "last_system_message_at": "string",
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
    // 1. Extract necessary data
    const { company_data, recipient_data, project_data, request_data } = messageBody;
    
    // 2. Get company configuration
    const companyConfig = await getCompanyConfig(company_data.company_id, company_data.project_id);
    
    // 3. Get API credentials
    const credentials = await getCredentials(companyConfig);
    
    // 4. Initialize OpenAI and Twilio clients
    const openai = initializeOpenAI(credentials.openaiApiKey);
    const twilioClient = initializeTwilio(credentials.twilioAccountSid, credentials.twilioAuthToken);
    
    // 5. Manage conversation
    const conversation = await manageConversation(recipient_data, company_data, project_data, request_data);
    
    // 6. Process with OpenAI
    const aiResponse = await processWithOpenAI(openai, conversation, project_data);
    
    // 7. Send via Twilio
    const deliveryResult = await sendViaTwilio(twilioClient, recipient_data, aiResponse, companyConfig);
    
    // 8. Update conversation with results
    await updateConversation(conversation, aiResponse, deliveryResult);
    
    // 9. Clean up and delete message
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

async function getCompanyConfig(companyId, projectId) {
  // Query DynamoDB for company configuration
}

async function getCredentials(companyConfig) {
  // Get API keys from Secrets Manager
}

async function manageConversation(recipientData, companyData, projectData, requestData) {
  // Create or update conversation in DynamoDB
}

async function processWithOpenAI(openai, conversation, projectData) {
  // Process message with OpenAI
}

async function sendViaTwilio(twilioClient, recipientData, aiResponse, companyConfig) {
  // Send message via Twilio
}

async function updateConversation(conversation, aiResponse, deliveryResult) {
  // Update conversation in DynamoDB
}

async function deleteMessage(receiptHandle) {
  // Delete message from SQS queue
}
```

### 4.2 OpenAI Integration

```javascript
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
```

### 4.3 Twilio Integration

```javascript
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
```

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
   - Company configuration retrieved
   - Conversation created/updated
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