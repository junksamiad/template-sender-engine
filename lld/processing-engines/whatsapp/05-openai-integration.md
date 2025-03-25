# WhatsApp Processing Engine - OpenAI Integration

> **Part 5 of 9 in the WhatsApp Processing Engine documentation series**

## 1. Introduction

This document details how the WhatsApp Processing Engine integrates with the OpenAI Assistants API to process messages. The integration handles thread creation, message submission, run management, and result processing, with particular attention to handling long-running operations and potential rate limits.

## 2. Integration Architecture

The OpenAI integration follows these key architectural principles:

1. **Thread-Based Processing**: Each conversation uses a dedicated OpenAI thread
2. **Asynchronous Run Management**: The engine manages asynchronous OpenAI runs
3. **Resilient Operation**: Handles API rate limits and temporary failures
4. **JSON Response Parsing**: Processes structured JSON responses from the assistant
5. **Context Preservation**: Maintains conversation context between messages
6. **Processing Stage Tracking**: Tracks the processing status for error handling

The system stores OpenAI thread IDs in the conversation record, enabling conversation continuity across multiple messages.

### 2.1 Assistant ID Selection

The WhatsApp Processing Engine uses a specific OpenAI assistant configured for template message generation. The assistant ID is sourced from the context object as follows:

```javascript
// Assistant ID is retrieved from the context object's ai_config section
const assistantId = contextObject.ai_config.assistant_id_template_sender;
```

This `assistant_id_template_sender` field is populated by the Channel Router when creating the context object, based on the `wa_company_data` DynamoDB table's `ai_config` section for the specific company and project. 

The template sender assistant is specifically designed to:
1. Process the context object
2. Extract relevant information for template variables
3. Generate appropriate JSON-formatted template variables
4. Return a structured response that can be used with WhatsApp templates

For reply handling (which is not implemented in this build but will be in future versions), a different assistant ID (`assistant_id_replies`) would be used from the same context object.

## 3. Rate Limit Handling with Exponential Backoff

OpenAI's API has rate limits that must be handled gracefully. A robust exponential backoff mechanism is implemented:

```javascript
/**
 * Wrapper function to implement exponential backoff for OpenAI API calls
 * @param {Function} apiCallFn - The API call function to execute with retry logic
 * @param {Array} args - Arguments to pass to the API call function
 * @param {object} options - Retry options
 * @returns {Promise<any>} - Result from the API call
 */
async function withExponentialBackoff(apiCallFn, args = [], options = {}) {
  const {
    maxRetries = 5,
    initialDelayMs = 1000,
    maxDelayMs = 30000,
    retryStatusCodes = [429, 500, 503],
    timeoutMs = 60000  // Default 60-second timeout for API calls
  } = options;
  
  let attempt = 0;
  
  while (true) {
    try {
      // Create a promise that rejects after timeoutMs
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => {
          reject(new Error(`API call timed out after ${timeoutMs}ms`));
        }, timeoutMs);
      });
      
      // Race the API call against the timeout
      return await Promise.race([
        apiCallFn(...args),
        timeoutPromise
      ]);
    } catch (error) {
      attempt++;
      
      // Add timeout flag to help with monitoring
      const isTimeout = error.message.includes('timed out');
      const isRateLimit = error.status === 429;
      const isRetryableServerError = retryStatusCodes.includes(error.status);
      const isRetryableError = isTimeout || isRateLimit || isRetryableServerError;
      
      // Only retry on rate limits, timeouts, or specific server errors
      if (isRetryableError && attempt < maxRetries) {
        // Calculate backoff delay with exponential increase and jitter
        const baseDelay = Math.min(initialDelayMs * Math.pow(2, attempt), maxDelayMs);
        // Add random jitter (±20%) to prevent thundering herd problem
        const jitter = baseDelay * (0.8 + Math.random() * 0.4);
        const delayMs = Math.floor(jitter);
        
        console.log(`API call failed with ${isTimeout ? 'timeout' : error.status}, retrying in ${delayMs}ms (attempt ${attempt}/${maxRetries})`, {
          error_message: error.message,
          status: error.status || 'timeout',
          is_timeout: isTimeout,
          is_rate_limit: isRateLimit
        });
        
        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, delayMs));
      } else {
        // Log and rethrow on permanent errors or max retries exceeded
        if (attempt >= maxRetries) {
          console.error(`Maximum retry attempts (${maxRetries}) exceeded for API call`, {
            error_message: error.message,
            status: error.status || 'timeout',
            is_timeout: isTimeout
          });
        }
        throw error;
      }
    }
  }
}
```

