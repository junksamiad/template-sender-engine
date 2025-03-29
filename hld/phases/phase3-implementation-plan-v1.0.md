# Phase 3: WhatsApp Processing Engine

This document outlines the detailed implementation steps for Phase 3 of the AI Multi-Communications Engine project. Phase 3 focuses on implementing the WhatsApp Processing Engine for handling WhatsApp messages.

## Objectives

- Implement WhatsApp Lambda for processing messages from SQS
- Develop OpenAI integration for message processing
- Implement Twilio integration for message delivery
- Create robust error handling strategies
- Implement monitoring and observability

## Key Documentation References

### High-Level Design
- [AI Multi-Communications Engine HLD](../multi-comms-engine-hld-v1.0.md) - The complete system architecture and overview

### Low-Level Design
- [Overview and Architecture](../../lld/processing-engines/whatsapp/01-overview-architecture.md) - WhatsApp engine design
- [SQS Integration](../../lld/processing-engines/whatsapp/02-sqs-integration.md) - Queue processing patterns
- [Conversation Management](../../lld/processing-engines/whatsapp/03-conversation-management.md) - Conversation data handling
- [Credential Management](../../lld/processing-engines/whatsapp/04-credential-management.md) - Secure credential access
- [OpenAI Integration](../../lld/processing-engines/whatsapp/05-openai-integration.md) - AI model integration
- [Twilio Processing and Final DB Update](../../lld/processing-engines/whatsapp/06-twilio-processing-and-final-db-update.md) - Message delivery
- [Error Handling Strategy](../../lld/processing-engines/whatsapp/07-error-handling-strategy.md) - Error management
- [Monitoring and Observability](../../lld/processing-engines/whatsapp/08-monitoring-observability.md) - Metrics and logging
- [Business Onboarding](../../lld/processing-engines/whatsapp/09-business-onboarding.md) - Client setup process

## Implementation Steps

### 1. WhatsApp Lambda Implementation

#### 1.1 Set Up Lambda Function ⬜
**Relevant Documentation:**
- [Overview and Architecture](../../lld/processing-engines/whatsapp/01-overview-architecture.md) - Lambda configuration
- [AI Multi-Communications Engine HLD](../multi-comms-engine-hld-v1.0.md) - Section 4.3.1 WhatsApp Processing Engine

- [ ] Create WhatsApp Lambda resource in CDK
- [ ] Configure Lambda environment variables
- [ ] Set up Lambda execution role with necessary permissions
- [ ] Configure Lambda memory and timeout settings
- [ ] Set up Lambda logging

#### 1.2 Implement SQS Message Consumption ⬜
**Relevant Documentation:**
- [SQS Integration](../../lld/processing-engines/whatsapp/02-sqs-integration.md) - Queue consumption patterns
- [AI Multi-Communications Engine HLD](../multi-comms-engine-hld-v1.0.md) - Section 4.2 Message Queues

- [ ] Create SQS event source mapping
- [ ] Implement message parsing and validation
- [ ] Configure batch processing settings
- [ ] Implement visibility timeout management
- [ ] Create message processing queue

#### 1.3 Extract and Validate Context Object ⬜
**Relevant Documentation:**
- [SQS Integration](../../lld/processing-engines/whatsapp/02-sqs-integration.md) - Context extraction
- [Context Object](../../lld/context-object/context-object-v1.0.md) - Context object structure
- [Context Object Implementation](../../lld/context-object/context-object-implementation-v1.0.md) - Context object deserialization and validation

- [ ] Extract context object from SQS message
- [ ] Validate context object structure
- [ ] Handle missing or invalid context data
- [ ] Enrich context with additional metadata
- [ ] Log context object for debugging

#### 1.4 Create Conversation Records ⬜
**Relevant Documentation:**
- [Conversation Management](../../lld/processing-engines/whatsapp/03-conversation-management.md) - DynamoDB operations
- [Conversations DB Schema](../../lld/db/conversations-db-schema-v1.0.md) - Database schema

- [ ] Create new DynamoDB record for new conversations
- [ ] Update existing records for ongoing conversations
- [ ] Implement conversation expiration logic
- [ ] Create conversation metadata
- [ ] Optimize DynamoDB operations

#### 1.5 Test Lambda Functionality ⬜
**Relevant Documentation:**
- [Overview and Architecture](../../lld/processing-engines/whatsapp/01-overview-architecture.md) - Testing approach
- [SQS Integration](../../lld/processing-engines/whatsapp/02-sqs-integration.md) - Queue testing

