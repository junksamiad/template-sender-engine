# WhatsApp Processing Engine - Overview and Architecture

> **Part 1 of 10 in the WhatsApp Processing Engine documentation series**

## 1. Introduction

The WhatsApp Processing Engine is a core component of our multi-channel communications system responsible for processing WhatsApp messages through the SQS queue, OpenAI, and Twilio. This document provides a high-level overview of the architecture and processing flow.

## 2. Component Purpose

The WhatsApp Processing Engine is responsible for:

- Consuming messages from the WhatsApp SQS queue
- Implementing the heartbeat pattern for long-running operations
- Creating and managing conversations in DynamoDB
- Retrieving credentials from AWS Secrets Manager using references provided in the context object
- Processing messages using the OpenAI Assistants API
- Delivering messages to end users via Twilio
- Handling failures and retries appropriately
- Providing detailed logging and monitoring

## 3. Position in System Architecture

The WhatsApp Processing Engine sits between:
- **Upstream**: Channel Router (via WhatsApp SQS queue)
- **Downstream**: OpenAI API and Twilio WhatsApp API
- **Persistence**: DynamoDB for conversation record management
- **Security**: AWS Secrets Manager for API credentials (accessed as needed)

```
                                   (1)                 (3)                  (5)
                                     ┌─► DynamoDB ◄────┐                    │
                                     │  (Conversations) │                    │
                                     │                  │                    ▼
Channel Router → WhatsApp SQS Queue → WhatsApp Processing Engine ────► OpenAI API ────► Twilio API → End User
                                     │          │        ▲                   ▲
                                     │          │        │                   │
                                     │          └───────(2)───────┐          │
                                     │                            ▼          │
                                     └─────────────────► AWS Secrets Manager(4)
```

Process flow:
1. Create conversation record in DynamoDB with status "received"
2. Update conversation status to "processing"
3. Update conversation with OpenAI processing results
4. Retrieve API credentials from Secrets Manager when needed:
   - For OpenAI API access before AI processing
   - For Twilio API access before message delivery
5. Update conversation with final status after delivery

## 4. Technical Implementation

The WhatsApp Processing Engine is implemented as:

- **Lambda Function**: Triggered by messages in the WhatsApp SQS queue
- **SQS Event Source**: Configured with batch size 1 for reliable processing
- **DynamoDB Access**: For conversation record creation and management
- **OpenAI Integration**: For AI-powered message processing
- **Twilio Integration**: For WhatsApp message delivery
- **Heartbeat Pattern**: For extending visibility timeout during long-running operations
- **CloudWatch**: For monitoring and logging operations
- **AWS Secrets Manager**: For securely accessing API keys

## 5. Processing Flow

The WhatsApp Processing Engine follows a linear, efficient processing flow:

1. **Message Receipt**: A message is received from the Channel Router's SQS queue containing a context object.

2. **Conversation Creation**: The engine creates a conversation record in DynamoDB with status "processing".

3. **OpenAI Processing**: 
   - The engine creates an OpenAI thread and adds the context as a message.
   - A run is created with the specified assistant.
   - The run is polled until completion.
   - The assistant responds with a structured JSON containing content variables.
   - The content variables are added to the context object.

4. **Template Message Sending**:
   - The updated context object with content variables is passed to the Twilio integration function.
   - The function retrieves the template SID from the Twilio credentials in AWS Secrets Manager.
   - The content variables are passed to the Twilio API along with the template SID.
   - The message is sent to the recipient's WhatsApp number.

5. **Conversation Finalization**:
   - The conversation record is updated with thread ID and delivery status.
   - Status is changed to "initial_message_sent".
   - The processing is complete.

## 6. Error Handling

The WhatsApp Processing Engine implements robust error handling through:

1. **Retry Logic**: Automatic retries with exponential backoff for transient failures.

2. **Dead Letter Queue**: Messages that fail after retries are sent to a DLQ for investigation.

3. **Error Categorization**: Errors are categorized by type (API errors, validation errors, etc.) for monitoring.

4. **Comprehensive Logging**: Detailed logging at each processing step for debugging.

5. **Structured Error Responses**: All errors include error codes, descriptive messages, and relevant metadata.

6. **JSON Validation**: Validation of the assistant's JSON response to ensure it contains the required variables.

## 7. Full Documentation

The WhatsApp Processing Engine is documented in detail across several files:

1. [SQS Integration](02-sqs-integration.md): Details on message queue integration, payload validation, and retry mechanisms.
2. [Conversation Management](03-conversation-management.md): Description of the DynamoDB conversation schema and operations.
3. [Credential Management](04-credential-management.md): Details on secure access to credentials for external APIs.
4. [OpenAI Integration](05-openai-integration.md): Comprehensive documentation on the OpenAI Assistants API integration.
5. [Template Management](07-template-management.md): Template creation, management, and message sending details.
6. [Error Handling Strategy](08-error-handling-strategy.md): Complete error handling approach and implementation.
7. [Monitoring & Observability](09-monitoring-observability.md): Monitoring, alerting, and observability details.
8. [Operations Playbook](10-operations-playbook.md): Operational procedures, troubleshooting, and maintenance tasks.

## 8. Component Documentation Structure

The WhatsApp Processing Engine documentation is organized into the following sections:

1. **Overview and Architecture** (this document)
2. **SQS Integration** - Queue consumption and the heartbeat pattern
3. **Conversation Management** - DynamoDB record creation and updates
4. **Credential Management** - AWS Secrets Manager integration
5. **OpenAI Integration** - Thread creation and management
6. **Function Execution** - Handling OpenAI function calls
7. **Twilio Integration** - Message delivery
8. **Error Handling Strategy** - Approach to failures and retries
9. **Monitoring and Observability** - CloudWatch integration
10. **CDK Implementation** - Infrastructure deployment

Each document focuses on a specific aspect of the processing engine, providing a modular approach to understanding the system.

## 9. Related Documentation

- [Context Object Structure](../../context-object/context-object-v1.0.md)
- [Conversations DB Schema](../../db/conversations-db-schema-v1.0.md)
- [AWS Reference Management](../../secrets-manager/aws-referencing-v1.0.md)
- [Error Tracking Strategies](../error-tracking-strategies-v1.0.md)
- [CloudWatch Dashboard Setup](../../cloudwatch-dashboard/cloudwatch-dashboard-setup-v1.0.md) 