## 4. Thread Creation and Message Submission

### 4.1 Creating a Thread

The first step in OpenAI processing is creating a thread to maintain conversation context:

```javascript
/**
 * Creates an OpenAI thread and adds the context as a message
 * @param {object} openai - Initialized OpenAI client
 * @param {object} contextObject - Full context object with all conversation data
 * @returns {Promise<object>} - Object containing thread_id
 */
async function createOpenAIThread(openai, contextObject) {
  try {
    console.log('Creating new OpenAI thread', {
      conversation_id: contextObject.conversation_data.conversation_id
    });
    
    // Create a new thread with retry logic and timeout
    const thread = await withExponentialBackoff(
      () => openai.beta.threads.create(),
      [],
      { timeoutMs: 15000 }  // 15 second timeout for thread creation
    );
    const threadId = thread.id;
    
    console.log('Thread created successfully', { 
      thread_id: threadId,
      conversation_id: contextObject.conversation_data.conversation_id
    });
    
    // Update conversation record with thread ID
    await updateThreadId(contextObject.conversation_data, threadId);
    
    // Convert context object to a structured message for the AI
    const messageContent = JSON.stringify(contextObject, null, 2);
    
    try {
      // Add the context object as a message to the thread
      await withExponentialBackoff(
        () => openai.beta.threads.messages.create(threadId, {
          role: 'user',
          content: messageContent
        }),
        [],
        { timeoutMs: 30000 }  // 30 second timeout for message creation
      );
      
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
    // Categorize and log error
    const errorCategory = categorizeOpenAIError(error);
    
    console.error('Error creating OpenAI thread:', {
      error_message: error.message,
      error_category: errorCategory,
      error_code: error.status || 'unknown'
    });
    
    throw new Error(`Failed to create OpenAI thread: ${error.message} [${errorCategory}]`);
  }
}
```

### 4.2 Error Categorization

The system categorizes OpenAI errors to enable better handling and monitoring:

```javascript
/**
 * Categorizes OpenAI errors into meaningful groups for monitoring and handling
 * @param {Error} error - The error object from OpenAI API
 * @returns {string} - Error category
 */
function categorizeOpenAIError(error) {
  if (!error) return 'unknown';
  
  // Handle timeout errors
  if (error.message.includes('timed out')) {
    return 'timeout';
  }
  
  // Handle rate limiting errors
  if (error.status === 429) {
    return 'rate_limit';
  }
  
  // Handle authentication errors
  if (error.status === 401) {
    return 'authentication';
  }
  
  // Handle permissions and scope errors
  if (error.status === 403) {
    return 'authorization';
  }
  
  // Handle resource not found
  if (error.status === 404) {
    return 'not_found';
  }
  
  // Handle invalid requests
  if (error.status === 400) {
    return 'invalid_request';
  }
  
  // Handle server errors
  if (error.status >= 500 && error.status < 600) {
    return 'server_error';
  }
  
  // Handle network errors
  if (error.code === 'ECONNRESET' || 
      error.code === 'ETIMEDOUT' || 
      error.code === 'ESOCKETTIMEDOUT') {
    return 'network_error';
  }
  
  // Default to 'api_error' for other error types
  return 'api_error';
}
```

## 5. Run Creation and Execution

### 5.1 Creating and Starting a Run

After adding the context message to the thread, a run is created to process it:

```javascript
/**
 * Creates and runs the assistant on the thread
 * @param {object} openai - Initialized OpenAI client
 * @param {string} threadId - OpenAI thread ID
 * @param {string} assistantId - OpenAI assistant ID (from context object)
 * @returns {Promise<object>} - Run object with status information
 */
async function createAndStartRun(openai, threadId, assistantId) {
  try {
    console.log('Creating run with assistant', { 
      thread_id: threadId, 
      assistant_id: assistantId 
    });
    
    // Create a run with the specified assistant
    const run = await withExponentialBackoff(
      () => openai.beta.threads.runs.create(threadId, {
        assistant_id: assistantId
      }),
      [],
      { timeoutMs: 60000 }  // 60 second timeout for run creation
    );
    
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
```

