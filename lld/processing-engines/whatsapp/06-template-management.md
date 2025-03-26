# WhatsApp Processing Engine - Template Management and Message Sending

> **Part 6 of 9 in the WhatsApp Processing Engine documentation series**

## 1. Introduction

This document details how the WhatsApp Processing Engine manages message templates and handles message sending through the Twilio API. WhatsApp requires business accounts to use pre-approved templates for initial outbound messages, and this system manages these templates while providing a streamlined interface for sending messages.

## 2. WhatsApp Template Structure

WhatsApp templates follow a structured format with specific components:

### 2.1 Template Components

1. **Header** (Optional): Can contain text, image, document, or video
2. **Body** (Required): Text content with optional variables (`{{1}}`, `{{2}}`, etc.)
3. **Footer** (Optional): Additional text content
4. **Buttons** (Optional): Up to 3 buttons (Quick Reply or URL)

Each template requires approval from WhatsApp before it can be used.

### 2.2 Template Categories

Templates are categorized into three types:

| Category | Description | Approval Likelihood | Example Use Case |
|----------|-------------|---------------------|------------------|
| UTILITY | Provides essential information or service updates | High | Appointment reminders, order confirmations |
| MARKETING | Promotional content | Medium | New product announcements, special offers |
| AUTHENTICATION | Verification codes and account authentication | High | Login codes, account verification |

## 3. Template Management Approach

Unlike traditional systems that maintain a separate database for templates, our approach simplifies template management by storing the necessary template information directly in AWS Secrets Manager alongside the Twilio credentials. This approach offers several advantages:

1. **Reduced Complexity**: No need for a separate template database
2. **Secure Storage**: Template IDs are stored alongside credentials in a secure manner
3. **Simplified Setup**: New businesses can be onboarded quickly without complex template migration
4. **Direct Integration**: Template SIDs can be retrieved directly during message sending

### 3.1 Template Setup Process

The template setup process for a new business client involves:

1. **Business Onboarding**: Adaptix Innovation works with the business to understand their use case
2. **Twilio Account Setup**: Creating or configuring the business's Twilio account
3. **WhatsApp Business Profile**: Setting up the WhatsApp Business Profile in Meta
4. **Template Creation**: Designing and submitting templates for WhatsApp approval
5. **Credentials Storage**: Once approved, storing the template SID along with Twilio credentials in AWS Secrets Manager
6. **AI Assistant Configuration**: Configuring an OpenAI Assistant with instructions specific to the template structure

### 3.2 Credentials and Template Storage

The credentials for each business are stored in AWS Secrets Manager with the following structure:

```javascript
/**
 * WhatsApp credentials structure in AWS Secrets Manager
 */
{
  "twilio_account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "twilio_auth_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "twilio_template_sid": "HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  // Template SID for the specific use case
}
```

This structure enables the system to retrieve both the authentication credentials and the template SID in a single operation, reducing API calls and simplifying the code.

## 4. Company Configuration in DynamoDB

While templates themselves are not stored in DynamoDB, essential configuration information for each company is maintained in the `wa_company_data` table:

```javascript
/**
 * Relevant fields in wa_company_data for template handling
 */
{
  "company_id": "adaptix-innovation",
  "project_id": "recruitment-assistant",
  "channel_config": {
    "whatsapp": {
      "company_whatsapp_number": "+447700900000",
      "whatsapp_credentials_id": "whatsapp/adaptix/recruitment-assistant" // Reference to Secrets Manager entry
    }
  },
  "ai_config": {
    "assistant_id_template_sender": "asst_123456789",
    "ai_api_key_reference": "openai/adaptix" // Reference to OpenAI API key in Secrets Manager
  }
}
```

This configuration provides all the necessary references to access both the template SID via the `whatsapp_credentials_id` and the appropriate AI assistant through `assistant_id_template_sender`.

## 5. Message Sending Process

The WhatsApp Processing Engine follows a streamlined process for sending template messages:

### 5.1 Process Overview

1. **Frontend Request**: A custom frontend sends a request with recipient data and business-specific information
2. **Context Object Creation**: The Channel Router creates a context object with company details from DynamoDB
3. **AI Processing**: The OpenAI assistant processes the context and generates appropriate template variables
4. **Template Sending**: The system sends the template message using Twilio API with the generated variables
5. **Conversation Tracking**: All interactions are recorded in the conversations DynamoDB table

