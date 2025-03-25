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

## 3. Template Registry in DynamoDB

Templates are stored in DynamoDB for tracking and management:

### 3.1 Template Table Structure

The `wa_templates` DynamoDB table tracks templates with the following structure:

```javascript
/**
 * Structure of a template record in DynamoDB
 */
const templateRecord = {
  // Primary Key (company_id)
  company_id: "company123",
  
  // Sort Key (template_name#language)
  template_key: "welcome_message#en_US",
  
  // Template details
  template_name: "welcome_message",
  language: "en_US",
  category: "UTILITY",
  components: [
    {
      type: "HEADER",
      format: "TEXT",
      text: "Welcome to {{1}}"
    },
    {
      type: "BODY", 
      text: "Hello {{1}}! Thank you for reaching out to us. How can we assist you today?"
    },
    {
      type: "FOOTER",
      text: "Reply to this message to start a conversation."
    }
  ],
  
  // Twilio/WhatsApp identifiers
  twilio_content_sid: "HXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  whatsapp_template_id: "123456789012345",
  
  // Status and timestamps
  status: "APPROVED", // PENDING, APPROVED, REJECTED
  created_at: "2023-05-15T12:34:56Z",
  updated_at: "2023-05-15T14:22:33Z",
  
  // Additional attributes
  rejection_reason: null,
  created_by: "user@example.com"
};
```

### 3.2 Template Management Operations

The system provides several operations for template management:

#### 3.2.1 Create Template

```javascript
/**
 * Creates a new template and submits to Twilio for WhatsApp approval
 * @param {object} template - Template object with components
 * @param {string} companyId - Company ID
 * @returns {Promise<object>} - Created template record
 */
async function createTemplate(template, companyId) {
  try {
    // Validate template structure
    validateTemplateStructure(template);
    
    // Get Twilio credentials
    const credentials = await getCredentials(
      'whatsapp/twilio',
      companyId,
      'default'
    );
    
    // Initialize Twilio client
    const twilioClient = twilio(
      credentials.twilio_account_sid,
      credentials.twilio_auth_token
    );
    
    // Prepare template for Twilio submission
    const twilioTemplate = buildTwilioTemplate(template);
    
    // Submit template to Twilio
    const content = await twilioClient.messaging.contentAndTemplates.templates.create(twilioTemplate);
    
    // Create DynamoDB record
    const templateRecord = {
      company_id: companyId,
      template_key: `${template.name}#${template.language}`,
      template_name: template.name,
      language: template.language,
      category: template.category,
      components: template.components,
      twilio_content_sid: content.sid,
      whatsapp_template_id: null,  // Will be populated by Twilio webhook later
      status: "PENDING",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      rejection_reason: null,
      created_by: template.created_by || "system"
    };
    
    // Save to DynamoDB
    await documentClient.put({
      TableName: 'wa_templates',
      Item: templateRecord
    }).promise();
    
    return templateRecord;
  } catch (error) {
    console.error('Error creating template:', error);
    throw error;
  }
}
```

#### 3.2.2 Get Template

```javascript
/**
 * Retrieves a template by name and language
 * @param {string} companyId - Company ID
 * @param {string} templateName - Template name
 * @param {string} language - Template language code
 * @returns {Promise<object>} - Template record
 */
async function getTemplate(companyId, templateName, language) {
  try {
    const templateKey = `${templateName}#${language}`;
    
    const result = await documentClient.get({
      TableName: 'wa_templates',
      Key: {
        company_id: companyId,
        template_key: templateKey
      }
    }).promise();
    
    if (!result.Item) {
      throw new Error(`Template not found: ${templateName} (${language})`);
    }
    
    return result.Item;
  } catch (error) {
    console.error('Error getting template:', error);
    throw error;
  }
}
```

#### 3.2.3 List Templates

```javascript
/**
 * Lists templates for a company
 * @param {string} companyId - Company ID
 * @param {object} filters - Optional filters (status, category)
 * @returns {Promise<Array>} - Array of template records
 */
