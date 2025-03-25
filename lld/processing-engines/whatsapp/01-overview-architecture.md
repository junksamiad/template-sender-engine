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

## 5. Processing Flow Overview

1. **SQS Message Consumption**:
   - Lambda triggered by WhatsApp SQS queue
   - Message becomes invisible for 600s (visibility timeout)
   - Heartbeat pattern extends visibility timeout during processing

2. **Context Object Parsing**:
   - Extract frontend payload, channel config, and AI config

3. **Conversation Record Creation**:
   - Create record in DynamoDB with status "processing"

4. **Credential Retrieval**:
   - Get OpenAI and Twilio credentials from AWS Secrets Manager

5. **OpenAI Processing**:
   - Create/retrieve thread ID
   - Process message with OpenAI Assistants API

6. **Twilio Delivery**:
   - Send processed message to recipient via Twilio

7. **Completion**:
   - Update conversation status to "initial_message_sent"
   - Delete message from SQS

## 6. Component Documentation Structure

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

## 7. Related Documentation

- [Context Object Structure](../../context-object/context-object-v1.0.md)
- [Conversations DB Schema](../../db/conversations-db-schema-v1.0.md)
- [AWS Reference Management](../../secrets-manager/aws-referencing-v1.0.md)
- [Error Tracking Strategies](../error-tracking-strategies-v1.0.md)
- [CloudWatch Dashboard Setup](../../cloudwatch-dashboard/cloudwatch-dashboard-setup-v1.0.md) 