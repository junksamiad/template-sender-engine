# Context Object Structure

This document describes the structure of the context object created by the Channel Router and passed to the channel-specific queues for processing.

## Purpose

The context object serves as a comprehensive package containing:
1. The original request payload from the frontend
2. Company and project configuration from the DynamoDB database
3. Channel-specific configuration and credentials
4. AI service configuration and credentials
5. Metadata for tracking and debugging

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
    "allowed_channels": ["whatsapp", "email"]
  },
  "project_rate_limits": {
    "requests_per_minute": 100,
    "requests_per_day": 10000,
    "concurrent_conversations": 50,
    "max_message_length": 4096
  },
  "channel_config": {
    "whatsapp": {
      "whatsapp_credentials_id": "twilio/cucumber-recruitment/cv-analysis/whatsapp-credentials",
      "company_whatsapp_number": "+14155238886"
    },
    "sms": {
      "sms_credentials_id": "twilio/cucumber-recruitment/cv-analysis/sms-credentials",
      "company_sms_number": "+14155238887"
    },
    "email": {
      "email_credentials_id": "sendgrid/cucumber-recruitment/cv-analysis/email-credentials",
      "company_email": "jobs@cucumber-recruitment.com"
    }
  },
  "ai_config": {
    "assistant_id_template_sender": "asst_Ds59ylP35Pn84pasJQVglC2Q",
    "assistant_id_replies": "asst_Ds59ylP35Pn84pesJQVglC2Q",
    "assistant_id_3": "",
    "assistant_id_4": "",
    "assistant_id_5": ""
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
    "whatsapp_credentials_id": "twilio/cucumber-recruitment/cv-analysis/whatsapp-credentials",
    "company_whatsapp_number": "+14155238886"
  },
  "sms": {
    "sms_credentials_id": "twilio/cucumber-recruitment/cv-analysis/sms-credentials",
    "company_sms_number": "+14155238887"
  },
  "email": {
    "email_credentials_id": "sendgrid/cucumber-recruitment/cv-analysis/email-credentials",
    "company_email": "jobs@cucumber-recruitment.com"
  }
}
```

| Channel | Field | Description |
|---------|-------|-------------|
| whatsapp | `whatsapp_credentials_id` | Reference to WhatsApp (Twilio) credentials in Secrets Manager |
| whatsapp | `company_whatsapp_number` | The WhatsApp phone number assigned to this company/project |
| sms | `sms_credentials_id` | Reference to SMS (Twilio) credentials in Secrets Manager |
| sms | `company_sms_number` | The SMS phone number assigned to this company/project |
| email | `email_credentials_id` | Reference to Email (SendGrid) credentials in Secrets Manager |
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
      "job_description": "We are looking for a skilled software engineer..."
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
    "allowed_channels": ["whatsapp", "email"]
  },
  "project_rate_limits": {
    "requests_per_minute": 100,
    "requests_per_day": 10000,
    "concurrent_conversations": 50,
    "max_message_length": 4096
  },
  "channel_config": {
    "whatsapp": {
      "whatsapp_credentials_id": "twilio/cucumber-recruitment/cv-analysis/whatsapp-credentials",
      "company_whatsapp_number": "+14155238886"
    }
  },
  "ai_config": {
    "assistant_id_template_sender": "asst_Ds59ylP35Pn84pasJQVglC2Q",
    "assistant_id_replies": "asst_Ds59ylP35Pn84pesJQVglC2Q",
    "assistant_id_3": "",
    "assistant_id_4": "",
    "assistant_id_5": ""
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
      "job_description": "We are looking for a skilled software engineer..."
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
    "allowed_channels": ["whatsapp", "email"]
  },
  "project_rate_limits": {
    "requests_per_minute": 100,
    "requests_per_day": 10000,
    "concurrent_conversations": 50,
    "max_message_length": 4096
  },
  "channel_config": {
    "email": {
      "email_credentials_id": "sendgrid/cucumber-recruitment/cv-analysis/email-credentials",
      "company_email": "jobs@cucumber-recruitment.com"
    }
  },
  "ai_config": {
    "assistant_id_template_sender": "asst_Ds59ylP35Pn84pasJQVglC2Q",
    "assistant_id_replies": "asst_Ds59ylP35Pn84pesJQVglC2Q",
    "assistant_id_3": "",
    "assistant_id_4": "",
    "assistant_id_5": ""
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
      "job_description": "We are looking for a skilled software engineer..."
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
    "allowed_channels": ["whatsapp", "email"]
  },
  "project_rate_limits": {
    "requests_per_minute": 100,
    "requests_per_day": 10000,
    "concurrent_conversations": 50,
    "max_message_length": 4096
  },
  "channel_config": {
    "sms": {
      "sms_credentials_id": "twilio/cucumber-recruitment/cv-analysis/sms-credentials",
      "company_sms_number": "+14155238887"
    }
  },
  "ai_config": {
    "assistant_id_template_sender": "asst_Ds59ylP35Pn84pasJQVglC2Q",
    "assistant_id_replies": "asst_Ds59ylP35Pn84pesJQVglC2Q",
    "assistant_id_3": "",
    "assistant_id_4": "",
    "assistant_id_5": ""
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
    
    // Extract channel-specific configuration
    const channelMethod = payload.request_data.channel_method;
    const channelConfig = contextObject.channel_config[channelMethod];
    
    // Extract AI configuration
    const aiConfig = contextObject.ai_config;
    
    // Get credentials from Secrets Manager based on channel
    if (channelMethod === 'whatsapp') {
      // Get WhatsApp credentials from Secrets Manager
      const whatsappCredentials = await getSecretValue(channelConfig.whatsapp_credentials_id);
      await processWhatsAppMessage(payload, whatsappCredentials, aiConfig);
    } 
    else if (channelMethod === 'sms') {
      // Get SMS credentials from Secrets Manager
      const smsCredentials = await getSecretValue(channelConfig.sms_credentials_id);
      await processSMSMessage(payload, smsCredentials, aiConfig);
    }
    else if (channelMethod === 'email') {
      // Get Email credentials from Secrets Manager
      const emailCredentials = await getSecretValue(channelConfig.email_credentials_id);
      await processEmailMessage(payload, emailCredentials, aiConfig);
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