async function listTemplates(companyId, filters = {}) {
  try {
    let params = {
      TableName: 'wa_templates',
      KeyConditionExpression: 'company_id = :companyId',
      ExpressionAttributeValues: {
        ':companyId': companyId
      }
    };
    
    // Apply additional filters if provided
    if (filters.status || filters.category) {
      let filterExpression = [];
      let expressionAttributeValues = { ...params.ExpressionAttributeValues };
      
      if (filters.status) {
        filterExpression.push('status = :status');
        expressionAttributeValues[':status'] = filters.status;
      }
      
      if (filters.category) {
        filterExpression.push('category = :category');
        expressionAttributeValues[':category'] = filters.category;
      }
      
      params.FilterExpression = filterExpression.join(' AND ');
      params.ExpressionAttributeValues = expressionAttributeValues;
    }
    
    const result = await documentClient.query(params).promise();
    
    return result.Items;
  } catch (error) {
    console.error('Error listing templates:', error);
    throw error;
  }
}
```

#### 3.2.4 Update Template Status

```javascript
/**
 * Updates a template status based on Twilio webhook
 * @param {string} companySid - Twilio account SID (mapped to company)
 * @param {string} contentSid - Twilio content SID
 * @param {string} status - New status
 * @param {string} whatsappTemplateId - WhatsApp template ID (for approved templates)
 * @param {string} rejectionReason - Reason for rejection (if rejected)
 * @returns {Promise<object>} - Updated template record
 */
async function updateTemplateStatus(companySid, contentSid, status, whatsappTemplateId, rejectionReason) {
  try {
    // Look up company ID by Twilio SID
    const companyId = await getCompanyIdByTwilioSid(companySid);
    
    // Find template by content SID
    const templates = await documentClient.scan({
      TableName: 'wa_templates',
      FilterExpression: 'company_id = :companyId AND twilio_content_sid = :contentSid',
      ExpressionAttributeValues: {
        ':companyId': companyId,
        ':contentSid': contentSid
      }
    }).promise();
    
    if (!templates.Items || templates.Items.length === 0) {
      throw new Error(`Template not found for content SID: ${contentSid}`);
    }
    
    const template = templates.Items[0];
    
    // Map Twilio status to internal status
    const mappedStatus = mapTwilioStatus(status);
    
    // Update template
    const updateParams = {
      TableName: 'wa_templates',
      Key: {
        company_id: template.company_id,
        template_key: template.template_key
      },
      UpdateExpression: 'SET #status = :status, updated_at = :updatedAt',
      ExpressionAttributeNames: {
        '#status': 'status'
      },
      ExpressionAttributeValues: {
        ':status': mappedStatus,
        ':updatedAt': new Date().toISOString()
      },
      ReturnValues: 'ALL_NEW'
    };
    
    if (whatsappTemplateId) {
      updateParams.UpdateExpression += ', whatsapp_template_id = :whatsappTemplateId';
      updateParams.ExpressionAttributeValues[':whatsappTemplateId'] = whatsappTemplateId;
    }
    
    if (rejectionReason) {
      updateParams.UpdateExpression += ', rejection_reason = :rejectionReason';
      updateParams.ExpressionAttributeValues[':rejectionReason'] = rejectionReason;
    }
    
    const result = await documentClient.update(updateParams).promise();
    
    return result.Attributes;
  } catch (error) {
    console.error('Error updating template status:', error);
    throw error;
  }
}
```

## 4. Sending WhatsApp Template Messages

### 4.1 Sending a Template Message with Variables

The key function for sending WhatsApp template messages integrates with Twilio and uses the variables provided by the OpenAI processing:

```javascript
/**
 * Sends a WhatsApp template message using Twilio API
 * @param {object} contextObject - Context object with conversation data and content variables
 * @returns {Promise<object>} - Result of sending message
 */
