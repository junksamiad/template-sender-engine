/**
 * WhatsApp Processing Engine - Lambda Handler
 * 
 * This Lambda function processes messages from the WhatsApp SQS queue,
 * interacts with OpenAI to generate template variables, and sends
 * messages via the Twilio API.
 */

const AWS = require('aws-sdk');
const { OpenAI } = require('openai');
const twilio = require('twilio');

// Initialize AWS services
const documentClient = new AWS.DynamoDB.DocumentClient();
const secretsManager = new AWS.SecretsManager();
const cloudwatch = new AWS.CloudWatch();

// Lambda handler for SQS events
exports.handler = async (event) => {
  try {
    console.log('Processing WhatsApp message event');
    
    // Extract context object from SQS event
    const sqsMessage = event.Records[0];
    const contextObject = JSON.parse(sqsMessage.body);
    
    // Create conversation record in DynamoDB
    const conversation = await createConversationRecord(contextObject);
    
    // Update contextObject with conversation data
    contextObject.conversation_data = {
      conversation_id: conversation.conversation_id,
      recipient_tel: conversation.recipient_tel
    };
    
    // Initialize OpenAI client with API key from Secrets Manager
    const openaiApiKey = await getSecretValue(contextObject.ai_config.ai_api_key_reference);
    const openaiClient = new OpenAI({ apiKey: openaiApiKey });
    
    // Process with OpenAI
    const openaiResult = await processWithOpenAI(openaiClient, contextObject);
    
    // Update conversation with threadId and completion status
    await finalizeConversation(conversation, openaiResult);
    
    console.log('WhatsApp processing completed successfully', {
      conversation_id: conversation.conversation_id,
      thread_id: openaiResult.thread_id,
      processing_time_ms: openaiResult.processing_time_ms
    });
    
    return {
      statusCode: 200,
      body: JSON.stringify({
        status: 'success',
        conversation_id: conversation.conversation_id
      })
    };
  } catch (error) {
    console.error('Error processing WhatsApp message:', error);
    
    // TODO: Add DLQ processing here
    
    return {
      statusCode: 500,
      body: JSON.stringify({
        status: 'error',
        message: error.message
      })
    };
  }
};

/**
 * Creates a conversation record in DynamoDB
 * @param {object} contextObject - The context object from SQS
 * @returns {Promise<object>} - Created conversation record
 */