### 5.2 Polling Run Status

Since OpenAI runs are asynchronous, the system needs to poll for completion:

```javascript
/**
 * Polls the run status until completion or error
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
    let run = await withExponentialBackoff(
      () => openai.beta.threads.runs.retrieve(threadId, runId),
      [],
      { timeoutMs: 60000 }
    );
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
      run = await withExponentialBackoff(
        () => openai.beta.threads.runs.retrieve(threadId, runId),
        [],
        { timeoutMs: 60000 }
      );
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
```

## 6. Processing the Assistant's Response

After the run completes, the system extracts the JSON response from the assistant's message:

```javascript
/**
 * Extracts and parses the JSON response from the assistant's message
 * @param {object} openai - Initialized OpenAI client
 * @param {string} threadId - OpenAI thread ID
 * @param {object} contextObject - Context object with conversation and configuration data
 * @returns {Promise<object>} - Parsed JSON variables from assistant response
 */
async function getAssistantResponse(openai, threadId, contextObject) {
  try {
    // Get assistant messages
    const messages = await withExponentialBackoff(
      () => openai.beta.threads.messages.list(threadId),
      [],
      { timeoutMs: 60000 }
    );
    
    // Find the most recent assistant message
    const assistantMessages = messages.data.filter(msg => msg.role === 'assistant');
    const latestMessage = assistantMessages[0];
    
    if (!latestMessage) {
      throw new Error('No assistant message found after completed run');
    }
    
    console.log('Retrieved assistant message', {
      thread_id: threadId,
      message_id: latestMessage.id
    });
    
    // Extract content from message
    const messageContent = latestMessage.content[0].text.value;
    
    // Parse JSON from the message content
    let contentVariables;
    try {
      // Extract JSON content from message (handle potential text before/after JSON)
      const jsonMatch = messageContent.match(/```json\n([\s\S]*?)\n```/) || 
                       messageContent.match(/\{[\s\S]*\}/);
                       
      const jsonContent = jsonMatch ? jsonMatch[1] || jsonMatch[0] : messageContent;
      const parsedContent = JSON.parse(jsonContent);
      
      // Validate the parsed content has content_variables field
      if (!parsedContent.content_variables) {
        throw new Error('Missing content_variables in assistant response');
      }
      
      contentVariables = parsedContent.content_variables;
      console.log('Successfully parsed content_variables from assistant response', { 
        variable_count: Object.keys(contentVariables).length 
      });
      
      return contentVariables;
    } catch (parseError) {
      console.error('Failed to parse JSON from assistant response', {
        parse_error: parseError.message,
        message_content: messageContent
      });
      
      // Emit metric for monitoring
      await emitConfigurationIssueMetric('InvalidJSONResponse', {
        conversation_id: contextObject.conversation_data.conversation_id,
        assistant_id: contextObject.ai_config.assistant_id_template_sender
      });
      
      throw new Error(`Failed to parse assistant response as JSON: ${parseError.message}`);
    }
  } catch (error) {
    console.error('Error getting assistant response:', error);
    throw error;
  }
}
```

## 7. Main Integration Function

The complete integration is orchestrated by a main function that handles the entire OpenAI processing flow:

```javascript
/**
 * Main function to process a message with OpenAI
 * @param {object} openai - Initialized OpenAI client
 * @param {object} contextObject - Full context object
 * @returns {Promise<object>} - Result of the OpenAI processing with content variables
 */
async function processWithOpenAI(openai, contextObject) {
  try {
    console.log('Starting OpenAI processing');
    const startTime = Date.now();
    
    // Create OpenAI thread and add context as message
    const { thread_id } = await createOpenAIThread(openai, contextObject);
    
    // Update context object with thread_id
    contextObject.thread_id = thread_id;
    
    // Get assistant ID from context - using the template sender assistant for initial messages
    // This assistant ID is populated by the Channel Router from the wa_company_data table
    const assistantId = contextObject.ai_config.assistant_id_template_sender;
    
    // Create and start the run
    const run = await createAndStartRun(openai, thread_id, assistantId);
    
    // Poll run status until completion
    const finalRun = await pollRunStatus(openai, thread_id, run.id);
    
    // Process run results
    if (finalRun.status === 'completed') {
      // Get content variables from assistant response
      const contentVariables = await getAssistantResponse(openai, thread_id, contextObject);
      
      // Calculate total processing time
      const processingTimeMs = Date.now() - startTime;
      
      // Retrieve usage information
      let usageMetrics = {
        ai_prompt_tokens: 0,
        ai_completion_tokens: 0,
        ai_total_tokens: 0
      };
      
      // Try to get usage metrics from the run object if available
      if (finalRun.usage) {
        usageMetrics = {
          ai_prompt_tokens: finalRun.usage.prompt_tokens || 0,
          ai_completion_tokens: finalRun.usage.completion_tokens || 0,
          ai_total_tokens: finalRun.usage.total_tokens || 0
        };
      }
      
      // Update context object with content variables and all metrics
      contextObject.content_variables = contentVariables;
      contextObject.processing_time_ms = processingTimeMs;
      contextObject.conversation_status = 'processed_by_ai'; // Intermediate status before sending message
      contextObject.ai_usage = usageMetrics;
      
      // Initialize messages array if it doesn't exist
      if (!contextObject.messages) {
        contextObject.messages = [];
      }
      
      // Add the assistant's response as a message to track in the conversation
      contextObject.messages.push({
        role: 'assistant',
        content: JSON.stringify(contentVariables),
        ai_prompt_tokens: usageMetrics.ai_prompt_tokens,
        ai_completion_tokens: usageMetrics.ai_completion_tokens,
        ai_total_tokens: usageMetrics.ai_total_tokens,
        message_timestamp: new Date().toISOString()
      });
      
      console.log('Run completed successfully', {
        thread_id,
        run_id: run.id,
        processing_time_ms: processingTimeMs,
        variable_count: Object.keys(contentVariables).length,
        ai_prompt_tokens: usageMetrics.ai_prompt_tokens,
        ai_completion_tokens: usageMetrics.ai_completion_tokens,
        ai_total_tokens: usageMetrics.ai_total_tokens
      });
      
      // Return updated context object and processing results
      return {
        thread_id,
        run_id: run.id,
        status: 'completed',
        content_variables: contentVariables,
        processing_time_ms: processingTimeMs,
        usage: usageMetrics
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
        conversation_id: contextObject.conversation_data.conversation_id
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
 * Sends a WhatsApp template message using Twilio API
 * @param {object} contextObject - Context object with conversation data
 * @param {object} variables - Template variables (numeric keys with string values)
 * @returns {Promise<object>} - Result of sending message
 */
async function sendWhatsAppTemplateMessage(contextObject, variables) {
  try {
    console.log('Sending WhatsApp template message', {
      conversation_id: contextObject.conversation_data.conversation_id,
      recipient_tel: contextObject.frontend_payload.recipient_data.recipient_tel
    });
    
    // Get template name from company configuration
    // This could be stored in the context object or in a config setting
    const templateName = contextObject.wa_company_data_payload.template_name || 'default_template';
    const templateLanguage = contextObject.wa_company_data_payload.template_language || 'en_US';
    
    // Get WhatsApp credentials from Secrets Manager
    const whatsappCredentialsId = contextObject.channel_config.whatsapp.whatsapp_credentials_id;
    const twilioCredentials = await getSecretValue(whatsappCredentialsId);
    
    // Initialize Twilio client
    const twilioClient = twilio(
      twilioCredentials.twilio_account_sid,
      twilioCredentials.twilio_auth_token
    );
    
    // Prepare message options
    const messageOptions = {
      from: `whatsapp:${contextObject.channel_config.whatsapp.company_whatsapp_number}`,
      to: `whatsapp:${contextObject.frontend_payload.recipient_data.recipient_tel}`,
      contentSid: null,
      contentVariables: JSON.stringify(variables)
    };
    
    // Find the content SID for the template
    const templates = await twilioClient.messaging.contentAndTemplates.templates.list();
    const template = templates.find(t => 
      t.name === templateName && t.language === templateLanguage
    );
    
    if (!template) {
      throw new Error(`Template not found: ${templateName} (${templateLanguage})`);
    }
    
    messageOptions.contentSid = template.sid;
    
    // Send the message
    const message = await twilioClient.messages.create(messageOptions);
    
    console.log('WhatsApp template message sent', {
      message_sid: message.sid, 
      status: message.status,
      conversation_id: contextObject.conversation_data.conversation_id
    });
    
    // First retrieve the conversation record from DynamoDB
    const conversation = await getConversationRecord(
      contextObject.frontend_payload.recipient_data.recipient_tel,
      contextObject.conversation_data.conversation_id
    );
    
    // Add template message to conversation history with message details and usage metrics from the context
    const messageData = {
      role: 'assistant',
      content: `Template: ${templateName}`,
      usage: {
        prompt_tokens: contextObject.ai_usage?.ai_prompt_tokens || 0,
        completion_tokens: contextObject.ai_usage?.ai_completion_tokens || 0,
        total_tokens: contextObject.ai_usage?.ai_total_tokens || 0
      }
    };
    
    // Add message to conversation record
    await addMessageToConversation(conversation, messageData);
    
    // Prepare the final conversation update data
    const finalUpdateData = {
      conversation_status: 'initial_message_sent',
      thread_id: contextObject.thread_id,
      processing_time_ms: contextObject.processing_time_ms || (Date.now() - new Date(conversation.created_at).getTime()),
      task_complete: true,
      ai_prompt_tokens: contextObject.ai_usage?.ai_prompt_tokens || 0,
      ai_completion_tokens: contextObject.ai_usage?.ai_completion_tokens || 0,
      ai_total_tokens: contextObject.ai_usage?.ai_total_tokens || 0
    };
    
    // Update conversation record with final status and metrics
    await updateConversationRecord(conversation, finalUpdateData);
    
    return {
      success: true,
      status: message.status,
      sent_at: new Date().toISOString()
    };
  } catch (error) {
    console.error('Error sending WhatsApp template message:', error);
    throw error;
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
    // Create CloudWatch client
    const cloudwatch = new AWS.CloudWatch();
    
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
  } catch (metricError) {
    // Just log the error but don't throw - metrics should not break processing
    console.error('Failed to emit configuration issue metric', metricError);
  }
}
```