async function sendWhatsAppTemplateMessage(contextObject) {
  try {
    console.log('Sending WhatsApp template message', {
      conversation_id: contextObject.conversation_data?.conversation_id,
      recipient_tel: contextObject.frontend_payload.recipient_data.recipient_tel
    });
    
    // Get WhatsApp credentials from Secrets Manager
    const whatsappCredentialsId = contextObject.channel_config.whatsapp.whatsapp_credentials_id;
    const twilioCredentials = await getSecretValue(whatsappCredentialsId);
    
    // Get the content/template SID from Twilio credentials in Secrets Manager
    const contentSid = twilioCredentials.twilio_template_sid;
    
    if (!contentSid) {
      throw new Error('Template SID not found in credentials. Please ensure twilio_template_sid is set in the WhatsApp credentials in Secrets Manager.');
    }
    
    // Initialize Twilio client
    const twilioClient = twilio(
      twilioCredentials.twilio_account_sid,
      twilioCredentials.twilio_auth_token
    );
    
    // Get content variables from the context object
    const contentVariables = contextObject.content_variables;
    
    // Validate content variables
    if (!contentVariables || typeof contentVariables !== 'object') {
      throw new Error('Invalid content variables in context object');
    }
    
    // Prepare message options
    const messageOptions = {
      from: `whatsapp:${contextObject.channel_config.whatsapp.company_whatsapp_number}`,
      to: `whatsapp:${contextObject.frontend_payload.recipient_data.recipient_tel}`,
      contentSid: contentSid,
      contentVariables: JSON.stringify(contentVariables)
    };
    
    // Send the message
    const message = await twilioClient.messages.create(messageOptions);
    
    console.log('WhatsApp template message sent', {
      message_sid: message.sid, 
      status: message.status,
      conversation_id: contextObject.conversation_data?.conversation_id
    });
    
    // Add message to conversation history
    await addMessageToConversation(
      contextObject.conversation_data,
      'assistant',
      'Template message sent',
      message.sid
    );
    
    // Update conversation status
    await updateConversationStatus(
      contextObject.conversation_data,
      'initial_message_sent'
    );
    
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
```

### 4.2 Error Handling

Template sending has specific error handling logic:

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

### 4.3 Integration with OpenAI Processing

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
    
    // Create conversation record
    await createConversationRecord(contextObject);
    
    // Setup OpenAI client with API key from Secrets Manager
    const openai = await setupOpenAIClient(contextObject.ai_config.ai_api_key_reference);
    
    // Process message with OpenAI and get content variables
    const openAIResult = await processWithOpenAI(openai, contextObject);
    
    // The contextObject now has content_variables from OpenAI processing
    
    // Send template message using the updated context object
    const messageResult = await sendWhatsAppTemplateMessage(contextObject);
    
    return {
      success: true,
      message_result: messageResult,
      openai_result: openAIResult
    };
  } catch (error) {
    console.error('Error processing WhatsApp message:', error);
    
    // Handle template sending errors if possible
    if (error.code && error.message && error.message.includes('Twilio')) {
      await handleTemplateSendingError(error, contextObject);
    }
    
    throw error;
  }
}
```

## 5. Message Sending

### 5.1 Sending Template Messages

```javascript
/**
 * Sends a WhatsApp message using a template
 * @param {string} companyId - Company ID
 * @param {string} to - Recipient phone number
 * @param {string} templateName - Template name
 * @param {string} language - Template language
 * @param {object} variables - Template variables
 * @returns {Promise<object>} - Message sending result
 */
async function sendTemplateMessage(companyId, to, templateName, language, variables = {}) {
  try {
    // Get credentials
    const credentials = await getCredentials(
      'whatsapp/twilio',
      companyId,
      'default'
    );
    
    // Get company WhatsApp number
    const companyDetails = await getCompanyDetails(companyId);
    const fromNumber = companyDetails.whatsapp_number;
    
    // Get template
    const template = await getTemplate(companyId, templateName, language);
    
    if (template.status !== 'APPROVED') {
      throw new Error(`Template ${templateName} is not approved for use (status: ${template.status})`);
    }
    
    // Initialize Twilio client
    const twilioClient = twilio(
      credentials.twilio_account_sid,
      credentials.twilio_auth_token
    );
    
    // Prepare message options
    const messageOptions = {
      from: `whatsapp:${fromNumber}`,
      to: `whatsapp:${to}`,
      contentSid: template.twilio_content_sid
    };
    
    // Add variables if present
    if (Object.keys(variables).length > 0) {
      messageOptions.contentVariables = JSON.stringify(variables);
    }
    
    // Send message
    const message = await twilioClient.messages.create(messageOptions);
    
    return {
      template_name: templateName,
      language,
      message_sid: message.sid,
      status: message.status,
      to: to,
      from: fromNumber
    };
  } catch (error) {
    console.error('Error sending template message:', error);
    throw error;
  }
}
```

### 5.2 Sending Free-Form Messages

```javascript
/**
 * Sends a free-form WhatsApp message (only allowed in response to user message)
 * @param {string} companyId - Company ID
 * @param {string} to - Recipient phone number
 * @param {string} text - Message text
 * @param {object} mediaUrl - Optional media URL
 * @returns {Promise<object>} - Message sending result
 */
async function sendFreeFormMessage(companyId, to, text, mediaUrl = null) {
  try {
    // Get credentials
    const credentials = await getCredentials(
      'whatsapp/twilio',
      companyId,
      'default'
    );
    
    // Get company WhatsApp number
    const companyDetails = await getCompanyDetails(companyId);
    const fromNumber = companyDetails.whatsapp_number;
    
    // Initialize Twilio client
    const twilioClient = twilio(
      credentials.twilio_account_sid,
      credentials.twilio_auth_token
    );
    
    // Prepare message options
    const messageOptions = {
      from: `whatsapp:${fromNumber}`,
      to: `whatsapp:${to}`,
      body: text
    };
    
    // Add media URL if present
    if (mediaUrl) {
      messageOptions.mediaUrl = mediaUrl;
    }
    
    // Send message
    const message = await twilioClient.messages.create(messageOptions);
    
    return {
      message_sid: message.sid,
      status: message.status,
      to: to,
      from: fromNumber,
      has_media: !!mediaUrl
    };
  } catch (error) {
    console.error('Error sending free-form message:', error);
    throw error;
  }
}
```

## 6. Message Status Handling

### 6.1 Twilio Webhook for Status Updates

The system receives status updates via Twilio webhooks:

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

### 6.2 Tracking Message Status in Conversation

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

## 7. Template Localization

The system supports template localization in multiple languages:

```javascript
/**
 * Creates a localized version of an existing template
 * @param {string} companyId - Company ID
 * @param {string} templateName - Template name
 * @param {string} sourceLanguage - Source language
 * @param {string} targetLanguage - Target language
 * @param {object} translatedComponents - Translated components
 * @returns {Promise<object>} - Created localized template
 */
async function createLocalizedTemplate(
  companyId, 
  templateName, 
  sourceLanguage, 
  targetLanguage, 
  translatedComponents
) {
  try {
    // Get source template
    const sourceTemplate = await getTemplate(companyId, templateName, sourceLanguage);
    
    // Create new template object
    const localizedTemplate = {
      name: sourceTemplate.template_name,
      language: targetLanguage,
      category: sourceTemplate.category,
      components: []
    };
    
    // Process components
    for (const component of sourceTemplate.components) {
      const translatedComponent = translatedComponents[component.type] || {};
      
      // Create new component with translations
      const localizedComponent = {
        type: component.type,
        format: component.format
      };
      
      if (component.text) {
        localizedComponent.text = translatedComponent.text || component.text;
      }
      
      if (component.buttons) {
        localizedComponent.buttons = component.buttons.map((button, index) => {
          const translatedButton = (translatedComponent.buttons || [])[index] || {};
          
          return {
            type: button.type,
            text: translatedButton.text || button.text,
            url: button.url // URL doesn't need translation
          };
        });
      }
      
      localizedTemplate.components.push(localizedComponent);
    }
    
    // Create the localized template
    return await createTemplate(localizedTemplate, companyId);
  } catch (error) {
    console.error('Error creating localized template:', error);
    throw error;
  }
}
```

## 8. Media Messages

The system supports sending media in messages:

```javascript
/**
 * Uploads media to Twilio for WhatsApp sending
 * @param {string} companyId - Company ID
 * @param {Buffer} mediaBuffer - Media file buffer
 * @param {string} mimeType - Media MIME type
 * @returns {Promise<string>} - Twilio media URL
 */
async function uploadMediaToTwilio(companyId, mediaBuffer, mimeType) {
  try {
    // Get credentials
    const credentials = await getCredentials(
      'whatsapp/twilio',
      companyId,
      'default'
    );
    
    // Initialize Twilio client
    const twilioClient = twilio(
      credentials.twilio_account_sid,
      credentials.twilio_auth_token
    );
    
    // Upload media
    const media = await twilioClient.messages.media.create({
      contentType: mimeType,
      data: mediaBuffer.toString('base64')
    });
    
    return media.uri;
  } catch (error) {
    console.error('Error uploading media to Twilio:', error);
    throw error;
  }
}
```

## 9. Integration with Function Execution

The template and message sending functionality is integrated with the Function Execution system, allowing the OpenAI Assistant to use these functions:

```javascript
// Excerpt from function implementations
async function generateWhatsAppTemplate(args) {
  // ... (validation code) ...
  
  // Create template object
  const template = {
    name: args.templateName,
    category: args.category,
    language: args.language,
    components: args.components
  };
  
  // Generate template without saving to Twilio
  return {
    template,
    message: 'Template generated successfully. Ready to be submitted to WhatsApp.'
  };
}

async function sendWhatsAppMessage(args) {
  // ... (validation code) ...
  
  if (args.useTemplate) {
    return await sendTemplateMessage(
      contextObject.company_id,
      contextObject.recipient_tel,
      args.templateName,
      args.templateLanguage,
      args.templateVariables
    );
  } else {
    return await sendFreeFormMessage(
      contextObject.company_id,
      contextObject.recipient_tel,
      args.messageText,
      args.mediaUrl
    );
  }
}
```

## 10. Related Documentation

- [Overview and Architecture](./01-overview-architecture.md)
- [OpenAI Integration](./05-openai-integration.md)
- [Error Handling Strategy](./07-error-handling-strategy.md)
- [Monitoring and Observability](./08-monitoring-observability.md)

## 11. Best Practices for Template Management

1. **Template Identifiers**: Store template SIDs in AWS Secrets Manager alongside Twilio credentials for secure access

2. **Error Handling**: Implement specific error handling for template-related issues

3. **Monitoring**: Track template usage and error metrics in CloudWatch

4. **Content Variables**: Ensure the OpenAI assistant is configured to return structured content variables

5. **Fallback Mechanisms**: Implement fallback templates for critical communications 