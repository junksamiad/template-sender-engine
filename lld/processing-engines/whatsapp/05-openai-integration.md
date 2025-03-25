# WhatsApp Processing Engine - OpenAI Integration

> **Part 5 of 10 in the WhatsApp Processing Engine documentation series**

## 1. Introduction

This document details how the WhatsApp Processing Engine integrates with the OpenAI Assistants API to process messages. The integration handles thread creation, message submission, run management, and result processing, with particular attention to handling long-running operations and potential rate limits.

## 2. Integration Architecture

The OpenAI integration follows these key architectural principles:

1. **Thread-Based Processing**: Each conversation uses a dedicated OpenAI thread
2. **Asynchronous Run Management**: The engine manages asynchronous OpenAI runs
3. **Resilient Operation**: Handles API rate limits and temporary failures
4. **Functional Implementation**: Uses OpenAI function calls for structured outputs
5. **Context Preservation**: Maintains conversation context between messages

The system stores OpenAI thread IDs in the conversation record, enabling conversation continuity across multiple messages.

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
      
      // Return immediately if action is required or in terminal state
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

## 6. Main Integration Function

The complete integration is orchestrated by a main function that handles the entire OpenAI processing flow:

```javascript
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
    
    // Poll run status until completion or action required
    const finalRun = await pollRunStatus(openai, thread_id, run.id);
    
    // Check final run status and handle accordingly
    if (finalRun.status === 'requires_action') {
      // Handle function calls - see Function Execution document
      console.log('Run requires action (function calls)', {
        thread_id,
        run_id: run.id
      });
      
      // Return thread_id and run_id for function execution
      return {
        thread_id,
        run_id: run.id,
        status: 'requires_action',
        required_action: finalRun.required_action,
        processing_time_ms: Date.now() - startTime
      };
    } else if (finalRun.status === 'completed') {
      // Get assistant messages
      const messages = await withExponentialBackoff(
        () => openai.beta.threads.messages.list(thread_id),
        [],
        { timeoutMs: 60000 }
      );
      
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
      const content = latestMessage.content[0].text.value;
      
      return {
        thread_id,
        run_id: run.id,
        message_id: latestMessage.id,
        content,
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
    console.error('Error in OpenAI processing:', error);
    throw error;
  }
}
```

## 7. Coordinating with the SQS Heartbeat Pattern

While the OpenAI processing is running, the system needs to coordinate with the SQS heartbeat pattern to ensure the message remains invisible until processing completes. This is handled by the main Lambda function:

```javascript
// Excerpt from main Lambda handler
try {
  // Set up heartbeat timer
  const heartbeatInterval = setupHeartbeat(receiptHandle);
  
  // Initialize OpenAI client
  const openai = new OpenAI({
    apiKey: aiCredentials.ai_api_key
  });
  
  // Process with OpenAI
  // This can take several minutes, during which the heartbeat will extend the visibility timeout
  const aiResponse = await processWithOpenAI(openai, contextObject);
  
  // Cleanup and complete processing
  clearInterval(heartbeatInterval);
  
  return aiResponse;
} catch (error) {
  // Clean up heartbeat timer
  clearInterval(heartbeatInterval);
  
  // Log and rethrow error
  console.error('OpenAI processing error:', error);
  throw error;
}
```

## 8. Error Handling Considerations

The OpenAI integration implements several error handling strategies:

### 8.1 Error Categories

Errors are categorized to enable appropriate handling:

| Category | HTTP Status | Description | Handling |
|----------|-------------|-------------|----------|
| `timeout` | N/A | API call timeout | Retry with exponential backoff |
| `rate_limit` | 429 | Rate limit exceeded | Retry with exponential backoff |
| `authentication` | 401 | Invalid API key | Fail immediately, alert operations team |
| `authorization` | 403 | Permissions issue | Fail immediately, alert operations team |
| `not_found` | 404 | Resource not found | Fail immediately, log details |
| `invalid_request` | 400 | Bad request format | Fail immediately, log details |
| `server_error` | 5xx | OpenAI server error | Retry with exponential backoff |
| `network_error` | N/A | Network connectivity | Retry with exponential backoff |

### 8.2 Partial Success Handling

The system handles partial success scenarios:

- If thread creation succeeds but message creation fails, the thread ID is still returned
- If a run times out, the Lambda's heartbeat pattern ensures the SQS message remains invisible

## 9. Monitoring and Metrics

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

## 10. Thread Management and Cleanup

For the initial WhatsApp implementation, threads are created and retained indefinitely. In future versions, a thread cleanup mechanism may be implemented to handle:

1. Thread archiving after a period of inactivity
2. Thread deletion for completed conversations
3. Token usage optimization

## 11. Related Documentation

- [Overview and Architecture](./01-overview-architecture.md)
- [Function Execution](./06-function-execution.md)
- [Error Handling Strategy](./08-error-handling-strategy.md) 