### 5.2 Sending a Template Message with Variables

The key function for sending WhatsApp template messages integrates with Twilio and uses the variables provided by the OpenAI processing:

```javascript
/**
 * Sends a WhatsApp template message using Twilio API
 * @param {object} contextObject - Context object with conversation data
 * @param {object} variables - Template variables from OpenAI processing
 * @returns {Promise<object>} - Result of sending message
 */
async function sendWhatsAppTemplateMessage(contextObject, variables) {
  try {
    console.log('Sending WhatsApp template message', {
      conversation_id: contextObject.conversation_data?.conversation_id,
      recipient_tel: contextObject.frontend_payload.recipient_data.recipient_tel
    });
    
    // Get WhatsApp credentials from Secrets Manager
    const whatsappCredentialsId = contextObject.channel_config.whatsapp.whatsapp_credentials_id;
    const twilioCredentials = await getSecretValue(whatsappCredentialsId);
    
    // Get the template SID directly from Twilio credentials in Secrets Manager
    const contentSid = twilioCredentials.twilio_template_sid;
    
    if (!contentSid) {
      throw new Error('Template SID not found in credentials. Please ensure twilio_template_sid is set in the WhatsApp credentials in Secrets Manager.');
    }
    
    // Initialize Twilio client
    const twilioClient = twilio(
      twilioCredentials.twilio_account_sid,
      twilioCredentials.twilio_auth_token
    );
    
    // Validate content variables
    if (!variables || typeof variables !== 'object') {
      throw new Error('Invalid content variables generated by AI');
    }
    
    // Prepare message options
    const messageOptions = {
      from: `whatsapp:${contextObject.channel_config.whatsapp.company_whatsapp_number}`,
      to: `whatsapp:${contextObject.frontend_payload.recipient_data.recipient_tel}`,
      contentSid: contentSid,
      contentVariables: JSON.stringify(variables)
    };
    
    // Send the message
    const message = await twilioClient.messages.create(messageOptions);
    
    console.log('WhatsApp template message sent', {
      message_sid: message.sid, 
      status: message.status,
      conversation_id: contextObject.conversation_data?.conversation_id
    });
    
    // Complete the message object with timestamp, role, and content
    contextObject.conversation_data.message.message_timestamp = new Date().toISOString();
    contextObject.conversation_data.message.role = "assistant";
    contextObject.conversation_data.message.content = `Template message sent with SID: ${message.sid}`;
    
    // First retrieve the conversation record from DynamoDB
    const conversation = await getConversationRecord(
      contextObject.frontend_payload.recipient_data.recipient_tel,
      contextObject.conversation_data.conversation_id
    );
    
    // Prepare the final conversation update data
    const finalUpdateData = {
      conversation_status: 'initial_message_sent',
      thread_id: contextObject.conversation_data.thread_id,
      messages: [contextObject.conversation_data.message]  // Message object contains all metrics
    };
    
    // Update conversation record with final status and metrics
    await updateConversationRecord(conversation, finalUpdateData);
    
    return {
      success: true,
      message_sid: message.sid,
      status: message.status,
      sent_at: new Date().toISOString()
    };
  } catch (error) {
    console.error('Error sending WhatsApp template message:', error);
    throw error;
  }
}

### 5.2.1 Final DynamoDB Update Mapping

When updating the conversation record after successful message sending, the following mapping is used:

```javascript
// Final DynamoDB Update Mapping
{
  // Status update
  conversation_status: "initial_message_sent",  // Static value
  
  // Thread reference
  thread_id: contextObject.conversation_data.thread_id,
  
  // Complete message added to messages array
  messages: [{                                                    // First message in conversation
    entry_id: contextObject.conversation_data.message.entry_id,   // Generated UUID
    message_timestamp: contextObject.conversation_data.message.message_timestamp,  // When Twilio confirmed sending
    role: "assistant",                                           // Static for template message
    content: contextObject.conversation_data.message.content,     // Template message with Twilio SID
    ai_prompt_tokens: contextObject.conversation_data.message.ai_prompt_tokens,      // From OpenAI
    ai_completion_tokens: contextObject.conversation_data.message.ai_completion_tokens,  // From OpenAI
    ai_total_tokens: contextObject.conversation_data.message.ai_total_tokens,          // From OpenAI
    processing_time_ms: contextObject.conversation_data.message.processing_time_ms      // Total processing time
  }]
}
```

This update:
1. Sets the conversation status to indicate successful template sending
2. Stores the OpenAI thread ID for future reference
3. Adds the complete message to the messages array with all metrics contained within the message object

### 5.3 Integration with OpenAI Processing

The template sending function is integrated with the OpenAI processing flow:

```javascript
/**
 * Main handler for processing WhatsApp messages
 * @param {object} event - SQS event trigger
 * @returns {Promise<object>} - Processing result
 */
