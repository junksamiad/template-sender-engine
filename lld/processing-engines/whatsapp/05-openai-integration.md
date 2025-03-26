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

### 3.1 Adaptive Rate Limiting

In addition to exponential backoff, the system implements adaptive rate limiting based on the OpenAI API's response headers:

```javascript
/**
 * Adaptive rate limiting implementation
 * Uses token bucket algorithm with dynamic refill rate
 */
class AdaptiveRateLimiter {
  constructor(options = {}) {
    // Initialize with conservative defaults
    this.maxTokens = options.maxTokens || 60;  // Maximum tokens in bucket
    this.refillRate = options.refillRate || 1;  // Tokens per second
    this.tokens = this.maxTokens;  // Start with a full bucket
    this.lastRefill = Date.now();
    this.waitingQueue = [];  // Queue of pending operations
    
    // Track recent rate limit responses
    this.rateLimitEvents = [];
    this.adaptationWindow = options.adaptationWindow || 60000;  // 1 minute
  }
  
  /**
   * Adapts rate limits based on recent API responses
   * @param {object} headers - Response headers from OpenAI API
   */
  adaptToResponseHeaders(headers) {
    // Extract rate limit information from headers
    const remaining = parseInt(headers['x-ratelimit-remaining-requests'] || headers['x-ratelimit-remaining'], 10);
    const reset = parseInt(headers['x-ratelimit-reset-requests'] || headers['x-ratelimit-reset'], 10);
    
    if (!isNaN(remaining) && !isNaN(reset) && reset > 0) {
      // Calculate new refill rate based on reset time
      const newRefillRate = remaining / reset;
      
      // Record rate limit event
      this.rateLimitEvents.push({
        timestamp: Date.now(),
        remaining,
        reset,
        calculatedRate: newRefillRate
      });
      
      // Clean up old events
      this.rateLimitEvents = this.rateLimitEvents.filter(
        event => Date.now() - event.timestamp < this.adaptationWindow
      );
      
      // Adapt only if we have enough data points
      if (this.rateLimitEvents.length >= 3) {
        // Take the most conservative rate from recent events
        const rates = this.rateLimitEvents.map(event => event.calculatedRate);
        const minRate = Math.min(...rates);
        
        // Apply with a safety factor of 0.8
        this.refillRate = minRate * 0.8;
        
        console.log('Adapted rate limiter:', {
          new_refill_rate: this.refillRate,
          data_points: this.rateLimitEvents.length,
          min_rate: minRate
        });
      }
    }
  }
  
  /**
   * Refills the token bucket based on elapsed time
   */
  refill() {
    const now = Date.now();
    const elapsedSeconds = (now - this.lastRefill) / 1000;
    
    if (elapsedSeconds > 0) {
      // Add tokens based on refill rate and elapsed time
      this.tokens = Math.min(
        this.maxTokens,
        this.tokens + (elapsedSeconds * this.refillRate)
      );
      this.lastRefill = now;
    }
  }
  
  /**
   * Processes the queue of waiting operations
   */
  processQueue() {
    // Process queue if we have tokens and waiting operations
    if (this.tokens >= 1 && this.waitingQueue.length > 0) {
      const { resolve } = this.waitingQueue.shift();
      this.tokens -= 1;
      resolve();
      
      // Continue processing queue if possible
      if (this.tokens >= 1 && this.waitingQueue.length > 0) {
        setImmediate(() => this.processQueue());
      }
    }
  }
  
  /**
   * Acquires a token for an operation
   * @returns {Promise<void>} - Resolves when a token is available
   */
  async acquire() {
    this.refill();
    
    // If we have tokens available, consume one immediately
    if (this.tokens >= 1) {
      this.tokens -= 1;
      return;
    }
    
    // Otherwise, wait for a token to become available
    return new Promise(resolve => {
      this.waitingQueue.push({ resolve });
      
      // Calculate wait time based on refill rate
      const waitTime = (1 / this.refillRate) * 1000;
      
      // Set timer to check for token availability
      setTimeout(() => {
        this.refill();
        this.processQueue();
      }, waitTime);
    });
  }
}

// Global rate limiter instance
const openaiRateLimiter = new AdaptiveRateLimiter();

/**
 * Enhanced API call function with adaptive rate limiting
 * @param {Function} apiCallFn - API call function
 * @param {Array} args - Function arguments
 * @param {object} options - Options for retries and timeouts
 * @returns {Promise<any>} - API call result
 */
async function withRateLimitedExponentialBackoff(apiCallFn, args = [], options = {}) {
  // Wait for a token from the rate limiter
  await openaiRateLimiter.acquire();
  
  try {
    // Make the API call with exponential backoff
    const result = await withExponentialBackoff(apiCallFn, args, options);
    
    // Adapt rate limiter based on response headers
    if (result && result.headers) {
      openaiRateLimiter.adaptToResponseHeaders(result.headers);
    }
    
    return result;
  } catch (error) {
    // If we hit a rate limit, adapt the limiter
    if (error.status === 429 && error.headers) {
      openaiRateLimiter.adaptToResponseHeaders(error.headers);
    }
    
    throw error;
  }
}
```