async function createConversationRecord(contextObject) {
  const { frontend_payload, channel_config, ai_config, wa_company_data_payload } = contextObject;
  const { company_data, recipient_data, project_data, request_data } = frontend_payload;
  
  // Generate conversation ID
  const conversationId = generateConversationId(
    company_data.company_id,
    company_data.project_id,
    request_data.request_id,
    channel_config.whatsapp.company_whatsapp_number
  );
  
  // Create timestamp
  const now = new Date().toISOString();
  
  // Create conversation record
  const conversation = {
    recipient_tel: recipient_data.recipient_tel,  // Partition key
    conversation_id: conversationId,              // Sort key
    company_id: company_data.company_id,
    project_id: company_data.project_id,
    company_name: wa_company_data_payload.company_name,
    project_name: wa_company_data_payload.project_name,
    company_rep: wa_company_data_payload.company_rep || {},
    channel_method: 'whatsapp',
    company_whatsapp_number: channel_config.whatsapp.company_whatsapp_number,
    request_id: request_data.request_id,
    router_version: contextObject.metadata.router_version,
    whatsapp_credentials_reference: channel_config.whatsapp.whatsapp_credentials_id,
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
  await documentClient.put({
    TableName: process.env.CONVERSATION_TABLE_NAME,
    Item: conversation
  }).promise();
  
  console.log('Conversation record created', { 
    conversation_id: conversation.conversation_id,
    status: 'processing',
    request_id: request_data.request_id
  });
  
  return conversation;
}

/**
 * Generates a conversation ID from component parts
 * @param {string} companyId - Company ID
 * @param {string} projectId - Project ID
 * @param {string} requestId - Request ID
 * @param {string} companyWhatsAppNumber - Company's WhatsApp number
 * @returns {string} - Generated conversation ID
 */
function generateConversationId(companyId, projectId, requestId, companyWhatsAppNumber) {
  // Sanitize phone number by removing any non-alphanumeric characters
  const sanitizedCompanyNumber = companyWhatsAppNumber.replace(/\D/g, '');
  
  // Combine into a single string with a delimiter
  return `${companyId}#${projectId}#${requestId}#${sanitizedCompanyNumber}`;
}

/**
 * Main function to process a message with OpenAI
 * @param {object} openai - Initialized OpenAI client
 * @param {object} contextObject - Full context object
 * @returns {Promise<object>} - Result of the OpenAI processing
 */
async function processWithOpenAI(openai, contextObject) {
  try {
    console.log('Starting OpenAI processing');
    const startTime = Date.now();
    
    // Create OpenAI thread and add context as message
    const { thread_id } = await createOpenAIThread(openai, contextObject);
    
    // Update context object with thread_id
    contextObject.thread_id = thread_id;
    
    // Get assistant ID from context
    const assistantId = contextObject.ai_config.assistant_id_template_sender;
    
    // Create and start the run
    const run = await createAndStartRun(openai, thread_id, assistantId);
    
    // Poll run status until completion
    const finalRun = await pollRunStatus(openai, thread_id, run.id);
    
    // Process run results
    if (finalRun.status === 'completed') {
      // Get assistant messages
      const messages = await openai.beta.threads.messages.list(thread_id);
      
      // Find the most recent assistant message
      const assistantMessages = messages.data.filter(msg => msg.role === 'assistant');
      const latestMessage = assistantMessages[0];
      
      if (!latestMessage) {
        throw new Error('No assistant message found after completed run');
      }
      
      console.log('Run completed successfully', {
        thread_id,
        run_id: run.id,
        message_id: latestMessage.id,
        processing_time_ms: Date.now() - startTime
      });
      
      // Extract content from message
      const messageContent = latestMessage.content[0].text.value;
      
      // Parse JSON from the message content
      let variables;
      try {
        // Extract JSON content from message (handle potential text before/after JSON)
        const jsonMatch = messageContent.match(/```json\n([\s\S]*?)\n```/) || 
                         messageContent.match(/\{[\s\S]*\}/);
                         
        const jsonContent = jsonMatch ? jsonMatch[1] || jsonMatch[0] : messageContent;
        const parsedContent = JSON.parse(jsonContent);
        
        // Validate the parsed content has variables
        if (!parsedContent.variables) {
          throw new Error('Missing variables in assistant response');
        }
        
        variables = parsedContent.variables;
        console.log('Successfully parsed variables from assistant response', { 
          variable_count: Object.keys(variables).length 
        });
      } catch (parseError) {
        console.error('Failed to parse JSON from assistant response', {
          parse_error: parseError.message,
          message_content: messageContent
        });
        
        // Emit metric for monitoring
        await emitConfigurationIssueMetric('InvalidJSONResponse', {
          conversation_id: contextObject.conversation_data?.conversation_id,
          assistant_id: assistantId
        });
        
        throw new Error(`Failed to parse assistant response as JSON: ${parseError.message}`);
      }
      
      // Process the variables and send message with Twilio
      const messageResult = await sendWhatsAppTemplateMessage(
        contextObject,
        variables
      );
      
      return {
        thread_id,
        run_id: run.id,
        message_id: latestMessage.id,
        message_result: messageResult,
        status: 'completed',
        processing_time_ms: Date.now() - startTime
      };
    } else {
      // Handle failure cases
      console.error('Run ended with unexpected status', {
        thread_id,
        run_id: run.id,
        status: finalRun.status
      });
      
      throw new Error(`Run ended with status: ${finalRun.status}`);
    }
  } catch (error) {
    // Add metadata to the error for DLQ processing
    if (!error.metadata) {
      error.metadata = {
        thread_id: contextObject.thread_id,
        conversation_id: contextObject.conversation_data?.conversation_id
      };
    }
    
    console.error('Error in OpenAI processing:', error, {
      error_code: error.code,
      error_metadata: error.metadata
    });
    
    throw error;
  }
}

/**
 * Creates an OpenAI thread and adds context as a message
 * @param {object} openai - Initialized OpenAI client
 * @param {object} contextObject - Context object
 * @returns {Promise<object>} - Thread creation result
 */
async function createOpenAIThread(openai, contextObject) {
  try {
    // Create a new thread
    const thread = await openai.beta.threads.create();
    const threadId = thread.id;
    
    console.log('Created OpenAI thread', { thread_id: threadId });
    
    // Prepare context for message
    const messageContent = prepareContextMessage(contextObject);
    
    try {
      // Add message to thread
      await openai.beta.threads.messages.create(threadId, {
        role: 'user',
        content: messageContent
      });
      
      console.log('Added context message to thread', { 
        thread_id: threadId,
        conversation_id: contextObject.conversation_data.conversation_id,
        content_size: messageContent.length
      });
      
      return {
        thread_id: threadId
      };
    } catch (messageError) {
      // Handle message creation failure
      console.error('Failed to add message to thread', {
        thread_id: threadId,
        error: messageError.message
      });
      
      // Still return the thread_id even if message creation failed
      return {
        thread_id: threadId,
        message_creation_failed: true,
        error: messageError.message
      };
    }
  } catch (error) {
    console.error('Error creating OpenAI thread:', error);
    throw new Error(`Failed to create OpenAI thread: ${error.message}`);
  }
}

/**
 * Prepares a message from the context object for the OpenAI thread
 * @param {object} contextObject - Context object
 * @returns {string} - Formatted message for OpenAI
 */
function prepareContextMessage(contextObject) {
  const { frontend_payload, wa_company_data_payload } = contextObject;
  const { recipient_data, project_data } = frontend_payload;
  
  // Extract key variables
  const recipientName = `${recipient_data.recipient_first_name || ''} ${recipient_data.recipient_last_name || ''}`.trim();
  const companyName = wa_company_data_payload.company_name;
  const companyRep = wa_company_data_payload.company_rep?.company_rep_1 || 'Company Representative';
  
  // Create a formatted context message
  const contextMessage = JSON.stringify({
    recipient: {
      name: recipientName,
      phone: recipient_data.recipient_tel,
      email: recipient_data.recipient_email
    },
    company: {
      name: companyName,
      representative: companyRep
    },
    project: project_data
  }, null, 2);
  
  return contextMessage;
}

/**
 * Creates and runs the assistant on the thread
 * @param {object} openai - Initialized OpenAI client
 * @param {string} threadId - OpenAI thread ID
 * @param {string} assistantId - OpenAI assistant ID
 * @returns {Promise<object>} - Run object
 */
async function createAndStartRun(openai, threadId, assistantId) {
  try {
    console.log('Creating run with assistant', { 
      thread_id: threadId, 
      assistant_id: assistantId 
    });
    
    // Create a run with the specified assistant
    const run = await openai.beta.threads.runs.create(threadId, {
      assistant_id: assistantId
    });
    
    console.log('Run created successfully', { 
      run_id: run.id, 
      status: run.status 
    });
    
    return run;
  } catch (error) {
    console.error('Error creating OpenAI run:', error);
    throw new Error(`Failed to create OpenAI run: ${error.message}`);
  }
}

/**
 * Polls the run status until completion
 * @param {object} openai - Initialized OpenAI client
 * @param {string} threadId - OpenAI thread ID
 * @param {string} runId - OpenAI run ID
 * @returns {Promise<object>} - Final run status object
 */
async function pollRunStatus(openai, threadId, runId) {
  try {
    console.log('Starting run status polling', { thread_id: threadId, run_id: runId });
    
    // Define polling parameters
    const maxPollDuration = 600000; // 10 minutes in milliseconds
    const pollInterval = 1000; // 1 second initial poll interval
    const maxPollInterval = 5000; // Maximum 5 seconds between polls
    const startTime = Date.now();
    let currentPollInterval = pollInterval;
    
    // Get initial run status
    let run = await openai.beta.threads.runs.retrieve(threadId, runId);
    console.log('Initial run status:', { status: run.status });
    
    // Poll until terminal state or timeout
    while (['queued', 'in_progress', 'cancelling'].includes(run.status)) {
      // Check for timeout
      if (Date.now() - startTime > maxPollDuration) {
        throw new Error('Run polling timed out after 10 minutes');
      }
      
      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, currentPollInterval));
      
      // Gradually increase poll interval with a cap
      currentPollInterval = Math.min(currentPollInterval * 1.5, maxPollInterval);
      
      // Get updated run status
      run = await openai.beta.threads.runs.retrieve(threadId, runId);
      console.log('Updated run status:', { status: run.status });
      
      // Return immediately if in terminal state
      if (run.status === 'completed' || 
          run.status === 'failed' || 
          run.status === 'cancelled' || 
          run.status === 'expired') {
        break;
      }
    }
    
    console.log('Run polling completed', { 
      thread_id: threadId, 
      run_id: runId, 
      final_status: run.status,
      polling_duration_ms: Date.now() - startTime
    });
    
    return run;
  } catch (error) {
    console.error('Error polling run status:', error);
    throw new Error(`Failed to poll run status: ${error.message}`);
  }
}