async function processWhatsAppMessage(event) {
  try {
    // Parse context object from SQS message
    const contextObject = JSON.parse(event.Records[0].body);
    
    // Setup OpenAI client with API key from Secrets Manager
    const openai = await setupOpenAIClient(contextObject.ai_config.ai_api_key_reference);
    
    // Process message with OpenAI and get content variables
    // This will:
    // 1. Create an OpenAI thread and store the thread_id in contextObject
    // 2. Run the OpenAI assistant to generate content variables
    // 3. Store the content_variables in contextObject.conversation_data
    // 4. Create a pending_assistant_message with metrics in contextObject.conversation_data
    const openAIResult = await processWithOpenAI(openai, contextObject);
    
    // Send WhatsApp template message with content variables
    // This will:
    // 1. Send the template message using Twilio API
    // 2. Retrieve the conversation record from DynamoDB
    // 3. Complete the pending_assistant_message by adding the content
    // 4. Add the completed message to the conversation's messages array
    // 5. Update the conversation with final status and metrics
    const messageResult = await sendWhatsAppTemplateMessage(
      contextObject, 
      contextObject.conversation_data.content_variables
    );
    
    // Return success result with key metrics
    return {
      success: true,
      thread_id: contextObject.thread_id,
      sent_at: messageResult.sent_at,
      processing_time_ms: contextObject.conversation_data.message.processing_time_ms,
      ai_total_tokens: contextObject.conversation_data.message.ai_total_tokens
    };
  } catch (error) {
    console.error('Error processing WhatsApp message:', error);
    
    // Handle template sending errors if appropriate
    if (error.code && error.message && error.message.includes('Twilio')) {
      await handleTemplateSendingError(error, contextObject);
    }
    
    throw error;
  }
}
```

## 6. Error Handling for Template Sending

Template sending has specific error handling logic to provide clear information about failures:

```javascript
/**
 * Error handling for template sending
 * @param {Error} error - Error from Twilio API
 * @param {object} contextObject - Context object
 * @returns {Promise<void>} - Resolves when error is handled
 */
async function handleTemplateSendingError(error, contextObject) {
  // Categorize the error
  let errorCategory = 'unknown';
  let shouldRetry = false;
  
  if (error.code === 20429 || error.status === 429) {
    errorCategory = 'rate_limit';
    shouldRetry = true;
  } else if (error.code === 20003) {
    errorCategory = 'authentication';
    shouldRetry = false;
  } else if (error.code === 21211) {
    errorCategory = 'invalid_number';
    shouldRetry = false;
  } else if (error.code === 21606) {
    errorCategory = 'template_not_found';
    shouldRetry = false;
  } else if (error.code === 21609) {
    errorCategory = 'template_not_approved';
    shouldRetry = false;
  } else if (error.code === 21610) {
    errorCategory = 'template_parameter_mismatch';
    shouldRetry = false;
  } else if (error.status >= 500 && error.status < 600) {
    errorCategory = 'server_error';
    shouldRetry = true;
  }
  
  // Log the error with detailed information
  console.error('Template sending error:', {
    error_category: errorCategory,
    error_code: error.code,
    error_message: error.message,
    should_retry: shouldRetry,
    conversation_id: contextObject.conversation_data?.conversation_id,
    recipient_tel: contextObject.frontend_payload.recipient_data.recipient_tel
  });
  
  // Update conversation record with error information
  await updateConversationError(
    contextObject.conversation_data,
    {
      error_type: 'template_sending',
      error_category: errorCategory,
      error_message: error.message,
      error_timestamp: new Date().toISOString()
    }
  );
  
  // Emit CloudWatch metric
  await emitTemplateErrorMetric(errorCategory, {
    company_id: contextObject.company_data.company_id,
    project_id: contextObject.company_data.project_id
  });
  
  // If the error is not retryable, update conversation status to failed
  if (!shouldRetry) {
    await updateConversationStatus(
      contextObject.conversation_data,
      'failed'
    );
  }
  
  // Rethrow the error for the Lambda handler to handle
  throw error;
}
```

## 7. Message Status Tracking

Once messages are sent, their status is tracked in the conversations DynamoDB table:

### 7.1 Status Webhook Integration

The system includes an API endpoint to receive status updates via Twilio webhooks:

```javascript
/**
 * Handles Twilio webhook for message status updates
 * @param {object} event - API Gateway event
 * @returns {Promise<object>} - API Gateway response
 */
