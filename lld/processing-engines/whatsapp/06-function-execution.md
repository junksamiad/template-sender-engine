# WhatsApp Processing Engine - Function Execution

> **Part 6 of 10 in the WhatsApp Processing Engine documentation series**

## 1. Introduction

This document details how the WhatsApp Processing Engine handles OpenAI Assistant function calls. The system defines a set of executable functions that the OpenAI Assistant can call to perform specific actions, such as generating WhatsApp templates, sending messages, and accessing contextual information.

## 2. Function Architecture

The function execution system follows these principles:

1. **Declarative Definition**: Functions are defined declaratively with input/output schemas
2. **Controlled Execution**: Only permitted functions can be executed by the OpenAI Assistant
3. **Strong Validation**: Input and output are validated against JSON schemas
4. **Error Resilience**: Comprehensive error handling for function failures
5. **Asynchronous Integration**: Functions can make API calls to external systems

Function calls are handled asynchronously as part of the OpenAI run lifecycle, with the engine managing their execution and submitting results back to the API.

## 3. Function Definition Structure

Each function is defined with a schema that matches the OpenAI Assistants API requirements:

```javascript
/**
 * Template for function definition
 */
const functionTemplate = {
  name: "function_name",
  description: "Description of what the function does and when it should be used",
  parameters: {
    type: "object",
    properties: {
      // Function parameter definitions
      param1: {
        type: "string",
        description: "Description of parameter 1"
      },
      param2: {
        type: "integer",
        description: "Description of parameter 2"
      }
    },
    required: ["param1"]
  }
};
```

## 4. Available Functions

The WhatsApp Processing Engine provides the following functions to the OpenAI Assistant:

### 4.1 Generate WhatsApp Template (`generateWhatsAppTemplate`)

This function creates a WhatsApp template based on input parameters, returning a structured template object:

```javascript
const generateWhatsAppTemplateFunction = {
  name: "generateWhatsAppTemplate",
  description: "Generates a WhatsApp template based on provided parameters",
  parameters: {
    type: "object",
    properties: {
      templateName: {
        type: "string",
        description: "Name for the template (alphanumeric with underscores only)"
      },
      category: {
        type: "string",
        enum: ["MARKETING", "UTILITY", "AUTHENTICATION"],
        description: "Category of the template"
      },
      language: {
        type: "string",
        description: "Language code for the template (e.g., 'en_US')"
      },
      components: {
        type: "array",
        description: "Components of the template (header, body, footer, buttons)",
        items: {
          type: "object",
          properties: {
            type: {
              type: "string",
              enum: ["HEADER", "BODY", "FOOTER", "BUTTONS"],
              description: "Type of component"
            },
            format: {
              type: "string",
              enum: ["TEXT", "IMAGE", "DOCUMENT", "VIDEO"],
              description: "Format of the component content"
            },
            text: {
              type: "string",
              description: "Text content for the component"
            },
            buttons: {
              type: "array",
              description: "Button definitions (for BUTTONS type only)",
              items: {
                type: "object",
                properties: {
                  type: {
                    type: "string",
                    enum: ["QUICK_REPLY", "URL"],
                    description: "Type of button"
                  },
                  text: {
                    type: "string",
                    description: "Button text"
                  },
                  url: {
                    type: "string",
                    description: "URL for URL type buttons"
                  }
                },
                required: ["type", "text"]
              }
            }
          },
          required: ["type"]
        }
      }
    },
    required: ["templateName", "category", "language", "components"]
  }
};
```

### 4.2 Send WhatsApp Message (`sendWhatsAppMessage`)

This function sends a message via WhatsApp using the Twilio API:

```javascript
const sendWhatsAppMessageFunction = {
  name: "sendWhatsAppMessage",
  description: "Sends a WhatsApp message using a template or free-form text",
  parameters: {
    type: "object",
    properties: {
      useTemplate: {
        type: "boolean",
        description: "Whether to use a template (true) or free-form text (false)"
      },
      templateName: {
        type: "string",
        description: "Name of the template to use (required if useTemplate is true)"
      },
      templateLanguage: {
        type: "string",
        description: "Language code for the template (e.g., 'en_US')"
      },
      templateVariables: {
        type: "object",
        description: "Variables to substitute in the template",
        additionalProperties: true
      },
      messageText: {
        type: "string",
        description: "Free-form message text (required if useTemplate is false)"
      }
    },
    required: ["useTemplate"]
  }
};
```