/**
 * Sends a WhatsApp template message using Twilio API
 * @param {object} contextObject - Context object with conversation data
 * @param {object} variables - Template variables (numeric keys with string values)
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
    
    // Add message to conversation history
    await addMessageToConversation(
      contextObject.conversation_data,
      'assistant',
      `Template message sent`,
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

/**
 * Adds a message to the conversation history
 * @param {object} conversation - Conversation data
 * @param {string} role - Message role ('user' or 'assistant')
 * @param {string} content - Message content
 * @param {string} messageSid - Twilio message SID
 * @returns {Promise<object>} - Added message entry
 */
async function addMessageToConversation(conversation, role, content, messageSid = null) {
  const now = new Date().toISOString();
  
  // Create message entry
  const messageEntry = {
    entry_id: `msg_${Date.now()}${Math.floor(Math.random() * 1000)}`,
    role: role,
    content: content,
    message_timestamp: now,
    message_sid: messageSid,
    status: messageSid ? 'queued' : 'internal'
  };
  
  // Update conversation in DynamoDB
  await documentClient.update({
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
    message_role: role,
    message_id: messageEntry.entry_id
  });
  
  return messageEntry;
}

/**
 * Updates the conversation status
 * @param {object} conversation - Conversation data
 * @param {string} status - New status
 * @returns {Promise<object>} - Updated conversation
 */