exports.handleStatusWebhook = async (event) => {
  try {
    // Parse webhook payload
    const payload = querystring.parse(event.body);
    
    console.log('Received status webhook', {
      message_sid: payload.MessageSid,
      message_status: payload.MessageStatus,
      error_code: payload.ErrorCode
    });
    
    // Get conversation by message SID
    const conversation = await findConversationByMessageSid(payload.MessageSid);
    
    if (!conversation) {
      console.warn('No conversation found for message SID', {
        message_sid: payload.MessageSid
      });
      return {
        statusCode: 200,
        body: JSON.stringify({ received: true, status: 'untracked_message' })
      };
    }
    
    // Update message status in conversation
    await updateMessageStatus(
      conversation,
      payload.MessageSid,
      payload.MessageStatus,
      payload.ErrorCode
    );
    
    return {
      statusCode: 200,
      body: JSON.stringify({ received: true, status: 'processed' })
    };
  } catch (error) {
    console.error('Error processing status webhook:', error);
    
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Error processing webhook' })
    };
  }
};
```

### 7.2 Status Update in Conversation Record

```javascript
/**
 * Updates message status in the conversation record
 * @param {object} conversation - Conversation record
 * @param {string} messageSid - Message SID
 * @param {string} status - New status
 * @param {string} errorCode - Error code (if failed)
 * @returns {Promise<object>} - Updated conversation
 */
async function updateMessageStatus(conversation, messageSid, status, errorCode = null) {
  // Find message in conversation history
  const messageIndex = conversation.messages.findIndex(m => 
    m.message_sid === messageSid
  );
  
  if (messageIndex === -1) {
    console.warn('Message not found in conversation history', {
      conversation_id: conversation.conversation_id,
      message_sid: messageSid
    });
    return conversation;
  }
  
  // Update expression
  let updateExpression = 'SET messages[' + messageIndex + '].status = :status, ' +
                          'messages[' + messageIndex + '].status_updated_at = :timestamp';
  
  let expressionAttributeValues = {
    ':status': status,
    ':timestamp': new Date().toISOString()
  };
  
  // Add error code if present
  if (errorCode) {
    updateExpression += ', messages[' + messageIndex + '].error_code = :errorCode';
    expressionAttributeValues[':errorCode'] = errorCode;
  }
  
  // Update conversation
  const result = await documentClient.update({
    TableName: 'conversations',
    Key: {
      recipient_tel: conversation.recipient_tel,
      conversation_id: conversation.conversation_id
    },
    UpdateExpression: updateExpression,
    ExpressionAttributeValues: expressionAttributeValues,
    ReturnValues: 'ALL_NEW'
  }).promise();
  
  // If message failed, update conversation status
  if (status === 'failed' || status === 'undelivered') {
    await updateConversationStatus(
      result.Attributes,
      'failed',
      `Message ${status}: ${errorCode || 'unknown error'}`
    );
  }
  
  return result.Attributes;
}
```

## 8. AI-Driven Template Variable Generation

A key innovation in our approach is using OpenAI to generate template variables based on the context data, rather than hardcoding variable mapping for each use case:

### 8.1 OpenAI Assistant Configuration

Each business use case has a dedicated OpenAI Assistant configured with:

1. **System Instructions**: Detailed instructions on how to extract data from the context object
2. **Template Structure**: Information about the template format and variable positions
3. **Output Format Requirements**: Explicit instructions to return content variables in a specific JSON format
4. **Constraints**: Rules for handling missing or ambiguous data

### 8.2 Processing Flow for Variable Generation

```javascript
/**
 * Main function to process a message with OpenAI
 * @param {object} openai - Initialized OpenAI client
 * @param {object} contextObject - Full context object
 * @returns {Promise<object>} - Result with content variables
 */
