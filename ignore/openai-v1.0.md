# OpenAI Integration for WhatsApp Processing Engine - v1.0

## 1. Overview

This document outlines the integration between the WhatsApp Processing Engine and OpenAI's Assistants API. This integration enables AI-powered message generation with template variable extraction for WhatsApp communication.

The core concept involves:
1. Creating an OpenAI thread for the conversation
2. Providing the full context object to the AI
3. Using an assistant specialized in extracting template variables
4. Processing the assistant's function calls to the `initial_whatsapp_message` function
5. Delivering the resulting message through Twilio
6. Maintaining state and context throughout the process

## 2. Integration Flow

### 2.1 Rate Limit Handling with Exponential Backoff

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

### 2.2 Thread Creation and Message Submission

```javascript
/**
 * Creates an OpenAI thread and adds the context as a message
 * @param {object} openai - Initialized OpenAI client
 * @param {object} contextObject - Full context object with all conversation data
 * @returns {Promise<object>} - Object containing thread_id
 */
async function createOpenAIThread(openai, contextObject) {
  const logger = createLogger(contextObject);
  
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
    
    // Convert context object to a structured message for the AI
    const messageContent = JSON.stringify(contextObject, null, 2);
    
    try {
      // Add the context object as a message to the thread (with retry logic and timeout)
      await withExponentialBackoff(
        () => openai.beta.threads.messages.create(threadId, {
          role: 'user',
          content: messageContent
        }),
        [],
        { timeoutMs: 30000 }  // 30 second timeout for message creation (larger content)
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
      // Specific error handling for message creation failure
      console.error('Failed to add message to thread, but thread was created', {
        thread_id: threadId,
        conversation_id: contextObject.conversation_data.conversation_id,
        error: messageError.message,
        error_code: messageError.status || 'unknown',
        is_timeout: messageError.message.includes('timed out')
      });
      
      // We should still return the thread_id even if message creation failed
      // The calling function can decide whether to retry or use the thread
      return {
        thread_id: threadId,
        message_creation_failed: true,
        error: messageError.message
      };
    }
  } catch (error) {
    // Categorize the error for better monitoring and handling
    const errorCategory = categorizeOpenAIError(error);
    
    console.error('Error creating OpenAI thread:', {
      error_message: error.message,
      error_category: errorCategory,
      error_code: error.status || 'unknown',
      conversation_id: contextObject.conversation_data.conversation_id,
      is_timeout: error.message.includes('timed out'),
      timestamp: new Date().toISOString()
    });
    
    // Rethrow with additional context
    throw new Error(`Failed to create OpenAI thread: ${error.message} [${errorCategory}]`);
  }
}

/**
 * Categorizes OpenAI errors into meaningful groups for monitoring and handling
 * @param {Error} error - The error object from OpenAI API
 * @returns {string} - Error category
 */
function categorizeOpenAIError(error) {
  // Check for specific OpenAI error types
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

### 2.3 Run Creation and Execution

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
    
    // Create a run with the specified assistant (with retry logic)
    const run = await withExponentialBackoff(
      () => openai.beta.threads.runs.create(threadId, {
        assistant_id: assistantId
      }),
      { timeoutMs: 60000 }
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

### 2.4 Run Polling and Status Monitoring

```javascript
/**
 * Polls the run status until completion or action required
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
    
    // Poll until terminal state or timeout
    let run = await withExponentialBackoff(
      () => openai.beta.threads.runs.retrieve(threadId, runId),
      { timeoutMs: 60000 }
    );
    console.log('Initial run status:', { status: run.status });
    
    while (['queued', 'in_progress', 'cancelling'].includes(run.status)) {
      // Check for timeout
      if (Date.now() - startTime > maxPollDuration) {
        throw new Error('Run polling timed out after 10 minutes');
      }
      
      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, currentPollInterval));
      
      // Gradually increase poll interval with a cap
      currentPollInterval = Math.min(currentPollInterval * 1.5, maxPollInterval);
      
      // Get updated run status (with retry logic)
      run = await withExponentialBackoff(
        () => openai.beta.threads.runs.retrieve(threadId, runId),
        { timeoutMs: 60000 }
      );
      console.log('Updated run status:', { status: run.status });
      
      // Return immediately if action is required or completed
      if (run.status === 'requires_action' || 
          run.status === 'completed' || 
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

### 2.5 Function Call Processing

```javascript
/**
 * Processes the required action from the run
 * @param {object} openai - Initialized OpenAI client
 * @param {object} run - OpenAI run object with requires_action status
 * @param {string} threadId - OpenAI thread ID
 * @param {object} contextObject - Full context object
 * @param {object} twilioClient - Initialized Twilio client
 * @returns {Promise<object>} - Result of the function execution
 */