async function updateConversationStatus(conversation, status) {
  const now = new Date().toISOString();
  
  // Update in DynamoDB
  await documentClient.update({
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

/**
 * Finalizes the conversation after processing
 * @param {object} conversation - Conversation record
 * @param {object} openaiResult - Result from OpenAI processing
 * @returns {Promise<object>} - Updated conversation
 */
async function finalizeConversation(conversation, openaiResult) {
  const now = new Date().toISOString();
  
  // Calculate processing time
  const processingStartTime = new Date(conversation.created_at).getTime();
  const processingEndTime = new Date().getTime();
  const processingTimeMs = processingEndTime - processingStartTime;
  
  // Update the conversation record
  await documentClient.update({
    TableName: process.env.CONVERSATION_TABLE_NAME,
    Key: {
      recipient_tel: conversation.recipient_tel,
      conversation_id: conversation.conversation_id
    },
    UpdateExpression: `
      SET thread_id = :thread_id,
          processing_time_ms = :processing_time,
          task_complete = :task_complete,
          updated_at = :updated_at
    `,
    ExpressionAttributeValues: {
      ':thread_id': openaiResult.thread_id,
      ':processing_time': processingTimeMs,
      ':task_complete': true,
      ':updated_at': now
    }
  }).promise();
  
  console.log('Conversation finalized', {
    conversation_id: conversation.conversation_id,
    thread_id: openaiResult.thread_id,
    processing_time_ms: processingTimeMs
  });
  
  return conversation;
}

/**
 * Gets a secret value from AWS Secrets Manager
 * @param {string} secretId - Secret ID
 * @returns {Promise<string>} - Secret value
 */
async function getSecretValue(secretId) {
  try {
    const data = await secretsManager.getSecretValue({ SecretId: secretId }).promise();
    
    if (data.SecretString) {
      return JSON.parse(data.SecretString);
    } else {
      throw new Error('Secret is binary and not supported');
    }
  } catch (error) {
    console.error('Error retrieving secret:', error);
    throw new Error(`Failed to retrieve secret: ${error.message}`);
  }
}

/**
 * Helper function to emit configuration issue metrics to CloudWatch
 * @param {string} issueType - Type of configuration issue
 * @param {object} dimensions - Dimensions for the metric
 * @returns {Promise<void>}
 */
async function emitConfigurationIssueMetric(issueType, dimensions) {
  try {
    // Prepare dimensions array for CloudWatch
    const metricDimensions = Object.entries(dimensions).map(([name, value]) => ({
      Name: name,
      Value: String(value)
    }));
    
    // Emit metric
    await cloudwatch.putMetricData({
      Namespace: 'WhatsAppProcessingEngine',
      MetricData: [
        {
          MetricName: 'AssistantConfigurationIssue',
          Value: 1,
          Unit: 'Count',
          Dimensions: [
            ...metricDimensions,
            { Name: 'IssueType', Value: issueType }
          ]
        }
      ]
    }).promise();
    
    console.log('Emitted configuration issue metric', {
      metric_name: 'AssistantConfigurationIssue',
      issue_type: issueType,
      dimensions
    });
  } catch (error) {
    console.error('Error emitting metric:', error);
  }
} 