- [ ] Create unit tests for Lambda handler
- [ ] Test SQS integration with mock events
- [ ] Verify DynamoDB operations
- [ ] Validate error handling
- [ ] Test performance under load

### 2. OpenAI Integration

#### 2.1 Implement OpenAI Client ⬜
**Relevant Documentation:**
- [OpenAI Integration](../../lld/processing-engines/whatsapp/05-openai-integration.md) - Client implementation
- [Credential Management](../../lld/processing-engines/whatsapp/04-credential-management.md) - API key access

- [ ] Create OpenAI API client wrapper
- [ ] Configure API key retrieval from Secrets Manager
- [ ] Implement request/response handling
- [ ] Create retry mechanism for API calls
- [ ] Implement error handling

#### 2.2 Develop Thread Management ⬜
**Relevant Documentation:**
- [OpenAI Integration](../../lld/processing-engines/whatsapp/05-openai-integration.md) - Thread management
- [Conversation Management](../../lld/processing-engines/whatsapp/03-conversation-management.md) - Thread storage

- [ ] Implement thread creation for new conversations
- [ ] Develop thread retrieval for existing conversations
- [ ] Create thread storage mechanism in DynamoDB
- [ ] Implement thread cleanup for expired conversations
- [ ] Create thread validation utilities

#### 2.3 Implement Message Processing ⬜
**Relevant Documentation:**
- [OpenAI Integration](../../lld/processing-engines/whatsapp/05-openai-integration.md) - Message formatting
- [AI Multi-Communications Engine HLD](../multi-comms-engine-hld-v1.0.md) - Section 8.2 OpenAI Integration

- [ ] Format incoming messages for OpenAI
- [ ] Create message assembly with context
- [ ] Implement token counting and management
- [ ] Configure model parameters
- [ ] Create message history management

#### 2.4 Create Response Handling ⬜
**Relevant Documentation:**
- [OpenAI Integration](../../lld/processing-engines/whatsapp/05-openai-integration.md) - Response parsing
- [Twilio Processing and Final DB Update](../../lld/processing-engines/whatsapp/06-twilio-processing-and-final-db-update.md) - Message preparation

- [ ] Implement response parsing
- [ ] Extract message content from responses
- [ ] Create validation for response format
- [ ] Implement content filtering if needed
- [ ] Format response for Twilio delivery

#### 2.5 Test OpenAI Integration ⬜
**Relevant Documentation:**
- [OpenAI Integration](../../lld/processing-engines/whatsapp/05-openai-integration.md) - Testing considerations
- [Error Handling Strategy](../../lld/processing-engines/whatsapp/07-error-handling-strategy.md) - OpenAI error handling

- [ ] Create unit tests with mock responses
- [ ] Test thread management
- [ ] Verify token management
- [ ] Test error scenarios
- [ ] Measure and optimize performance

### 3. Twilio Integration

#### 3.1 Implement Twilio Client ⬜
**Relevant Documentation:**
- [Twilio Processing and Final DB Update](../../lld/processing-engines/whatsapp/06-twilio-processing-and-final-db-update.md) - Client implementation
- [Credential Management](../../lld/processing-engines/whatsapp/04-credential-management.md) - Twilio credentials

- [ ] Create Twilio API client wrapper
- [ ] Configure credentials retrieval from Secrets Manager
- [ ] Implement request/response handling
- [ ] Create retry mechanism for API calls
- [ ] Implement error handling

#### 3.2 Develop Template Message Construction ⬜
**Relevant Documentation:**
- [Twilio Processing and Final DB Update](../../lld/processing-engines/whatsapp/06-twilio-processing-and-final-db-update.md) - Template handling
- [Business Onboarding](../../lld/processing-engines/whatsapp/09-business-onboarding.md) - Template configuration

- [ ] Create message templates based on company configuration
- [ ] Implement dynamic content insertion
- [ ] Format message for WhatsApp requirements
- [ ] Implement template validation
- [ ] Create fallback mechanisms

#### 3.3 Implement Message Delivery ⬜
**Relevant Documentation:**
- [Twilio Processing and Final DB Update](../../lld/processing-engines/whatsapp/06-twilio-processing-and-final-db-update.md) - Message sending
- [AI Multi-Communications Engine HLD](../multi-comms-engine-hld-v1.0.md) - Section 8.3 Twilio Integration