This adaptive rate limiting system:

1. **Self-tunes** based on observed API response headers
2. **Prevents cascading failures** by limiting request rate
3. **Maximizes throughput** while staying within API limits
4. **Adjusts dynamically** as OpenAI's rate limits change
5. **Shares limits** across multiple concurrent executions

### 3.2 Usage Monitoring and Circuit Breaking

The system also implements circuit breaking to prevent overloading the OpenAI API during periods of high load or API degradation:

```javascript
/**
 * Circuit breaker implementation for OpenAI API
 */
class OpenAICircuitBreaker {
  constructor(options = {}) {
    this.failureThreshold = options.failureThreshold || 5;
    this.resetTimeout = options.resetTimeout || 30000;
    this.halfOpenTimeout = options.halfOpenTimeout || 5000;
    this.state = 'closed';  // closed, open, half-open
    this.failures = 0;
    this.lastFailure = null;
    this.halfOpenTimer = null;
  }
  
  /**
   * Records a successful API call
   */
  recordSuccess() {
    if (this.state === 'half-open') {
      // If successful during half-open state, close the circuit
      this.state = 'closed';
      this.failures = 0;
      console.log('Circuit breaker state changed to closed after successful half-open call');
    } else if (this.state === 'closed') {
      // In closed state, reset failure count on success
      this.failures = 0;
    }
  }
  
  /**
   * Records a failed API call
   * @param {Error} error - The error that occurred
   */
  recordFailure(error) {
    // Only count certain types of failures
    if (error.status === 429 || error.status >= 500) {
      this.failures++;
      this.lastFailure = Date.now();
      
      // If we exceed the threshold, open the circuit
      if (this.state === 'closed' && this.failures >= this.failureThreshold) {
        this.state = 'open';
        console.log('Circuit breaker opened due to multiple failures', {
          failure_count: this.failures,
          failure_threshold: this.failureThreshold
        });
        
        // Schedule half-open state
        this.halfOpenTimer = setTimeout(() => {
          if (this.state === 'open') {
            this.state = 'half-open';
            console.log('Circuit breaker state changed to half-open');
          }
        }, this.resetTimeout);
      }
    }
  }
  
  /**
   * Checks if the circuit is open
   * @returns {boolean} - True if circuit is open
   */
  isOpen() {
    // If we're in open state but enough time has passed, try half-open
    if (this.state === 'open' && 
        this.lastFailure && 
        Date.now() - this.lastFailure > this.resetTimeout) {
      this.state = 'half-open';
      console.log('Circuit breaker state changed to half-open after timeout');
    }
    
    return this.state === 'open';
  }
  
  /**
   * Executes a function with circuit breaker protection
   * @param {Function} fn - Function to execute
   * @param {Array} args - Function arguments
   * @returns {Promise<any>} - Function result
   */
  async execute(fn, args = []) {
    // If circuit is open, fail fast
    if (this.isOpen()) {
      throw new Error('Circuit breaker is open, request rejected');
    }
    
    // Allow only one request in half-open state
    if (this.state === 'half-open') {
      console.log('Test request in half-open state');
    }
    
    try {
      const result = await fn(...args);
      this.recordSuccess();
      return result;
    } catch (error) {
      this.recordFailure(error);
      throw error;
    }
  }
}

// Global circuit breaker instance
const openaiCircuitBreaker = new OpenAICircuitBreaker();

/**
 * Complete API call function with rate limiting, circuit breaking, and retry logic
 * @param {Function} apiCallFn - API call function
 * @param {Array} args - Function arguments
 * @param {object} options - Options for retries and timeouts
 * @returns {Promise<any>} - API call result
 */
async function protectedOpenAICall(apiCallFn, args = [], options = {}) {
  // Use circuit breaker to prevent cascading failures
  return openaiCircuitBreaker.execute(
    async () => withRateLimitedExponentialBackoff(apiCallFn, args, options),
    []
  );
}
```