## 8. Integration with Twilio Message Sending

After processing with OpenAI, the updated context object with content variables is passed to the Twilio message sending function:

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
    const openAIResult = await processWithOpenAI(openai, contextObject);
    
    // Update context object with OpenAI processing results
    // Note: Most metrics are already added to the contextObject within processWithOpenAI
    // Here we ensure any additional metrics from the result are also available
    contextObject.thread_id = openAIResult.thread_id;
    contextObject.content_variables = openAIResult.content_variables;
    contextObject.processing_time_ms = openAIResult.processing_time_ms;
    
    // Ensure ai_usage is properly set
    if (openAIResult.usage) {
      contextObject.ai_usage = {
        ai_prompt_tokens: openAIResult.usage.ai_prompt_tokens,
        ai_completion_tokens: openAIResult.usage.ai_completion_tokens,
        ai_total_tokens: openAIResult.usage.ai_total_tokens
      };
    }
    
    // Send WhatsApp template message with content variables and all the collected metrics
    const messageResult = await sendWhatsAppTemplateMessage(contextObject, openAIResult.content_variables);
    
    // Return success result with key metrics
    return {
      success: true,
      thread_id: openAIResult.thread_id,
      processing_time_ms: openAIResult.processing_time_ms,
      ai_usage: contextObject.ai_usage
    };
  } catch (error) {
    console.error('Error processing WhatsApp message:', error);
    throw error;
  }
}
```

## 9. Error Detection for Assistant Configuration Issues

The system specifically detects configuration issues related to the assistant's response format:

```javascript
/**
 * Validates the structure of the assistant's response
 * @param {object} contentVariables - Parsed content variables from assistant
 * @param {object} contextObject - Context object with conversation data
 * @returns {boolean} - True if valid, throws error if invalid
 */