### 4.3 Get Conversation Details (`getConversationDetails`)

This function retrieves details about the current conversation:

```javascript
const getConversationDetailsFunction = {
  name: "getConversationDetails",
  description: "Retrieves detailed information about the current conversation",
  parameters: {
    type: "object",
    properties: {
      includeMessageHistory: {
        type: "boolean",
        description: "Whether to include message history in the response"
      }
    }
  }
};
```

## 5. Function Execution Flow

The function execution flow is handled in several stages:

### 5.1 Function Call Handler

When an OpenAI run requires action, the function calls are processed:

```javascript
/**
 * Handles function calls required by an OpenAI run
 * @param {object} openai - Initialized OpenAI client
 * @param {string} threadId - OpenAI thread ID
 * @param {string} runId - OpenAI run ID
 * @param {object} requiredAction - The required action object from the run
 * @returns {Promise<object>} - Result of the function execution
 */
async function handleFunctionCalls(openai, threadId, runId, requiredAction) {
  try {
    console.log('Handling function calls', {
      thread_id: threadId,
      run_id: runId,
      tool_calls_count: requiredAction.submit_tool_outputs.tool_calls.length
    });
    
    const toolCalls = requiredAction.submit_tool_outputs.tool_calls;
    const toolOutputs = [];
    
    // Process each tool call
    for (const toolCall of toolCalls) {
      const { id, function: functionCall } = toolCall;
      const { name, arguments: argsString } = functionCall;
      
      console.log('Processing function call', {
        function_name: name,
        tool_call_id: id
      });
      
      try {
        // Parse function arguments
        const args = JSON.parse(argsString);
        
        // Execute the function
        const result = await executeFunctionByName(name, args);
        
        // Add to tool outputs
        toolOutputs.push({
          tool_call_id: id,
          output: JSON.stringify(result)
        });
        
        console.log('Function executed successfully', {
          function_name: name,
          tool_call_id: id
        });
      } catch (functionError) {
        console.error('Error executing function', {
          function_name: name,
          tool_call_id: id,
          error: functionError.message
        });
        
        // Add error result to tool outputs
        toolOutputs.push({
          tool_call_id: id,
          output: JSON.stringify({ error: functionError.message })
        });
      }
    }
    
    // Submit tool outputs back to OpenAI
    await withExponentialBackoff(
      () => openai.beta.threads.runs.submitToolOutputs(threadId, runId, {
        tool_outputs: toolOutputs
      }),
      [],
      { timeoutMs: 60000 }
    );
    
    console.log('Submitted tool outputs to OpenAI', {
      thread_id: threadId,
      run_id: runId,
      tool_outputs_count: toolOutputs.length
    });
    
    // Continue polling the run until it completes
    return await pollRunStatus(openai, threadId, runId);
  } catch (error) {
    console.error('Error handling function calls', error);
    throw error;
  }
}
```

### 5.2 Function Execution

The `executeFunctionByName` function dispatches the function call to the appropriate handler:

```javascript
/**
 * Executes a function by name with the provided arguments
 * @param {string} functionName - Name of the function to execute
 * @param {object} args - Arguments for the function
 * @returns {Promise<any>} - Result of the function execution
 */
async function executeFunctionByName(functionName, args) {
  // Validate function name
  const validFunctions = {
    generateWhatsAppTemplate,
    sendWhatsAppMessage,
    getConversationDetails
  };
  
  if (!validFunctions[functionName]) {
    throw new Error(`Unknown function: ${functionName}`);
  }
  
  // Execute the function
  return await validFunctions[functionName](args);
}
```

## 6. Individual Function Implementations

### 6.1 Generate WhatsApp Template