async function processWithOpenAI(openai, contextObject) {
  try {
    console.log('Starting OpenAI processing');
    const startTime = Date.now();
    
    // Create OpenAI thread with the context object as input
    const thread = await openai.beta.threads.create({
      messages: [
        {
          role: "user",
          content: JSON.stringify(contextObject)
        }
      ]
    });
    
    // Update context object with thread_id
    contextObject.thread_id = thread.id;
    
    // Get assistant ID from context - using the template sender assistant
    const assistantId = contextObject.ai_config.assistant_id_template_sender;
    
    // Start the run
    const run = await openai.beta.threads.runs.create(
      thread.id,
      { assistant_id: assistantId }
    );
    
    // Poll run status until completion
    const finalRun = await pollRunStatus(openai, thread.id, run.id);
    
    if (finalRun.status === 'completed') {
      // Extract content variables from assistant response
      const contentVariables = await getAssistantResponse(openai, thread.id, contextObject);
      
      // Store metrics and content variables
      const processingTimeMs = Date.now() - startTime;
      
      // Store content_variables in the conversation_data object
      contextObject.conversation_data.content_variables = contentVariables;
      
      // Create a pending assistant message with all metrics
      const assistantMessage = {
        entry_id: uuidv4(),
        message_timestamp: new Date().toISOString(),
        role: 'assistant',
        ai_prompt_tokens: finalRun.usage?.prompt_tokens || 0,
        ai_completion_tokens: finalRun.usage?.completion_tokens || 0,
        ai_total_tokens: finalRun.usage?.total_tokens || 0,
        processing_time_ms: processingTimeMs
      };
      
      // Store pending message for later completion
      contextObject.conversation_data.message = assistantMessage;
      
      return {
        thread_id: thread.id,
        run_id: run.id,
        status: 'completed',
        content_variables: contentVariables,
        processing_time_ms: processingTimeMs
      };
    } else {
      throw new Error(`Run ended with status: ${finalRun.status}`);
    }
  } catch (error) {
    console.error('Error in OpenAI processing:', error);
    throw error;
  }
}
```

## 9. Setup Process for New Business Integration

Setting up a new business to use the WhatsApp Processing Engine involves these steps:

1. **Business Requirements Analysis**: 
   - Understand the use case and communication needs
   - Identify recipient data structure and content requirements

2. **Twilio & WhatsApp Setup**:
   - Set up a Twilio account for the business (or use their existing account)
   - Create a WhatsApp Sender profile in Meta Business Manager
   - Design and submit templates for approval according to use case

3. **System Configuration**:
   - Create an entry in the `wa_company_data` table with company_id and project_id
   - Configure channel_config with WhatsApp number and credentials reference
   - Configure ai_config with assistant_id and API key reference

4. **Secrets Manager Setup**:
   - Store Twilio credentials (account SID, auth token)
   - Store the approved template SID alongside credentials
   - Generate and store secure reference keys

5. **OpenAI Assistant Configuration**:
   - Create a custom assistant for the business use case
   - Configure system instructions specific to the template structure
   - Test assistant with sample context objects

6. **Frontend Development**:
   - Create a custom frontend (embedded or standalone) for the business use case
   - Configure API endpoints and authentication
   - Implement client-specific data capture

7. **Testing and Deployment**:
   - Validate end-to-end message flow
   - Monitor initial message delivery rates
   - Adjust AI configuration if necessary

## 10. Related Documentation

- [Overview and Architecture](./01-overview-architecture.md)
- [OpenAI Integration](./05-openai-integration.md)
- [Error Handling Strategy](./07-error-handling-strategy.md)
- [Monitoring and Observability](./08-monitoring-observability.md)
- [Operations Playbook](./09-operations-playbook.md)

## 11. Best Practices for Template Management

1. **Template Identifiers**: Store template SIDs in AWS Secrets Manager alongside Twilio credentials for secure access

2. **AI Configuration**: Ensure the OpenAI assistant is properly configured to understand the template structure and output compatible content variables

3. **Error Monitoring**: Implement specific monitoring for template-related errors, particularly parameter mismatch issues

4. **Testing**: Before deploying a new template, test thoroughly with varied context data

5. **Template Approval**: Plan for WhatsApp approval time (typically 1-3 business days) when onboarding new businesses

6. **Documentation**: Maintain clear documentation of each business's template structure and variable mappings for troubleshooting

7. **Credentials Rotation**: Implement a secure process for rotating Twilio credentials without disrupting template access 