- [ ] Create message sending logic
- [ ] Implement delivery receipts handling
- [ ] Create message ID tracking
- [ ] Implement rate limiting adherence
- [ ] Configure delivery timeouts

#### 3.4 Handle Delivery Confirmation ⬜
**Relevant Documentation:**
- [Twilio Processing and Final DB Update](../../lld/processing-engines/whatsapp/06-twilio-processing-and-final-db-update.md) - Delivery status updates
- [Conversation Management](../../lld/processing-engines/whatsapp/03-conversation-management.md) - Status tracking

- [ ] Create webhook handlers for delivery status
- [ ] Update conversation record with delivery status
- [ ] Implement notification for failed deliveries
- [ ] Create delivery analytics tracking
- [ ] Implement retry logic for failed deliveries

#### 3.5 Test Twilio Integration ⬜
**Relevant Documentation:**
- [Twilio Processing and Final DB Update](../../lld/processing-engines/whatsapp/06-twilio-processing-and-final-db-update.md) - Testing approach
- [Error Handling Strategy](../../lld/processing-engines/whatsapp/07-error-handling-strategy.md) - Twilio error handling

- [ ] Create unit tests with mock responses
- [ ] Test message template rendering
- [ ] Verify delivery tracking
- [ ] Test webhooks with simulated responses
- [ ] Validate error handling

### 4. Error Handling Strategies

#### 4.1 Implement Transient Error Handling ⬜
**Relevant Documentation:**
- [Error Handling Strategy](../../lld/processing-engines/whatsapp/07-error-handling-strategy.md) - Transient errors
- [AI Multi-Communications Engine HLD](../multi-comms-engine-hld-v1.0.md) - Section 5.3 Error Handling Strategy

- [ ] Create retry mechanism with backoff
- [ ] Implement circuit breaker for external services
- [ ] Configure timeout handling
- [ ] Create temporary storage for in-process messages
- [ ] Implement recovery procedures

#### 4.2 Handle Permanent Errors ⬜
**Relevant Documentation:**
- [Error Handling Strategy](../../lld/processing-engines/whatsapp/07-error-handling-strategy.md) - Permanent errors
- [AI Multi-Communications Engine HLD](../multi-comms-engine-hld-v1.0.md) - Section 5.3 Error Handling Strategy

- [ ] Identify and categorize permanent errors
- [ ] Implement dead letter queue routing
- [ ] Create detailed error reporting
- [ ] Implement administrator notifications
- [ ] Create error documentation for operations

#### 4.3 Implement Dead Letter Queue Integration ⬜
**Relevant Documentation:**
- [Error Handling Strategy](../../lld/processing-engines/whatsapp/07-error-handling-strategy.md) - DLQ integration
- [SQS Integration](../../lld/processing-engines/whatsapp/02-sqs-integration.md) - Queue error handling

- [ ] Configure DLQ message format
- [ ] Create error context enrichment
- [ ] Implement DLQ monitoring
- [ ] Create manual retry mechanisms
- [ ] Configure DLQ retention policy

#### 4.4 Test Error Handling ⬜
**Relevant Documentation:**
- [Error Handling Strategy](../../lld/processing-engines/whatsapp/07-error-handling-strategy.md) - Testing scenarios
- [Monitoring and Observability](../../lld/processing-engines/whatsapp/08-monitoring-observability.md) - Error tracking

- [ ] Create tests for transient error scenarios
- [ ] Test permanent error handling
- [ ] Verify DLQ functionality
- [ ] Test recovery procedures
- [ ] Validate error reporting

### 5. Heartbeat Pattern Implementation

#### 5.1 Design Heartbeat Mechanism ⬜
**Relevant Documentation:**
- [SQS Integration](../../lld/processing-engines/whatsapp/02-sqs-integration.md) - Heartbeat pattern
- [AI Multi-Communications Engine HLD](../multi-comms-engine-hld-v1.0.md) - Section 5.1 Message Processing Flow

- [ ] Create heartbeat timer implementation
- [ ] Configure visibility timeout extension
- [ ] Implement progress tracking
- [ ] Create heartbeat logging
- [ ] Design failure detection

#### 5.2 Implement SQS Visibility Extension ⬜
**Relevant Documentation:**
- [SQS Integration](../../lld/processing-engines/whatsapp/02-sqs-integration.md) - Visibility timeout management
- [AI Multi-Communications Engine HLD](../multi-comms-engine-hld-v1.0.md) - Section 4.2 Message Queues