```javascript
/**
 * Generates a WhatsApp template
 * @param {object} args - Function arguments
 * @returns {Promise<object>} - Generated template object
 */
async function generateWhatsAppTemplate(args) {
  try {
    const { templateName, category, language, components } = args;
    
    // Validate template name (alphanumeric with underscores only)
    if (!/^[a-zA-Z0-9_]+$/.test(templateName)) {
      throw new Error('Template name must contain only letters, numbers, and underscores');
    }
    
    // Process components
    const processedComponents = [];
    let hasBodyComponent = false;
    
    for (const component of components) {
      // Body component is required
      if (component.type === 'BODY') {
        hasBodyComponent = true;
      }
      
      // Process based on component type
      switch (component.type) {
        case 'HEADER':
          // Only one header allowed
          if (processedComponents.some(c => c.type === 'HEADER')) {
            throw new Error('Only one HEADER component is allowed');
          }
          
          // Add format-specific validation here
          break;
          
        case 'BODY':
          // Only one body allowed
          if (processedComponents.some(c => c.type === 'BODY')) {
            throw new Error('Only one BODY component is allowed');
          }
          
          // Ensure body has text
          if (!component.text) {
            throw new Error('BODY component must have text content');
          }
          
          // Validate variable format if present
          if (component.text.includes('{{')) {
            const variableMatches = component.text.match(/{{[1-9][0-9]?}}/g);
            if (variableMatches) {
              const variables = new Set(variableMatches);
              
              // Variables must be consecutive
              for (let i = 1; i <= variables.size; i++) {
                if (!variables.has(`{{${i}}}`)) {
                  throw new Error(`Template variables must be consecutive: missing {{${i}}}`);
                }
              }
            }
          }
          break;
          
        case 'FOOTER':
          // Only one footer allowed
          if (processedComponents.some(c => c.type === 'FOOTER')) {
            throw new Error('Only one FOOTER component is allowed');
          }
          break;
          
        case 'BUTTONS':
          // Only one buttons component allowed
          if (processedComponents.some(c => c.type === 'BUTTONS')) {
            throw new Error('Only one BUTTONS component is allowed');
          }
          
          // Validate buttons
          if (!component.buttons || !Array.isArray(component.buttons)) {
            throw new Error('BUTTONS component must have a buttons array');
          }
          
          if (component.buttons.length > 3) {
            throw new Error('Maximum of 3 buttons allowed');
          }
          
          // Validate each button
          component.buttons.forEach(button => {
            if (!button.type) {
              throw new Error('Each button must have a type');
            }
            
            if (!button.text) {
              throw new Error('Each button must have text');
            }
            
            if (button.type === 'URL' && !button.url) {
              throw new Error('URL buttons must have a url property');
            }
          });
          break;
          
        default:
          throw new Error(`Unknown component type: ${component.type}`);
      }
      
      processedComponents.push(component);
    }
    
    // Ensure body component exists
    if (!hasBodyComponent) {
      throw new Error('Template must have a BODY component');
    }
    
    // Create template object
    const template = {
      name: templateName,
      category,
      language,
      components: processedComponents,
      status: 'PENDING',
      created_at: new Date().toISOString()
    };
    
    return {
      template,
      message: 'Template generated successfully. Ready to be submitted to WhatsApp.'
    };
  } catch (error) {
    console.error('Error generating WhatsApp template:', error);
    throw error;
  }
}
```

### 6.2 Send WhatsApp Message