This comprehensive approach to OpenAI API resilience provides:

1. **Graceful degradation** during API instability
2. **Fast failure** when the API is known to be unavailable
3. **Automatic recovery** when the API service improves
4. **Detailed metrics** for monitoring system health
5. **Adaptive behavior** that responds to changing conditions

## 4. Message Processing and Context Updates

The OpenAI integration adds several key pieces of data to the context object during processing:

1. **Thread ID**: After creating an OpenAI thread
```javascript
contextObject.conversation_data.thread_id = thread.id;
```

2. **Content Variables**: Generated by the OpenAI assistant for template use
```javascript
contextObject.conversation_data.content_variables = {
    "1": "John",
    "2": "Healthcare Assistant",
    "3": "your driving licence status and the gap in your work experience..."
};
```

3. **Message Object**: Created during OpenAI processing with metrics
```javascript
contextObject.conversation_data.message = {
    entry_id: "msg_67890abcdef12345...",
    ai_prompt_tokens: 2345,
    ai_completion_tokens: 156,
    ai_total_tokens: 2501,
    processing_time_ms: 4267
};
```

After the Twilio message is sent successfully, the message object is completed with:
```javascript
contextObject.conversation_data.message.message_timestamp = "2023-06-15T14:31:12.456Z";
contextObject.conversation_data.message.role = "assistant";
contextObject.conversation_data.message.content = "Template message sent with SID: SM1234567890abcdef...";
```

