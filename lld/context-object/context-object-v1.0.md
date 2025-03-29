# Context Object Structure

This document describes the structure of the context object created by the Channel Router and passed to the channel-specific queues for processing.

## Purpose

The context object serves as a comprehensive package containing:
1. The original request payload from the frontend
2. Company and project configuration from the DynamoDB database
3. Channel-specific configuration and credentials
4. AI service configuration and credentials
5. Metadata for tracking and debugging
6. Conversation reference data for downstream processing

This approach eliminates the need for downstream services to query the database again, providing all necessary information in one place.

## Structure

The context object has the following structure:

```json
{
  "frontend_payload": {
    "company_data": {
      "company_id": "cucumber-recruitment",
      "project_id": "cv-analysis"
    },
    "recipient_data": {
      "recipient_first_name": "John",
      "recipient_last_name": "Doe",
      "recipient_tel": "+447700900123",
      "recipient_email": "john.doe@example.com",
      "comms_consent": true
    },
    "project_data": {
      "job_title": "Software Engineer",
      "job_description": "We are looking for a skilled software engineer...",
      "application_deadline": "2023-07-30T23:59:59Z"
    },
    "request_data": {
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "channel_method": "whatsapp",
      "initial_request_timestamp": "2023-06-15T14:30:45.123Z"
    }
  },
  "wa_company_data_payload": {
    "company_name": "Cucumber Recruitment Ltd",
    "project_name": "CV Analysis Bot",
    "project_status": "active",
    "allowed_channels": ["whatsapp", "email"],
    "company_rep": {
      "company_rep_1": "Carol",
      "company_rep_2": "Mark",
      "company_rep_3": null,
      "company_rep_4": null,
      "company_rep_5": null
    }
  },
  "project_rate_limits": {
    "requests_per_minute": 100,
    "requests_per_day": 10000,
    "concurrent_conversations": 50,
    "max_message_length": 4096
  },
  "channel_config": {
    "whatsapp": {
      "whatsapp_credentials_id": "whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio",
      "company_whatsapp_number": "+14155238886"
    },
    "sms": {
      "sms_credentials_id": "sms-credentials/cucumber-recruitment/cv-analysis/twilio",
      "company_sms_number": "+14155238887"
    },
    "email": {
      "email_credentials_id": "email-credentials/cucumber-recruitment/cv-analysis/sendgrid",
      "company_email": "jobs@cucumber-recruitment.com"
    }
  },
  "ai_config": {
    "assistant_id_template_sender": "asst_Ds59ylP35Pn84pasJQVglC2Q",
    "assistant_id_replies": "asst_Ds59ylP35Pn84pesJQVglC2Q",
    "assistant_id_3": "",
    "assistant_id_4": "",
    "assistant_id_5": "",
    "ai_api_key_reference": "ai-api-key/global"
  },
  "conversation_data": {
    "conversation_id": "cucumber-recruitment#cv-analysis#550e8400-e29b-41d4-a716-446655440000#14155238886",
    "thread_id": "thread_abc123def456",
    "content_variables": {
      "1": "John",
      "2": "Software Engineer",
      "3": "your experience with cloud technologies"
    },
    "message": {
      "entry_id": "msg_67890abcdef12345...",
      "message_timestamp": "2023-06-15T14:31:12.456Z",
      "role": "assistant",
      "content": "Template message sent with SID: SM1234567890abcdef...",
      "ai_prompt_tokens": 2345,
      "ai_completion_tokens": 156,
      "ai_total_tokens": 2501,
      "processing_time_ms": 4267
    }
  },
  "metadata": {
    "router_version": "1.0.0"
  }
}
```

## Field Descriptions

### frontend_payload

Contains the complete, unmodified payload as received from the frontend application:

| Field | Description |
|-------|-------------|
| company_data | Company and project identifiers |
| recipient_data | Information about the message recipient |
| project_data | Project-specific data that varies by use case |
| request_data | Request metadata including ID, channel, and timestamp |

### wa_company_data_payload