```javascript
/**
 * Sends a WhatsApp message
 * @param {object} args - Function arguments
 * @returns {Promise<object>} - Message sending result
 */
async function sendWhatsAppMessage(args) {
  try {
    const { useTemplate, templateName, templateLanguage, templateVariables, messageText } = args;
    
    // Get Twilio credentials from the context
    const twilioCredentials = await getCredentials(
      'whatsapp/twilio',
      contextObject.company_id,
      contextObject.project_id
    );
    
    // Initialize Twilio client
    const twilioClient = twilio(
      twilioCredentials.twilio_account_sid,
      twilioCredentials.twilio_auth_token
    );
    
    let messageOptions;
    
    if (useTemplate) {
      // Validate template parameters
      if (!templateName) {
        throw new Error('templateName is required when useTemplate is true');
      }
      
      if (!templateLanguage) {
        throw new Error('templateLanguage is required when useTemplate is true');
      }
      
      // Create template message options
      messageOptions = {
        from: `whatsapp:${contextObject.company_whatsapp_number}`,
        to: `whatsapp:${contextObject.recipient_tel}`,
        contentSid: null, // Will be determined by template name
        contentVariables: JSON.stringify(templateVariables || {})
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
    } else {
      // Validate free-form message
      if (!messageText) {
        throw new Error('messageText is required when useTemplate is false');
      }
      
      // Create free-form message options
      messageOptions = {
        from: `whatsapp:${contextObject.company_whatsapp_number}`,
        to: `whatsapp:${contextObject.recipient_tel}`,
        body: messageText
      };
    }
    
    // Send the message
    const message = await twilioClient.messages.create(messageOptions);
    
    // Add message to conversation history
    await addMessageToConversation(
      contextObject.conversation_data,
      'assistant',
      useTemplate ? `Template: ${templateName}` : messageText
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
    console.error('Error sending WhatsApp message:', error);
    throw error;
  }
}
```

### 6.3 Get Conversation Details

```javascript
/**
 * Gets details about the current conversation
 * @param {object} args - Function arguments
 * @returns {Promise<object>} - Conversation details
 */
async function getConversationDetails(args) {
  try {
    const { includeMessageHistory = false } = args || {};
    
    // Get conversation data
    const conversationData = contextObject.conversation_data;
    
    // Create basic response
    const response = {
      conversation_id: conversationData.conversation_id,
      company_id: conversationData.company_id,
      project_id: conversationData.project_id,
      recipient_tel: conversationData.recipient_tel,
      company_whatsapp_number: conversationData.company_whatsapp_number,
      status: conversationData.conversation_status,
      created_at: conversationData.created_at,
      updated_at: conversationData.updated_at
    };
    
    // Add message history if requested
    if (includeMessageHistory && conversationData.messages) {
      response.messages = conversationData.messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.message_timestamp
      }));
    }
    
    return response;
  } catch (error) {
    console.error('Error getting conversation details:', error);
    throw error;
  }
}
```

## 7. Error Handling in Function Execution

Function execution includes robust error handling at multiple levels:

### 7.1 Function-Level Error Handling

Each function implementation includes try-catch blocks to handle function-specific errors.

### 7.2 Execution-Level Error Handling

The function execution wrapper catches and processes all errors, returning them in a structured format:

```javascript
try {
  // Function execution
  const result = await functionImplementation(args);
  return result;
} catch (error) {
  console.error(`Error executing ${functionName}:`, error);
  
  // Return structured error response
  return {
    error: true,
    message: error.message,
    code: error.code || 'EXECUTION_ERROR'
  };
}
```

### 7.3 Error Reporting to OpenAI

Errors from function execution are reported back to OpenAI as outputs, allowing the AI to handle the errors gracefully:

```javascript
toolOutputs.push({
  tool_call_id: id,
  output: JSON.stringify({ 
    error: true,
    message: error.message
  })
});
```

## 8. Function Security Considerations

The function execution system follows these security principles:

1. **Input Validation**: All function inputs are validated against schemas
2. **Controlled Access**: Only predefined functions are executable
3. **Credential Protection**: Credentials are never exposed to the AI
4. **Error Sanitization**: Errors are sanitized to avoid leaking sensitive information
5. **Audit Logging**: All function calls are logged for audit purposes

## 9. Monitoring and Debugging

The function execution system includes detailed logging for monitoring and debugging:

```javascript
// Log function call
console.log('Function call', {
  function_name: functionName,
  args: JSON.stringify(sanitizedArgs),
  timestamp: new Date().toISOString(),
  conversation_id: contextObject.conversation_data.conversation_id
});

// Log function result
console.log('Function result', {
  function_name: functionName,
  result: JSON.stringify(sanitizedResult),
  execution_time_ms: Date.now() - startTime,
  conversation_id: contextObject.conversation_data.conversation_id
});
```

## 10. Related Documentation

- [Overview and Architecture](./01-overview-architecture.md)
- [OpenAI Integration](./05-openai-integration.md)
- [Template Management and Message Sending](./07-template-management.md) 