function validateAssistantResponse(contentVariables, contextObject) {
  if (!contentVariables || typeof contentVariables !== 'object') {
    emitConfigurationIssueMetric('InvalidResponseFormat', {
      conversation_id: contextObject.conversation_data.conversation_id,
      assistant_id: contextObject.ai_config.assistant_id_template_sender
    });
    throw new Error('Assistant response is not a valid object');
  }
  
  // Check for empty variables object
  if (Object.keys(contentVariables).length === 0) {
    emitConfigurationIssueMetric('EmptyVariables', {
      conversation_id: contextObject.conversation_data.conversation_id,
      assistant_id: contextObject.ai_config.assistant_id_template_sender
    });
    throw new Error('Assistant returned empty content_variables object');
  }
  
  return true;
}
```

This approach ensures the system can detect and report issues with the assistant's configuration or response format, enabling quick diagnosis and resolution of problems.

## 10. Monitoring and Metrics

To monitor OpenAI API usage and performance, several metrics are tracked:

```javascript
// Emit metrics for OpenAI API performance monitoring
await cloudwatch.putMetricData({
  Namespace: 'ChannelRouter',
  MetricData: [
    {
      MetricName: 'OpenAIThreadCreationTime',
      Value: threadCreationTime,
      Unit: 'Milliseconds'
    },
    {
      MetricName: 'OpenAIRunPollTime',
      Value: runPollTime,
      Unit: 'Milliseconds'
    },
    {
      MetricName: 'OpenAIAPITokens',
      Value: aiResponse.usage?.total_tokens || 0,
      Unit: 'Count'
    }
  ]
}).promise();
```

## 11. Thread Management and Cleanup

For the initial WhatsApp implementation, threads are created and retained indefinitely. In future versions, a thread cleanup mechanism may be implemented to handle:

1. Thread archiving after a period of inactivity
2. Thread deletion for completed conversations
3. Token usage optimization

## 12. Related Documentation

- [Overview and Architecture](./01-overview-architecture.md)
- [Conversation Management](./03-conversation-management.md)
- [Template Management](./06-template-management.md)
- [Error Handling Strategy](./07-error-handling-strategy.md)
- [Monitoring and Observability](./08-monitoring-observability.md)
- [Operations Playbook](./09-operations-playbook.md)

## 13. New Update Conversation Record Function

```
/**
 * Updates the conversation record with all metrics and final status
 * @param {object} conversation - The conversation record from DynamoDB
 * @param {object} updateData - Data to update in the conversation record
 * @returns {Promise<object>} - The updated conversation record
 */
async function updateConversationRecord(conversation, updateData) {
  try {
    console.log('Updating conversation record with metrics and final status', {
      conversation_id: conversation.conversation_id,
      status: updateData.conversation_status,
      processing_time_ms: updateData.processing_time_ms,
      thread_id: updateData.thread_id
    });
    
    const now = new Date().toISOString();
    
    // Build the update expression and attribute values
    let updateExpression = 'SET updated_at = :updated';
    const expressionAttributeValues = {
      ':updated': now
    };
    
    // Add each field from updateData to the expression
    Object.entries(updateData).forEach(([key, value]) => {
      updateExpression += `, ${key} = :${key}`;
      expressionAttributeValues[`:${key}`] = value;
    });
    
    // Update in DynamoDB
    await dynamoDB.update({
      TableName: process.env.CONVERSATION_TABLE_NAME,
      Key: {
        recipient_tel: conversation.recipient_tel,
        conversation_id: conversation.conversation_id
      },
      UpdateExpression: updateExpression,
      ExpressionAttributeValues: expressionAttributeValues
    }).promise();
    
    console.log('Conversation record updated successfully', {
      conversation_id: conversation.conversation_id,
      status: updateData.conversation_status,
      ai_total_tokens: updateData.ai_total_tokens || 0
    });
    
    return {
      ...conversation,
      ...updateData,
      updated_at: now
    };
  } catch (error) {
    console.error('Error updating conversation record', error);
    throw error;
  }
}