Contains essential company and project information retrieved from the DynamoDB database:

| Field | Description |
|-------|-------------|
| company_name | Human-readable company name |
| project_name | Human-readable project name |
| project_status | Current status of the project (active, inactive, etc.) |
| allowed_channels | List of communication channels this project can use |
| company_rep | Company representative information |

### project_rate_limits

Contains rate limiting configuration for the company/project:

| Field | Description |
|-------|-------------|
| requests_per_minute | Maximum number of requests allowed per minute |
| requests_per_day | Maximum number of requests allowed per day |
| concurrent_conversations | Maximum number of concurrent conversations allowed |
| max_message_length | Maximum length of messages in characters |

### channel_config

Contains channel-specific configuration based on the requested channel method:

```json
{
  "whatsapp": {
    "whatsapp_credentials_id": "whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio",
    "company_whatsapp_number": "+14155238886"
  },
  "sms": {
    "sms_credentials_id": "sms-credentials/cucumber-recruitment/cv-analysis/twilio",
    "company_sms_number": "+14155238887"
  },
  "email": {
    "email_credentials_id": "email-credentials/cucumber-recruitment/cv-analysis/sendgrid",
    "company_email": "jobs@cucumber-recruitment.com"
  }
}
```

| Channel | Field | Description |
|---------|-------|-------------|
| whatsapp | `whatsapp_credentials_id` | Reference to WhatsApp (Twilio) credentials in Secrets Manager using format: whatsapp-credentials/{company_id}/{project_id}/twilio |
| whatsapp | `company_whatsapp_number` | The WhatsApp phone number assigned to this company/project |
| sms | `sms_credentials_id` | Reference to SMS (Twilio) credentials in Secrets Manager using format: sms-credentials/{company_id}/{project_id}/twilio |
| sms | `company_sms_number` | The SMS phone number assigned to this company/project |
| email | `email_credentials_id` | Reference to Email (SendGrid) credentials in Secrets Manager using format: email-credentials/{company_id}/{project_id}/sendgrid |
| email | `company_email` | The email address assigned to this company/project |

### ai_config

Contains AI service configuration for OpenAI:

| Field | Description |
|-------|-------------|
| assistant_id_template_sender | OpenAI Assistant ID for sending initial templates |
| assistant_id_replies | OpenAI Assistant ID for handling replies |
| assistant_id_3 | Additional OpenAI Assistant ID (optional) |
| assistant_id_4 | Additional OpenAI Assistant ID (optional) |
| assistant_id_5 | Additional OpenAI Assistant ID (optional) |
| ai_api_key_reference | Reference to the AI API key in Secrets Manager that is used across all channels |

### conversation_data

Contains reference data for the conversation record created in DynamoDB:

| Field | Description |
|-------|-------------|
| conversation_id | The unique identifier for the conversation in DynamoDB |
| thread_id | The OpenAI thread ID for this conversation (added during OpenAI processing) |
| content_variables | Object containing template variables generated by OpenAI |
| message | Object containing the current message being processed |

The `message` object structure:
```json
{
  "entry_id": "msg_67890abcdef12345...",  // Generated UUID
  "message_timestamp": "2023-06-15T14:31:12.456Z",  // When Twilio confirmed sending
  "role": "assistant",  // Message role (assistant for template messages)
  "content": "Template message sent with SID: SM1234567890abcdef...",  // Message content
  "ai_prompt_tokens": 2345,  // Token usage from OpenAI
  "ai_completion_tokens": 156,  // Token usage from OpenAI
  "ai_total_tokens": 2501,  // Total token usage
  "processing_time_ms": 4267  // Total processing time for this message
}
```