async function processRequiredAction(openai, run, threadId, contextObject, twilioClient) {
  try {
    if (run.status !== 'requires_action' || run.required_action.type !== 'submit_tool_outputs') {
      throw new Error(`Run is not in requires_action state or tool outputs not required`);
    }
    
    const toolCalls = run.required_action.submit_tool_outputs.tool_calls;
    const toolOutputs = [];
    
    for (const toolCall of toolCalls) {
      console.log('Processing tool call', { 
        id: toolCall.id, 
        function: toolCall.function.name
      });
      
      if (toolCall.function.name === 'initial_whatsapp_message') {
        // Parse the function arguments from the tool call
        const functionArgs = JSON.parse(toolCall.function.arguments);
        
        // Verify required arguments are present
        if (!functionArgs.content_variables) {
          throw new Error('content_variables not provided in function arguments');
        }
        
        // Execute the initial_whatsapp_message function
        const result = await executeInitialWhatsAppMessage(
          functionArgs, 
          contextObject, 
          twilioClient
        );
        
        // Add the result to tool outputs
        toolOutputs.push({
          tool_call_id: toolCall.id,
          output: JSON.stringify(result)
        });
      } else {
        throw new Error(`Unknown function name: ${toolCall.function.name}`);
      }
    }
    
    // Submit the tool outputs back to OpenAI (with retry logic)
    console.log('Submitting tool outputs', { 
      thread_id: threadId, 
      run_id: run.id, 
      num_outputs: toolOutputs.length 
    });
    
    const updatedRun = await withExponentialBackoff(
      () => openai.beta.threads.runs.submitToolOutputs(
        threadId,
        run.id,
        { tool_outputs: toolOutputs },
        { timeoutMs: 60000 }
      ),
      []
    );
    
    return {
      tool_outputs: toolOutputs,
      updated_run: updatedRun
    };
  } catch (error) {
    console.error('Error processing required action:', error);
    throw new Error(`Failed to process required action: ${error.message}`);
  }
}
```

### 2.6 WhatsApp Message Execution Function

```javascript
/**
 * Executes the initial WhatsApp message function
 * @param {object} functionArgs - Arguments from the OpenAI function call
 * @param {object} contextObject - Full context object
 * @param {object} twilioClient - Initialized Twilio client
 * @returns {Promise<object>} - Result of the WhatsApp message send operation
 */
