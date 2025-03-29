# WhatsApp Processing Engine - Conversation Management

> **Part 3 of 10 in the WhatsApp Processing Engine documentation series**

## 1. Introduction

This document outlines how the WhatsApp Processing Engine creates, updates, and manages conversation records in DynamoDB. The conversation database serves as the persistent store for message history, processing state, and all relevant metadata for the communication.

## 2. Conversation Record Schema

Conversation records in the `conversations` table follow a specific schema optimized for WhatsApp channel operations. The key structure is designed to support efficient lookups and effective reply matching.

### 2.1 Key Structure

For WhatsApp conversations:

- **Partition Key**: `recipient_tel` - The recipient's phone number
- **Sort Key**: `conversation_id` - A composite identifier in the format: `{company_id}#{project_id}#{request_id}#{company_whatsapp_number}`

This structure enables:
- Quick lookups for specific conversations
- Efficient queries for all conversations with a given recipient
- Clear organization by company, project, and request
- Effective WhatsApp reply matching

### 2.2 Key Attributes

The primary attributes stored in each WhatsApp conversation record include:

| Attribute | Type | Description | Source |
|-----------|------|-------------|--------|
| `recipient_tel` | String | Primary key - Recipient's phone number | `frontend_payload.recipient_data.recipient_tel` |
| `conversation_id` | String | Sort key - Composite conversation identifier | Generated (see format above) |
| `company_id` | String | Company identifier | `frontend_payload.company_data.company_id` |
| `project_id` | String | Project identifier | `frontend_payload.company_data.project_id` |
| `channel_method` | String | Communication channel (always "whatsapp") | `frontend_payload.request_data.channel_method` |
| `company_whatsapp_number` | String | Company's WhatsApp number | `channel_config.whatsapp.company_whatsapp_number` |
| `conversation_status` | String | Status of the conversation | Initially "processing" |
| `thread_id` | String | OpenAI thread ID | Generated during OpenAI processing |
| `messages` | List | Array of message objects | Built during conversation |
| `task_complete` | Boolean | Whether processing is complete | Initially false |
| `created_at` | String | ISO 8601 timestamp of creation | Generated timestamp |
| `updated_at` | String | ISO 8601 timestamp of last update | Generated timestamp |

For a complete listing of all attributes, refer to the [Conversations DB Schema](../../db/conversations-db-schema-v1.0.md) document.

## 3. Conversation Creation Process

### 3.1 Generating the Conversation ID

The WhatsApp Processing Engine forms a unique conversation ID by combining several key identifiers:

```javascript
function generateConversationId(companyId, projectId, requestId, companyWhatsAppNumber) {
  // Sanitize phone number by removing any non-alphanumeric characters
  const sanitizedCompanyNumber = companyWhatsAppNumber.replace(/\D/g, '');
  
  // Combine into a single string with a delimiter
  return `${companyId}#${projectId}#${requestId}#${sanitizedCompanyNumber}`;
}
```

### 3.2 Creating the Company Representative Structure

The company representative information is structured from the `wa_company_data_payload` in the context object:

```javascript
// Map company representatives from wa_company_data_payload
const companyRep = contextObject.wa_company_data_payload.company_rep || {
  company_rep_1: null,
  company_rep_2: null,
  company_rep_3: null,
  company_rep_4: null,
  company_rep_5: null
};
```

### 3.3 Building and Storing the Conversation Record

```javascript
async function createConversationRecord(contextObject) {
  const { frontend_payload, channel_config, ai_config } = contextObject;
  const { company_data, recipient_data, project_data, request_data } = frontend_payload;
  
  // Generate conversation ID
  const conversationId = generateConversationId(
    company_data.company_id,
    company_data.project_id,
    request_data.request_id,
    channel_config.whatsapp.company_whatsapp_number
  );
  
  // Map company representatives from wa_company_data_payload, not frontend payload
  const companyRep = contextObject.wa_company_data_payload.company_rep || {
    company_rep_1: null,
    company_rep_2: null,
    company_rep_3: null,
    company_rep_4: null,
    company_rep_5: null
  };
  
  // Create timestamp
  const now = new Date().toISOString();
  
  // Create conversation record
  const conversation = {
    recipient_tel: recipient_data.recipient_tel,  // Partition key
    conversation_id: conversationId,              // Sort key
    company_id: company_data.company_id,
    project_id: company_data.project_id,
    company_name: contextObject.wa_company_data_payload.company_name,
    project_name: contextObject.wa_company_data_payload.project_name,
    company_rep: companyRep,
    channel_method: 'whatsapp',
    company_whatsapp_number: channel_config.whatsapp.company_whatsapp_number,
    request_id: request_data.request_id,
    router_version: contextObject.metadata.router_version,
    whatsapp_credentials_reference: channel_config.whatsapp.whatsapp_credentials_id,
    sms_credentials_reference: channel_config.sms?.sms_credentials_id,
    email_credentials_reference: channel_config.email?.email_credentials_id,
    recipient_first_name: recipient_data.recipient_first_name,
    recipient_last_name: recipient_data.recipient_last_name,
    conversation_status: 'processing',
    thread_id: null,  // Will be populated after OpenAI processing
    processing_time_ms: null,  // Will be populated after full processing
    task_complete: false,
    comms_consent: recipient_data.comms_consent || false,
    project_data: frontend_payload.project_data,
    ai_config: {
      assistant_id_template_sender: ai_config.assistant_id_template_sender,
      assistant_id_replies: ai_config.assistant_id_replies,
      assistant_id_3: ai_config.assistant_id_3 || null,
      assistant_id_4: ai_config.assistant_id_4 || null,
      assistant_id_5: ai_config.assistant_id_5 || null,
      ai_api_key_reference: ai_config.ai_api_key_reference
    },
    messages: [],
    created_at: now,
    updated_at: now
  };
  
  // Save to DynamoDB
  await dynamoDB.put({
    TableName: process.env.CONVERSATION_TABLE_NAME,
    Item: conversation
  }).promise();
  
  console.log('Conversation record created', { 
    conversation_id: conversation.conversation_id,
    status: 'processing',
    request_id: request_data.request_id
  });
  
  // Update context object with conversation ID for downstream processing
  contextObject.conversation_data = {
    conversation_id: conversationId
  };
  
  return conversation;
}
```

## 4. Status Lifecycle Management

The `conversation_status` field tracks the conversation's progression through the system. We use a streamlined approach with three essential states:

| Status | Description | When Set |
|--------|-------------|----------|
| `processing` | Initial state when processing begins | During conversation record creation |
| `initial_message_sent` | Message successfully delivered | After Twilio confirms message delivery |
| `failed` | Processing failed after retries | When message lands in DLQ after retries |

### 4.1 Status Update Implementation

```javascript
async function updateConversationStatus(conversation, status) {
  const now = new Date().toISOString();
  
  // Update in DynamoDB
  await dynamoDB.update({
    TableName: process.env.CONVERSATION_TABLE_NAME,
    Key: {
      recipient_tel: conversation.recipient_tel,
      conversation_id: conversation.conversation_id
    },
    UpdateExpression: 'SET conversation_status = :status, updated_at = :updated',
    ExpressionAttributeValues: {
      ':status': status,
      ':updated': now
    }
  }).promise();
  
  console.log(`Conversation status updated to ${status}`, {
    conversation_id: conversation.conversation_id,
    status,
    timestamp: now
  });
  
  return conversation;
}
```

## 5. Message History Management

The `messages` array in the conversation record maintains the complete history of the conversation. Each message entry includes:

### 5.1 Message Entry Structure

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `entry_id` | String (UUID) | Unique identifier for the message | "550e8400-e29b-41d4-a716-446655440001" |
| `message_timestamp` | String (ISO) | When the message was sent/received | "2023-05-01T12:35:26Z" |
| `role` | String | "user" or "assistant" | "assistant" |
| `content` | String | The message content | "Hello! I'd be happy to help..." |
| `ai_prompt_tokens` | Number | OpenAI token usage | 24 |
| `ai_completion_tokens` | Number | OpenAI token usage | 72 |
| `ai_total_tokens` | Number | OpenAI token usage | 96 |

### 5.2 Adding Messages to the Conversation

```javascript
async function addMessageToConversation(conversation, messageData) {
  const now = new Date().toISOString();
  
  // Create the message entry
  const messageEntry = {
    entry_id: uuidv4(),
    message_timestamp: now,
    role: messageData.role,
    content: messageData.content,
    ai_prompt_tokens: messageData.usage?.prompt_tokens || null,
    ai_completion_tokens: messageData.usage?.completion_tokens || null,
    ai_total_tokens: messageData.usage?.total_tokens || null
  };
  
  // Update the conversation record
  await dynamoDB.update({
    TableName: process.env.CONVERSATION_TABLE_NAME,
    Key: {
      recipient_tel: conversation.recipient_tel,
      conversation_id: conversation.conversation_id
    },
    UpdateExpression: 'SET messages = list_append(if_not_exists(messages, :empty_list), :new_message), updated_at = :updated',
    ExpressionAttributeValues: {
      ':new_message': [messageEntry],
      ':empty_list': [],
      ':updated': now
    }
  }).promise();
  
  console.log('Added message to conversation', {
    conversation_id: conversation.conversation_id,
    message_role: messageData.role,
    message_id: messageEntry.entry_id
  });
  
  return messageEntry;
}
```

## 6. Updating the OpenAI Thread ID

After creating an OpenAI thread, the ID is stored in the conversation record:

```javascript
async function updateThreadId(conversation, threadId) {
  const now = new Date().toISOString();
  
  await dynamoDB.update({
    TableName: process.env.CONVERSATION_TABLE_NAME,
    Key: {
      recipient_tel: conversation.recipient_tel,
      conversation_id: conversation.conversation_id
    },
    UpdateExpression: 'SET thread_id = :thread_id, updated_at = :updated',
    ExpressionAttributeValues: {
      ':thread_id': threadId,
      ':updated': now
    }
  }).promise();
  
  console.log('Updated conversation with thread ID', {
    conversation_id: conversation.conversation_id,
    thread_id: threadId
  });
  
  return conversation;
}
```

## 7. Final Conversation Update

Upon successful completion of all processing steps, a final update is performed:

```javascript
async function finalizeConversation(conversation, aiResponse, deliveryResult) {
  const now = new Date().toISOString();
  
  // Calculate processing time
  const processingStartTime = new Date(conversation.created_at).getTime();
  const processingEndTime = new Date().getTime();
  const processingTimeMs = processingEndTime - processingStartTime;
  
  // Update the conversation record
  await dynamoDB.update({
    TableName: process.env.CONVERSATION_TABLE_NAME,
    Key: {
      recipient_tel: conversation.recipient_tel,
      conversation_id: conversation.conversation_id
    },
    UpdateExpression: `
      SET thread_id = :thread_id,
          processing_time_ms = :processing_time,
          conversation_status = :status,
          task_complete = :task_complete,
          updated_at = :updated_at
    `,
    ExpressionAttributeValues: {
      ':thread_id': aiResponse.thread_id,
      ':processing_time': processingTimeMs,
      ':status': 'initial_message_sent',
      ':task_complete': true,
      ':updated_at': now
    }
  }).promise();
  
  console.log('Conversation finalized', {
    conversation_id: conversation.conversation_id,
    thread_id: aiResponse.thread_id,
    status: 'initial_message_sent',
    processing_time_ms: processingTimeMs
  });
  
  return conversation;
}
```

## 8. DLQ Processing for Failed Conversations

When a message lands in the Dead Letter Queue after exhausting retries, a DLQ processor Lambda updates the conversation status to "failed":

```javascript
// In DLQ Processor Lambda
async function handleFailedConversation(dlqMessage) {
  try {
    // Parse original message from DLQ
    const originalMessage = JSON.parse(dlqMessage.body);
    const contextObject = JSON.parse(originalMessage.body);
    
    // Extract key information
    const { frontend_payload, channel_config } = contextObject;
    const { company_data, recipient_data, request_data } = frontend_payload;
    
    // Generate the same conversation ID
    const conversationId = generateConversationId(
      company_data.company_id,
      company_data.project_id,
      request_data.request_id,
      channel_config.whatsapp.company_whatsapp_number
    );
    
    // Look up the conversation in DynamoDB
    const conversation = await getConversationRecord(
      recipient_data.recipient_tel,
      conversationId
    );
    
    // Update status to failed
    if (conversation) {
      await updateConversationStatus(conversation, 'failed');
      
      console.log('Updated conversation status to failed', {
        conversation_id: conversationId,
        request_id: request_data.request_id
      });
    }
  } catch (error) {
    console.error('Error handling failed conversation', error);
  }
}
```

## 9. Reply Matching Strategy

> **Important Note**: The reply matching functionality described in this section is not implemented within the current WhatsApp Processing Engine build. This strategy will be implemented in a separate external service application that specifically handles incoming user replies. This section serves as a reference for how reply matching should be implemented in that service.

For WhatsApp, reply matching uses the composite key structure:

1. **Primary Lookup**: Using recipient's phone number (partition key) to identify all their conversations
2. **Company Filtering**: Filtering conversations by the company WhatsApp number
3. **Status Filtering**: Optionally filtering by conversation status

```javascript
// Example of retrieving a conversation for reply handling
// Note: This is a reference implementation for the external reply handling service
async function findExistingConversation(recipientTel, companyWhatsAppNumber) {
  // Query conversations by recipient phone number
  const result = await dynamoDB.query({
    TableName: process.env.CONVERSATION_TABLE_NAME,
    KeyConditionExpression: 'recipient_tel = :tel',
    FilterExpression: 'company_whatsapp_number = :company_number',
    ExpressionAttributeValues: {
      ':tel': recipientTel,
      ':company_number': companyWhatsAppNumber
    }
  }).promise();
  
  // Return the most recent conversation if found
  if (result.Items && result.Items.length > 0) {
    // Sort by creation time (newest first)
    result.Items.sort((a, b) => 
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
    
    return result.Items[0];
  }
  
  return null;
}
```

## 10. Accessing the Conversation Schema

For full schema details, global secondary indexes, and access patterns, refer to the comprehensive [Conversations DB Schema](../../db/conversations-db-schema-v1.0.md) document.

## 11. Error Handling

All DynamoDB operations include robust error handling to ensure data integrity:

```javascript
try {
  await dynamoDB.put({
    TableName: process.env.CONVERSATION_TABLE_NAME,
    Item: conversation
  }).promise();
  
  // Success logging
} catch (error) {
  // Categorize error type
  if (error.code === 'ProvisionedThroughputExceededException') {
    console.error('DynamoDB throughput exceeded', { error_code: error.code });
  } else if (error.code === 'ResourceNotFoundException') {
    console.error('DynamoDB table not found', { error_code: error.code });
  } else {
    console.error('DynamoDB error', { error_code: error.code, message: error.message });
  }
  
  // Rethrow for Lambda retry
  throw error;
}
```

## 12. Related Documentation

- [Overview and Architecture](./01-overview-architecture.md)
- [Conversations DB Schema](../../db/conversations-db-schema-v1.0.md)
- [Context Object Structure](../../context-object/context-object-v1.0.md) 