- [ ] Create visibility timeout calculation
- [ ] Implement SQS API calls for extension
- [ ] Configure extension frequency
- [ ] Create maximum processing time limits
- [ ] Implement graceful shutdown

#### 5.3 Test Heartbeat Pattern ⬜
**Relevant Documentation:**
- [SQS Integration](../../lld/processing-engines/whatsapp/02-sqs-integration.md) - Testing approach
- [Error Handling Strategy](../../lld/processing-engines/whatsapp/07-error-handling-strategy.md) - Recovery testing

- [ ] Test with long-running operations
- [ ] Verify timeout extension
- [ ] Test failure scenarios
- [ ] Validate cleanup procedures
- [ ] Measure performance impact

### 6. Monitoring and Logging Configuration

#### 6.1 Configure Processing Metrics ⬜
**Relevant Documentation:**
- [Monitoring and Observability](../../lld/processing-engines/whatsapp/08-monitoring-observability.md) - Processing metrics
- [AI Multi-Communications Engine HLD](../multi-comms-engine-hld-v1.0.md) - Section 10.1 CloudWatch Dashboards

- [ ] Create metrics for message volume
- [ ] Implement processing time tracking
- [ ] Configure queue depth monitoring
- [ ] Create success/failure rate metrics
- [ ] Implement batch size tracking

#### 6.2 Implement Error Metrics ⬜
**Relevant Documentation:**
- [Monitoring and Observability](../../lld/processing-engines/whatsapp/08-monitoring-observability.md) - Error metrics
- [Error Handling Strategy](../../lld/processing-engines/whatsapp/07-error-handling-strategy.md) - Error categorization

- [ ] Create metrics for error categories
- [ ] Implement retry count monitoring
- [ ] Configure DLQ monitoring
- [ ] Create service failure metrics
- [ ] Implement error rate alerting

#### 6.3 Configure Token Usage Tracking ⬜
**Relevant Documentation:**
- [Monitoring and Observability](../../lld/processing-engines/whatsapp/08-monitoring-observability.md) - Token tracking
- [OpenAI Integration](../../lld/processing-engines/whatsapp/05-openai-integration.md) - Token management

- [ ] Implement OpenAI token counting
- [ ] Create cost monitoring metrics
- [ ] Configure token usage alerting
- [ ] Implement token optimization tracking
- [ ] Create token usage reporting

#### 6.4 Test Monitoring Configuration ⬜
**Relevant Documentation:**
- [Monitoring and Observability](../../lld/processing-engines/whatsapp/08-monitoring-observability.md) - Testing approach
- [CloudWatch Dashboard Setup](../../lld/cloudwatch-dashboard/cloudwatch-dashboard-setup-v1.0.md) - Dashboard testing

- [ ] Verify metric generation
- [ ] Test alerting thresholds
- [ ] Validate dashboard functionality
- [ ] Test log generation and filtering
- [ ] Verify tracing capabilities

## Testing Requirements

### Local Tests
- Unit tests for Lambda components
- Mock tests for OpenAI and Twilio interactions
- DynamoDB operation tests
- Error handling scenario tests
- Heartbeat pattern tests

### AWS Tests
- Integration tests with deployed Lambda
- End-to-end message processing tests
- SQS integration tests
- Performance tests under load
- Long-running operation tests with heartbeat pattern

## Documentation Deliverables

- WhatsApp Processing Engine architecture documentation
- OpenAI integration guide
- Twilio integration guide
- Error handling strategy documentation
- Heartbeat pattern documentation
- Monitoring and observability guide
- Operational procedures for common issues

## Dependencies

- Completion of Phase 2
- Access to SQS queues
- Access to DynamoDB tables
- Access to Secrets Manager
- Shared utilities from Phase 1

## Notes

- Record any challenges or issues encountered during this phase
- Document any deviations from the original plan
- Keep track of AWS resources created for cost monitoring
- Track OpenAI token usage for cost optimization
- Note any performance considerations or bottlenecks

## Phase Completion Criteria

Phase 3 is considered complete when:
- All implementation steps are marked with a green tick (✅)
- All local and AWS tests pass successfully
- All documentation deliverables are completed
- The WhatsApp Processing Engine is fully operational
- Error handling is robust and well-tested
- Monitoring and logging provide adequate visibility 