async function executeInitialWhatsAppMessage(functionArgs, contextObject, twilioClient) {
  try {
    console.log('Executing initial_whatsapp_message function');
    
    // Merge the content_variables from function arguments into context object
    const updatedContext = {
      ...contextObject,
      content_variables: functionArgs.content_variables
    };
    
    // Get Twilio credentials from Secrets Manager
    const twilioCredentials = await getSecretValue(
      updatedContext.channel_config.whatsapp.whatsapp_credentials_id
    );
    
    // Extract required information from context
    const recipientTel = updatedContext.frontend_payload.recipient_data.recipient_tel;
    const companyWhatsAppNumber = updatedContext.channel_config.whatsapp.company_whatsapp_number;
    
    // Send the WhatsApp message via Twilio API
    const messageResult = await sendWhatsAppViaTwilio(
      twilioClient,
      recipientTel,
      companyWhatsAppNumber,
      updatedContext.content_variables,
      twilioCredentials
    );
    
    console.log('WhatsApp message sent successfully', { 
      message_sid: messageResult.sid,
      status: messageResult.status
    });
    
    // Update the conversation record in DynamoDB
    await updateConversationRecord(updatedContext, messageResult);
    
    // Return the result to be passed back to OpenAI
    return {
      status: 'success',
      message_id: messageResult.sid,
      delivery_status: messageResult.status,
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    console.error('Error executing initial_whatsapp_message:', error);
    
    // Return error information to be passed back to OpenAI
    return {
      status: 'error',
      error: error.message,
      timestamp: new Date().toISOString()
    };
  }
}
```

### 2.7 Twilio Message Sending Function

```javascript
/**
 * Sends a WhatsApp message via Twilio API
 * @param {object} twilioClient - Initialized Twilio client
 * @param {string} recipientNumber - Recipient's phone number
 * @param {string} senderNumber - Company's WhatsApp number
 * @param {object} contentVariables - Variables to insert into the template
 * @param {object} credentials - Twilio credentials
 * @returns {Promise<object>} - Twilio message result
 */
async function sendWhatsAppViaTwilio(
  twilioClient, 
  recipientNumber, 
  senderNumber, 
  contentVariables,
  credentials
) {
  try {
    console.log('Sending WhatsApp message via Twilio');
    
    // Ensure phone numbers are properly formatted for Twilio
    const formattedRecipientNumber = formatPhoneNumberForTwilio(recipientNumber);
    const formattedSenderNumber = formatPhoneNumberForTwilio(senderNumber);
    
    // Create the message options
    const messageOptions = {
      from: `whatsapp:${formattedSenderNumber}`,
      to: `whatsapp:${formattedRecipientNumber}`,
      contentSid: credentials.twilio_template_sid, // Template ID from Twilio
      contentVariables: JSON.stringify(contentVariables)
    };
    
    // Send the message using Twilio
    const message = await twilioClient.messages.create(messageOptions);
    
    console.log('Twilio message sent', { 
      sid: message.sid, 
      status: message.status 
    });
    
    return message;
  } catch (error) {
    console.error('Error sending WhatsApp message via Twilio:', error);
    throw new Error(`Failed to send WhatsApp message: ${error.message}`);
  }
}

/**
 * Formats a phone number for Twilio
 * @param {string} phoneNumber - Phone number to format
 * @returns {string} - Formatted phone number
 */
function formatPhoneNumberForTwilio(phoneNumber) {
  // Remove any non-digit characters
  return phoneNumber.replace(/\D/g, '');
}
```

### 2.8 DynamoDB Conversation Update

```javascript
/**
 * Updates the conversation record with message results
 * @param {object} contextObject - Full context object
 * @param {object} messageResult - Result from Twilio message send
 * @returns {Promise<object>} - Updated conversation record
 */
async function updateConversationRecord(contextObject, messageResult) {
  try {
    console.log('Updating conversation record in DynamoDB');
    
    // Calculate processing time
    const startTime = new Date(contextObject.frontend_payload.request_data.initial_request_timestamp).getTime();
    const endTime = Date.now();
    const processingTimeMs = endTime - startTime;
    
    // Create the message entry for the messages array
    const messageEntry = {
      entry_id: uuidv4(),
      message_timestamp: new Date().toISOString(),
      role: 'assistant',
      content: JSON.stringify(contextObject.content_variables),
      ai_prompt_tokens: null, // These will be added once we get them from OpenAI
      ai_completion_tokens: null,
      ai_total_tokens: null
    };
    
    // Update the DynamoDB record
    const result = await dynamoDB.update({
      TableName: process.env.CONVERSATION_TABLE_NAME,
      Key: {
        recipient_tel: contextObject.frontend_payload.recipient_data.recipient_tel,
        conversation_id: contextObject.conversation_data.conversation_id
      },
      UpdateExpression: `
        SET thread_id = :thread_id,
            processing_time_ms = :processing_time,
            conversation_status = :status,
            task_complete = :task_complete,
            messages = list_append(if_not_exists(messages, :empty_list), :new_message),
            updated_at = :updated_at
      `,
      ExpressionAttributeValues: {
        ':thread_id': contextObject.thread_id,
        ':processing_time': processingTimeMs,
        ':status': 'initial_message_sent',
        ':task_complete': true,
        ':new_message': [messageEntry],
        ':empty_list': [],
        ':updated_at': new Date().toISOString()
      },
      ReturnValues: 'ALL_NEW'
    }).promise();
    
    console.log('Conversation record updated successfully', {
      conversation_id: contextObject.conversation_data.conversation_id,
      thread_id: contextObject.thread_id,
      status: 'initial_message_sent'
    });
    
    return result.Attributes;
  } catch (error) {
    console.error('Error updating conversation record:', error);
    throw new Error(`Failed to update conversation record: ${error.message}`);
  }
}
```

## 3. Main Integration Function

```javascript
/**
 * Main function to process a message with OpenAI
 * @param {object} openai - Initialized OpenAI client
 * @param {object} contextObject - Full context object
 * @param {object} twilioClient - Initialized Twilio client
 * @returns {Promise<object>} - Result of the OpenAI processing
 */
async function processWithOpenAI(openai, contextObject, twilioClient) {
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
    
    // Poll run status until completion or action required
    const finalRun = await pollRunStatus(openai, thread_id, run.id);
    
    // Process function calls if action is required
    if (finalRun.status === 'requires_action') {
      const actionResult = await processRequiredAction(
        openai, finalRun, thread_id, contextObject, twilioClient
      );
      
      // Poll run again after submitting tool outputs
      const completedRun = await pollRunStatus(openai, thread_id, run.id);
      
      // Check if run completed successfully
      if (completedRun.status === 'completed') {
        console.log('Run completed successfully after tool outputs', {
          thread_id,
          run_id: run.id,
          processing_time_ms: Date.now() - startTime
        });
      } else {
        console.error('Run did not complete successfully after tool outputs', {
          thread_id,
          run_id: run.id,
          final_status: completedRun.status
        });
        throw new Error(`Run failed with status: ${completedRun.status}`);
      }
      
      return {
        thread_id,
        run_id: run.id,
        status: 'completed',
        tool_outputs: actionResult.tool_outputs,
        processing_time_ms: Date.now() - startTime
      };
    } else if (finalRun.status === 'completed') {
      // This shouldn't normally happen as we expect a function call
      console.warn('Run completed without requiring action', {
        thread_id,
        run_id: run.id
      });
      
      // Get the assistant's messages (with retry logic)
      const messages = await withExponentialBackoff(
        () => openai.beta.threads.messages.list(thread_id),
        []
      );
      const assistantMessages = messages.data.filter(msg => msg.role === 'assistant');
      
      // This branch doesn't trigger the initial WhatsApp message function
      // Handle as exceptional case
      console.error('Assistant did not call initial_whatsapp_message function', {
        thread_id,
        run_id: run.id,
        messages: assistantMessages.map(m => m.content)
      });
      
      throw new Error('Assistant did not call the required function');
    } else {
      // Run failed, was cancelled, or expired
      console.error('Run ended with unexpected status', {
        thread_id,
        run_id: run.id,
        status: finalRun.status
      });
      
      throw new Error(`Run ended with status: ${finalRun.status}`);
    }
  } catch (error) {
    console.error('Error in OpenAI processing:', error);
    throw error;
  }
}
```

## 4. Integration in Main Lambda Handler

```javascript
// Excerpt from main Lambda handler
try {
  // Previous steps: SQS message handling, context parsing, conversation creation
  
  // Get channel credentials from AWS Secrets Manager
  const channelCredentials = await getCredentials(
    channel_config.whatsapp.whatsapp_credentials_id
  );
  
  // Get AI credentials from AWS Secrets Manager
  const aiCredentials = await getCredentials(
    contextObject.ai_config.ai_api_key_reference
  );
  
  // Initialize OpenAI client with global AI API key
  const openai = new OpenAI({
    apiKey: aiCredentials.ai_api_key
  });
  
  // Initialize Twilio client
  const twilioClient = twilio(
    channelCredentials.twilio_account_sid,
    channelCredentials.twilio_auth_token
  );
  
  // Process with OpenAI
  const openAiResult = await processWithOpenAI(openai, contextObject, twilioClient);
  
  // At this point:
  // 1. OpenAI has processed the request
  // 2. WhatsApp message has been sent via Twilio
  // 3. Conversation record has been updated in DynamoDB with:
  //    - Token usage in the messages array
  //    - Associated project_id for usage tracking
  //    - Full conversation context and results
  // 4. SQS message can be deleted
  
  await sqs.deleteMessage({
    QueueUrl: process.env.WHATSAPP_QUEUE_URL,
    ReceiptHandle: receiptHandle
  }).promise();
  
  console.log('Message processed successfully', {
    conversation_id: contextObject.conversation_data.conversation_id,
    thread_id: contextObject.thread_id,
    project_id: contextObject.frontend_payload.project_data.project_id  // Log project_id for tracking
  });
  
  return { statusCode: 200 };
} catch (error) {
  // Error handling logic
}
```

### 4.1 API Key Management and Usage Tracking

The system uses a simplified approach to OpenAI API key management and usage tracking:

1. **Single API Key Strategy**:
   - One OpenAI API key used across the entire application
   - Key stored and rotated in AWS Secrets Manager at a designated global reference path
   - The key reference is stored in the `ai_config.ai_api_key_reference` field as `ai-api-key/global`
   - Separating the AI API key from channel-specific credentials provides cleaner architecture
   - Simplifies key rotation and management across the system

2. **Usage Tracking**:
   - Project-level tracking through `project_id` in conversations table
   - Token usage tracked per message in the messages array:
     ```javascript
     {
       ai_prompt_tokens: number,
       ai_completion_tokens: number,
       ai_total_tokens: number
     }
     ```
   - Enables detailed usage reporting and cost allocation per project
   - Facilitates billing and monitoring without OpenAI organization overhead

3. **Benefits**:
   - Simplified key management with a single source of truth
   - Clean separation between channel credentials and AI service credentials
   - Centralized usage tracking in DynamoDB
   - Easy querying for project-specific usage
   - Clear cost allocation through message-level token counting

## 5. Concurrency and Robustness Considerations

### 5.1 Asynchronous Processing

The OpenAI Assistants API has inherent asynchronous behavior through the Run API. Several considerations:

1. **Long-Running Operations**:
   - OpenAI runs can take variable time to complete
   - The heartbeat pattern (already implemented) is essential for extending SQS visibility timeout
   - The polling mechanism must be robust with proper timeouts

2. **Idempotent Processing**:
   - All operations should be idempotent to allow safe retries
   - Thread creation, message sending, and DynamoDB updates should be designed for idempotency
   - Use of existing request_id and conversation_id maintains traceability across retries

### 5.2 Rate Limit Handling

1. **OpenAI Rate Limits**:
   - Thread creation: ~10-20 requests per minute depending on tier
   - Run creation: ~10-15 requests per minute
   - Message creation: Higher limits but still constrained
   - Status checks: Higher limits but can be affected by heavy usage

2. **Exponential Backoff Implementation**:
   - All OpenAI API calls use the `withExponentialBackoff` wrapper
   - Initial delay: 1 second
   - Maximum delay: 30 seconds
   - Maximum retries: 5 attempts
   - Random jitter: ±20% to prevent "thundering herd" problem

3. **Adaptive Response to Rate Limiting**:
   - Automatically adjusts based on OpenAI's response
   - Backoff becomes progressively longer under sustained high load
   - Returns to normal immediately when rate limits are no longer hit

4. **Monitoring Rate Limits**:
   - Log retry attempts with detailed diagnostics
   - Consider adding custom CloudWatch metrics to track rate limit hits
   - Set up alerts if rate limiting becomes excessive

The exponential backoff pattern combined with our existing SQS queue and visibility timeout management provides a comprehensive solution for handling both expected rate limits and unexpected API issues.

### 5.3 Error Handling

1. **Categorized Errors**:
   - **Transient errors**: Network issues, OpenAI rate limits, Twilio temporary failures
   - **Permanent errors**: Invalid credentials, invalid thread/run IDs, invalid function arguments
   - Handle both types appropriately with proper retry logic

2. **Partial Success Handling**:
   - OpenAI success but Twilio failure
   - Thread created but run failed
   - Run succeeded but function execution failed
   - Each requires specific recovery steps

3. **Dead Letter Queue Integration**:
   - Messages that fail repeatedly will go to DLQ
   - DLQ processor should update conversation status to 'failed'

### 5.4 Monitoring Integration

1. **Custom Metrics**:
   - OpenAI API response times
   - Function execution times
   - Success/failure rates

2. **Detailed Logging**:
   - Log each step of the OpenAI process
   - Include correlation IDs (conversation_id, thread_id, run_id) in all logs
   - Mask sensitive data in logs

## 6. Twilio Template Integration

The OpenAI function `initial_whatsapp_message` will output content variables to be used in Twilio's template messaging system.

1. **Twilio Template Setup**:
   - Templates must be pre-approved by WhatsApp
   - Templates contain variables like `{{1}}`, `{{2}}`, etc.
   - These variables are filled by the content_variables from our function

2. **Content Variable Mapping**:
   - OpenAI extracts relevant information from context
   - Assistant maps information to numbered variables
   - Function call passes these variables to Twilio

Example Template:
```
Hi {{1}}! This is {{2}} from {{3}}. We're reaching out about your application for the {{4}} position. Your interview is scheduled for {{5}}. Reply to this message to confirm or reschedule.
```

Content Variables (from OpenAI):
```json
{
  "1": "John",           // recipient_first_name
  "2": "Carol",          // company_rep_1
  "3": "Cucumber Recruitment",  // company_name
  "4": "Software Engineer",     // project_data.job_title
  "5": "Tuesday, July 12 at 2pm"  // Extracted from project_data
}
```

## 7. Security Considerations

1. **API Key Management**:
   - Never log API keys or credentials
   - Use AWS Secrets Manager for all sensitive values
   - Rotate keys regularly

2. **Content Security**:
   - Validate and sanitize content variables before sending
   - Ensure AI-generated content meets policy requirements
   - Monitor for potential misuse

3. **Data Protection**:
   - Encrypt sensitive data in transit and at rest
   - Limit exposure of personally identifiable information
   - Implement proper access controls

## 8. Summary

This integration approach:

1. Creates an OpenAI thread and provides the full context object
2. Uses an AI assistant specifically configured to extract template variables
3. Processes the assistant's function call to initial_whatsapp_message
4. Sends the WhatsApp message via Twilio with extracted content variables
5. Updates the DynamoDB conversation record with processing results
6. Maintains full context and data flow throughout the process

The design leverages OpenAI's Assistants API for flexible template variable extraction while maintaining a robust processing flow with proper error handling, security, and monitoring. 