Example of complete conversation_data structure:
```json
"conversation_data": {
  "conversation_id": "cucumber-recruitment#cv-analysis#550e8400-e29b-41d4-a716-446655440000#14155238886",
  "thread_id": "thread_abc123def456",
  "content_variables": {
    "1": "John",
    "2": "Software Engineer",
    "3": "your experience with cloud technologies"
  },
  "message": {
    "entry_id": "msg_67890abcdef12345...",
    "message_timestamp": "2023-06-15T14:31:12.456Z",
    "role": "assistant",
    "content": "Template message sent with SID: SM1234567890abcdef...",
    "ai_prompt_tokens": 2345,
    "ai_completion_tokens": 156,
    "ai_total_tokens": 2501,
    "processing_time_ms": 4267
  }
}
```

> **Note**: The `conversation_data` section evolves during processing:
> 1. Initially contains only `conversation_id` when created by Channel Router
> 2. `thread_id` is added after OpenAI thread creation
> 3. `content_variables` are added after OpenAI processing
> 4. `message` object is built up during processing and completed after Twilio sends the message

### metadata

Contains metadata about the context object itself:

| Field | Description |
|-------|-------------|
| `router_version` | Version of the Channel Router that created the context |

## Channel-Specific Examples

### WhatsApp Channel Example

```json
{
  "frontend_payload": {
    "company_data": {
      "company_id": "cucumber-recruitment",
      "project_id": "cv-analysis"
    },
    "recipient_data": {
      "recipient_first_name": "John",
      "recipient_last_name": "Doe",
      "recipient_tel": "+447700900123",
      "recipient_email": "john.doe@example.com",
      "comms_consent": true
    },
    "project_data": {
      "job_title": "Software Engineer",
      "job_description": "We are looking for a skilled software engineer...",
      "application_deadline": "2023-07-30T23:59:59Z"
    },
    "request_data": {
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "channel_method": "whatsapp",
      "initial_request_timestamp": "2023-06-15T14:30:45.123Z"
    }
  },
  "wa_company_data_payload": {
    "company_name": "Cucumber Recruitment Ltd",
    "project_name": "CV Analysis Bot",
    "project_status": "active",
    "allowed_channels": ["whatsapp", "email"],
    "company_rep": {
      "company_rep_1": "Carol",
      "company_rep_2": "Mark",
      "company_rep_3": null,
      "company_rep_4": null,
      "company_rep_5": null
    }
  },
  "project_rate_limits": {
    "requests_per_minute": 100,
    "requests_per_day": 10000,
    "concurrent_conversations": 50,
    "max_message_length": 4096
  },
  "channel_config": {
    "whatsapp": {
      "whatsapp_credentials_id": "whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio",
      "company_whatsapp_number": "+14155238886"
    }
  },
  "ai_config": {
    "assistant_id_template_sender": "asst_Ds59ylP35Pn84pasJQVglC2Q",
    "assistant_id_replies": "asst_Ds59ylP35Pn84pesJQVglC2Q",
    "assistant_id_3": "",
    "assistant_id_4": "",
    "assistant_id_5": "",
    "ai_api_key_reference": "ai-api-key/global"
  },
  "conversation_data": {
    "conversation_id": "cucumber-recruitment#cv-analysis#550e8400-e29b-41d4-a716-446655440000#14155238886",
    "thread_id": "thread_abc123def456",
    "content_variables": {
      "1": "John",
      "2": "Software Engineer",
      "3": "your experience with cloud technologies"
    },
    "message": {
      "entry_id": "msg_67890abcdef12345...",
      "message_timestamp": "2023-06-15T14:31:12.456Z",
      "role": "assistant",
      "content": "Template message sent with SID: SM1234567890abcdef...",
      "ai_prompt_tokens": 2345,
      "ai_completion_tokens": 156,
      "ai_total_tokens": 2501,
      "processing_time_ms": 4267
    }
  },
  "metadata": {
    "router_version": "1.0.0"
  }
}
```

### Email Channel Example