This completed message will be stored in the DynamoDB conversation record's messages array during the final update.

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
    const run = await withRateLimitedExponentialBackoff(
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
    let run = await withRateLimitedExponentialBackoff(
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
      run = await withRateLimitedExponentialBackoff(
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
    const messages = await withRateLimitedExponentialBackoff(
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
    contextObject.conversation_data.thread_id = thread_id;
    
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
      
      // Get token usage from the run
      const aiPromptTokens = finalRun.usage?.prompt_tokens || 0;
      const aiCompletionTokens = finalRun.usage?.completion_tokens || 0;
      const aiTotalTokens = finalRun.usage?.total_tokens || 0;
      
      // Store content_variables only in the conversation_data object
      contextObject.conversation_data.content_variables = contentVariables;
      
      // Initialize conversation_data.messages array if it doesn't exist
      if (!contextObject.conversation_data.messages) {
        contextObject.conversation_data.messages = [];
      }
      
      // Create a new message object in the messages array
      // This will be the first message in the conversation, with role='assistant'
      // Note: content will be added after the template is sent via Twilio
      const assistantMessage = {
        entry_id: uuidv4(), // Generate a unique ID for the message
        message_timestamp: new Date().toISOString(),
        role: 'assistant',
        ai_prompt_tokens: aiPromptTokens,
        ai_completion_tokens: aiCompletionTokens,
        ai_total_tokens: aiTotalTokens,
        processing_time_ms: processingTimeMs
        // content field will be added after Twilio sends the template
      };
      
      // Store this assistant message for later completion
      contextObject.conversation_data.pending_assistant_message = assistantMessage;
      
      console.log('Run completed successfully', {
        thread_id,
        run_id: run.id,
        processing_time_ms: processingTimeMs,
        variable_count: Object.keys(contentVariables).length,
        ai_prompt_tokens: aiPromptTokens,
        ai_completion_tokens: aiCompletionTokens,
        ai_total_tokens: aiTotalTokens
      });
      
      // Return updated context object and processing results
      return {
        thread_id,
        run_id: run.id,
        status: 'completed',
        content_variables: contentVariables,
        processing_time_ms: processingTimeMs,
        usage: {
          prompt_tokens: aiPromptTokens,
          completion_tokens: aiCompletionTokens,
          total_tokens: aiTotalTokens
        }
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
    
    // Complete the pending assistant message with the template content
    const completeAssistantMessage = {
      ...contextObject.conversation_data.pending_assistant_message,
      content: `Template: ${templateName}`
    };
    
    // Add the complete message to conversation history
    await addMessageToConversation(conversation, completeAssistantMessage);
    
    // Prepare the final conversation update data
    const finalUpdateData = {
      conversation_status: 'initial_message_sent',
      thread_id: contextObject.thread_id,
      processing_time_ms: completeAssistantMessage.processing_time_ms,
      task_complete: true,
      ai_prompt_tokens: completeAssistantMessage.ai_prompt_tokens,
      ai_completion_tokens: completeAssistantMessage.ai_completion_tokens,
      ai_total_tokens: completeAssistantMessage.ai_total_tokens
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
    // This will:
    // 1. Create an OpenAI thread and store thread_id in contextObject.conversation_data
    // 2. Run the OpenAI assistant to generate content variables
    // 3. Store content_variables in contextObject.conversation_data
    // 4. Create message object with metrics in contextObject.conversation_data.message
    const openAIResult = await processWithOpenAI(openai, contextObject);
    
    // Send WhatsApp template message with content variables
    // This will:
    // 1. Send the template message using Twilio API
    // 2. Complete the message object by adding timestamp, role, and content
    // 3. Update the conversation record in DynamoDB with the completed message
    const messageResult = await sendWhatsAppTemplateMessage(
      contextObject, 
      contextObject.conversation_data.content_variables
    );
    
    // Return success result with key metrics
    return {
      success: true,
      thread_id: contextObject.conversation_data.thread_id,
      sent_at: messageResult.sent_at,
      processing_time_ms: contextObject.conversation_data.message.processing_time_ms,
      ai_total_tokens: contextObject.conversation_data.message.ai_total_tokens
    };
  } catch (error) {
    console.error('Error processing WhatsApp message:', error);
    throw error;
  }
}

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

/**
 * Adds a message to the conversation record's messages array
 * @param {object} conversation - The conversation record from DynamoDB
 * @param {object} messageData - Message data including metrics and content
 * @returns {Promise<object>} - The updated conversation record
 */
async function addMessageToConversation(conversation, messageData) {
  try {
    console.log('Adding message to conversation history', {
      conversation_id: conversation.conversation_id,
      message_role: messageData.role,
      entry_id: messageData.entry_id
    });
    
    const now = new Date().toISOString();
    
    // Prepare the message entry with all required fields
    const messageEntry = {
      entry_id: messageData.entry_id,
      message_timestamp: messageData.message_timestamp || now,
      role: messageData.role,
      content: messageData.content,
      ai_prompt_tokens: messageData.ai_prompt_tokens || 0,
      ai_completion_tokens: messageData.ai_completion_tokens || 0,
      ai_total_tokens: messageData.ai_total_tokens || 0,
      processing_time_ms: messageData.processing_time_ms || 0
    };
    
    // Update the conversation record in DynamoDB
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
    
    console.log('Message added to conversation', {
      conversation_id: conversation.conversation_id,
      message_role: messageEntry.role,
      entry_id: messageEntry.entry_id
    });
    
    return {
      ...conversation,
      messages: [...(conversation.messages || []), messageEntry],
      updated_at: now
    };
  } catch (error) {
    console.error('Error adding message to conversation', error);
    throw error;
  }
}

/**
 * Retrieves a conversation record from DynamoDB
 * @param {string} recipientTel - The recipient's phone number (partition key)
 * @param {string} conversationId - The conversation ID (sort key)
 * @returns {Promise<object>} - The conversation record
 */
async function getConversationRecord(recipientTel, conversationId) {
  try {
    console.log('Retrieving conversation record', {
      recipient_tel: recipientTel,
      conversation_id: conversationId
    });
    
    const result = await dynamoDB.get({
      TableName: process.env.CONVERSATION_TABLE_NAME,
      Key: {
        recipient_tel: recipientTel,
        conversation_id: conversationId
      }
    }).promise();
    
    if (!result.Item) {
      throw new Error(`Conversation not found: ${conversationId}`);
    }
    
    console.log('Retrieved conversation record', {
      conversation_id: conversationId,
      status: result.Item.conversation_status
    });
    
    return result.Item;
  } catch (error) {
    console.error('Error retrieving conversation record', error);
    throw error;
  }
}