```json
{
  "frontend_payload": {
    "company_data": {
      "company_id": "cucumber-recruitment",
      "project_id": "cv-analysis"
    },
    "recipient_data": {
      "recipient_first_name": "John",
      "recipient_last_name": "Doe",
      "recipient_tel": "+447700900123",
      "recipient_email": "john.doe@example.com",
      "comms_consent": true
    },
    "project_data": {
      "job_title": "Software Engineer",
      "job_description": "We are looking for a skilled software engineer...",
      "application_deadline": "2023-07-30T23:59:59Z"
    },
    "request_data": {
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "channel_method": "email",
      "initial_request_timestamp": "2023-06-15T14:30:45.123Z"
    }
  },
  "wa_company_data_payload": {
    "company_name": "Cucumber Recruitment Ltd",
    "project_name": "CV Analysis Bot",
    "project_status": "active",
    "allowed_channels": ["whatsapp", "email"],
    "company_rep": {
      "company_rep_1": "Carol",
      "company_rep_2": "Mark",
      "company_rep_3": null,
      "company_rep_4": null,
      "company_rep_5": null
    }
  },
  "project_rate_limits": {
    "requests_per_minute": 100,
    "requests_per_day": 10000,
    "concurrent_conversations": 50,
    "max_message_length": 4096
  },
  "channel_config": {
    "email": {
      "email_credentials_id": "email-credentials/cucumber-recruitment/cv-analysis/sendgrid",
      "company_email": "jobs@cucumber-recruitment.com"
    }
  },
  "ai_config": {
    "assistant_id_template_sender": "asst_Ds59ylP35Pn84pasJQVglC2Q",
    "assistant_id_replies": "asst_Ds59ylP35Pn84pesJQVglC2Q",
    "assistant_id_3": "",
    "assistant_id_4": "",
    "assistant_id_5": "",
    "ai_api_key_reference": "ai-api-key/global"
  },
  "conversation_data": {
    "conversation_id": "cucumber-recruitment#cv-analysis#550e8400-e29b-41d4-a716-446655440000#<550e8400.1625097083@cucumber.recruitment.mail>",
    "thread_id": "thread_abc123def456",
    "content_variables": {
      "1": "John",
      "2": "Software Engineer",
      "3": "your experience with cloud technologies"
    },
    "message": {
      "entry_id": "msg_67890abcdef12345...",
      "message_timestamp": "2023-06-15T14:31:12.456Z",
      "role": "assistant",
      "content": "Template message sent with Message-ID: <550e8400.1625097083@cucumber.recruitment.mail>",
      "ai_prompt_tokens": 2345,
      "ai_completion_tokens": 156,
      "ai_total_tokens": 2501,
      "processing_time_ms": 4267
    }
  },
  "metadata": {
    "router_version": "1.0.0"
  }
}
```

### SMS Channel Example

```json
{
  "frontend_payload": {
    "company_data": {
      "company_id": "cucumber-recruitment",
      "project_id": "cv-analysis"
    },
    "recipient_data": {
      "recipient_first_name": "John",
      "recipient_last_name": "Doe",
      "recipient_tel": "+447700900123",
      "recipient_email": "john.doe@example.com",
      "comms_consent": true
    },
    "project_data": {
      "job_title": "Software Engineer",
      "job_description": "We are looking for a skilled software engineer...",
      "application_deadline": "2023-07-30T23:59:59Z"
    },
    "request_data": {
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "channel_method": "sms",
      "initial_request_timestamp": "2023-06-15T14:30:45.123Z"
    }
  },
  "wa_company_data_payload": {
    "company_name": "Cucumber Recruitment Ltd",
    "project_name": "CV Analysis Bot",
    "project_status": "active",
    "allowed_channels": ["whatsapp", "email"],
    "company_rep": {
      "company_rep_1": "Carol",
      "company_rep_2": "Mark",
      "company_rep_3": null,
      "company_rep_4": null,
      "company_rep_5": null
    }
  },
  "project_rate_limits": {
    "requests_per_minute": 100,
    "requests_per_day": 10000,
    "concurrent_conversations": 50,
    "max_message_length": 4096
  },
  "channel_config": {
    "sms": {
      "sms_credentials_id": "sms-credentials/cucumber-recruitment/cv-analysis/twilio",
      "company_sms_number": "+14155238887"
    }
  },
  "ai_config": {
    "assistant_id_template_sender": "asst_Ds59ylP35Pn84pasJQVglC2Q",
    "assistant_id_replies": "asst_Ds59ylP35Pn84pesJQVglC2Q",
    "assistant_id_3": "",
    "assistant_id_4": "",
    "assistant_id_5": "",
    "ai_api_key_reference": "ai-api-key/global"
  },
  "conversation_data": {
    "conversation_id": "cucumber-recruitment#cv-analysis#550e8400-e29b-41d4-a716-446655440000#14155238887",
    "thread_id": "thread_abc123def456",
    "content_variables": {
      "1": "John",
      "2": "Software Engineer",
      "3": "your experience with cloud technologies"
    },
    "message": {
      "entry_id": "msg_67890abcdef12345...",
      "message_timestamp": "2023-06-15T14:31:12.456Z",
      "role": "assistant",
      "content": "Template message sent with SID: SM1234567890abcdef...",
      "ai_prompt_tokens": 2345,
      "ai_completion_tokens": 156,
      "ai_total_tokens": 2501,
      "processing_time_ms": 4267
    }
  },
  "metadata": {
    "router_version": "1.0.0"
  }
}
```

## Security Considerations

The context object contains sensitive information such as API keys and authentication tokens. To protect this data:

1. All SQS queues should have server-side encryption enabled
2. IAM policies should restrict access to the queues to only the necessary services
3. Lambda functions processing these messages should have appropriate security controls
4. Logs should be configured to not include sensitive data from the context object
5. The context object should never be stored in its entirety in persistent storage
6. **API keys from the frontend payload are not included in the context object. The API key is only used for initial authentication in the Channel Router and then discarded for security best practices**
7. Only credential references (not actual credentials) are included in the context object, requiring downstream services to retrieve credentials from Secrets Manager as needed

## Usage by Downstream Services

Downstream services can extract the necessary information from the context object:

```javascript
// Example of how a processing Lambda would use the context object
exports.handler = async (event) => {
  // SQS triggers Lambda with a batch of messages
  for (const record of event.Records) {
    // Parse the context object from the message
    const contextObject = JSON.parse(record.body);
    
    // Extract frontend payload
    const payload = contextObject.frontend_payload;
    
    // Extract company data including company representatives
    const companyData = contextObject.wa_company_data_payload;
    const companyRep = companyData.company_rep.company_rep_1 || "Company Representative";
    
    // Extract channel-specific configuration
    const channelMethod = payload.request_data.channel_method;
    const channelConfig = contextObject.channel_config[channelMethod];
    
    // Extract AI configuration
    const aiConfig = contextObject.ai_config;
    
    // Extract conversation ID for database operations
    const conversationId = contextObject.conversation_data.conversation_id;
    
    // Get credentials from Secrets Manager based on channel
    if (channelMethod === 'whatsapp') {
      // Get WhatsApp credentials from Secrets Manager
      const whatsappCredentials = await getSecretValue(channelConfig.whatsapp_credentials_id);
      await processWhatsAppMessage(payload, whatsappCredentials, aiConfig, conversationId, companyRep);
    } 
    else if (channelMethod === 'sms') {
      // Get SMS credentials from Secrets Manager
      const smsCredentials = await getSecretValue(channelConfig.sms_credentials_id);
      await processSMSMessage(payload, smsCredentials, aiConfig, conversationId, companyRep);
    }
    else if (channelMethod === 'email') {
      // Get Email credentials from Secrets Manager
      const emailCredentials = await getSecretValue(channelConfig.email_credentials_id);
      await processEmailMessage(payload, emailCredentials, aiConfig, conversationId, companyRep);
    }
  }
};

// Helper function to get secret values
async function getSecretValue(secretId) {
  const secretsManager = new AWS.SecretsManager();
  const response = await secretsManager.getSecretValue({ SecretId: secretId }).promise();
  return JSON.parse(response.SecretString);
}
``` 