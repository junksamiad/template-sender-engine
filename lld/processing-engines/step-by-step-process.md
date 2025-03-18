# WhatsApp Processing Engine - Step by Step Process

This document outlines the detailed step-by-step flow of the WhatsApp Processing Engine from message retrieval to OpenAI API call.

## Initial Processing Flow

1. **SQS Message Consumption**:
   - WhatsApp Processing Engine Lambda is triggered by a new message in the WhatsApp SQS queue
   - The message contains the context object created by the Channel Router
   - Lambda immediately sets up the heartbeat pattern to extend visibility timeout every 5 minutes

2. **Context Object Parsing**:
   - Lambda parses the context object which contains:
     - `frontend_payload`: Original request from the frontend
     - `db_payload`: Company/project data from DynamoDB 
     - `channel_config`: Channel-specific configurations
     - `ai_config`: OpenAI assistant configurations
     - `metadata`: Additional context information including:
        - `context_creation_timestamp`: When the context object was created
        - `router_version`: Version of the Channel Router that created the context
        - `request_id`: Same as the request_id in the frontend_payload (for easy access)
     - `project_rate_limits`: Rate limiting configuration for the project

3. **Conversation Record Creation**:
   - A composite key structure is used for the conversation table
   - Primary key would be `recipient_tel` (recipient's phone number)
   - Sort key would be `conversation_id` (which incorporates the company's WhatsApp number)
   - The `conversation_id` follows this format: `{company_id}#{project_id}#{request_id}#{company_whatsapp_number}`
   - This structure ensures uniqueness across all conversations while facilitating efficient queries
   - Including the `project_id` in the conversation_id is critical for companies with multiple projects
   - The company WhatsApp number is obtained from the `channel_config.whatsapp.company_whatsapp_number` field

4. **Channel Configuration Access**:
   - The company's WhatsApp number is stored in the `channel_config.whatsapp.company_whatsapp_number` object in DynamoDB wa_company_data table rather than in Secrets Manager
   - This makes sense as the phone number itself isn't sensitive credentials (unlike API keys)
   - Makes it easier to create the conversation record without additional Secrets Manager calls
   - The actual Twilio credentials are retrieved from AWS Secrets Manager using the reference `channel_config.whatsapp.whatsapp_credentials_id`

5. **Multi-Channel Support in Conversations Table**:
   - A `channel_method` field is included in every record to indicate the communication channel (whatsapp, sms, email)
   - Each channel requires a different approach to key structure and conversation identification:
   
   **WhatsApp Channel:**
   - Primary Key: `recipient_tel` (recipient's phone number)
   - Sort Key: `conversation_id` with format: `{company_id}#{project_id}#{request_id}#{company_whatsapp_number}`
   - Reply Identification: Match on recipient phone number and company WhatsApp number
   
   **SMS Channel:**
   - Primary Key: `recipient_tel` (recipient's phone number)
   - Sort Key: `conversation_id` with format: `{company_id}#{project_id}#{request_id}#{company_sms_number}`
   - Reply Identification: Match on recipient phone number and company SMS number
   
   **Email Channel:**
   - Primary Key: `recipient_email` (recipient's email address)
   - Sort Key: `conversation_id` with format: `{company_id}#{project_id}#{request_id}#{message_id}`
   - Where `message_id` would be a unique identifier for the email thread (e.g., Message-ID header)
   - Reply Identification: Use of email threading headers (References, In-Reply-To) to match to original message
   
   **Implementation Considerations:**
   - The conversations table will have a sparse index pattern where records contain only relevant fields for their channel
   - Secondary indexes may be needed for efficient email thread lookup based on email headers
   - For email, we would store both the email thread ID and the company sender email to enable different query paths

## Configuration Details

The channel configuration in the `wa_company_data` DynamoDB table would vary by channel:

```json
"channel_config": {
  "whatsapp": {
    "company_whatsapp_number": "+14155238886",  // Company's WhatsApp number for this project
    "whatsapp_credentials_id": "twilio/cucumber-recruitment/cv-analysis/whatsapp-credentials"  // Reference to auth credentials
  },
  "sms": {
    "company_sms_number": "+14155238887",  // Company's SMS number for this project  
    "sms_credentials_id": "twilio/cucumber-recruitment/cv-analysis/sms-credentials"  // Reference to auth credentials
  },
  "email": {
    "company_email_address": "jobs@cucumber-recruitment.com",  // Sender email for this project
    "email_credentials_id": "sendgrid/cucumber-recruitment/cv-analysis/email-credentials"  // Reference to auth credentials
  }
}
```

## Conversation Record Creation By Channel

The conversation record creation would adapt based on the channel:

### WhatsApp Conversation Creation

```javascript
// WhatsApp conversation ID generation
const whatsapp_conversation_id = generateWhatsAppConversationId(
  company_data.company_id,
  company_data.project_id,
  request_data.request_id,
  channel_config.whatsapp.company_whatsapp_number
);

// Create WhatsApp conversation record
const newWhatsAppConversation = {
  recipient_tel: recipient_data.recipient_tel,  // Partition key
  conversation_id: whatsapp_conversation_id,  // Sort key
  company_id: company_data.company_id,
  project_id: company_data.project_id,
  channel_method: "whatsapp",  // Indicates this is a WhatsApp conversation
  company_phone_number: channel_config.whatsapp.company_whatsapp_number,
  request_id: request_data.request_id,
  credentials_reference: channel_config.whatsapp.whatsapp_credentials_id,
  processing_metadata: {
    conversation_status: "received",
    processing_started_at: new Date().toISOString(),
    retry_count: 0
  }
  // ... other fields
};
```

### Email Conversation Creation

```javascript
// Generate a unique message ID for email threading
const message_id = generateUniqueMessageId(company_data.company_id, request_data.request_id);

// Email conversation ID generation
const email_conversation_id = generateEmailConversationId(
  company_data.company_id,
  company_data.project_id,
  request_data.request_id,
  message_id
);

// Create Email conversation record
const newEmailConversation = {
  recipient_email: recipient_data.recipient_email,  // Partition key
  conversation_id: email_conversation_id,  // Sort key
  company_id: company_data.company_id,
  project_id: company_data.project_id,
  channel_method: "email",  // Indicates this is an Email conversation
  company_email: channel_config.email.company_email_address,
  message_id: message_id,  // Store for email thread tracking
  request_id: request_data.request_id,
  credentials_reference: channel_config.email.email_credentials_id,
  processing_metadata: {
    conversation_status: "received",
    processing_started_at: new Date().toISOString(),
    retry_count: 0
  }
  // ... other fields
};
```

### Channel-Specific Generation Logic

```javascript
function generateWhatsAppConversationId(companyId, projectId, requestId, companyWhatsAppNumber) {
  // Sanitize phone number by removing any non-alphanumeric characters
  const sanitizedCompanyNumber = companyWhatsAppNumber.replace(/\D/g, '');
  
  // Combine into a single string with a delimiter
  return `${companyId}#${projectId}#${requestId}#${sanitizedCompanyNumber}`;
}

function generateEmailConversationId(companyId, projectId, requestId, messageId) {
  // For email, we use the message ID which is already unique
  return `${companyId}#${projectId}#${requestId}#${messageId}`;
}

function generateUniqueMessageId(companyId, requestId) {
  // Generate a unique ID following common email Message-ID format
  const domain = companyId.includes('-') ? companyId.split('-').join('.') : companyId;
  const timestamp = Date.now();
  return `<${requestId}.${timestamp}@${domain}.mail>`;
}
```

### Reply Handling by Channel

Different channels require different approaches to match incoming replies:

#### WhatsApp Reply Handling

```javascript
// For handling WhatsApp replies
async function findWhatsAppConversation(recipientTel, companyWhatsAppNumber) {
  const params = {
    TableName: "wa_conversation",
    KeyConditionExpression: "recipient_tel = :tel",
    FilterExpression: "company_phone_number = :companyNumber AND channel_method = :channel",
    ExpressionAttributeValues: {
      ":tel": recipientTel,
      ":companyNumber": companyWhatsAppNumber,
      ":channel": "whatsapp"
    }
  };
  
  const result = await dynamoDB.query(params).promise();
  return result.Items;
}
```

#### Email Reply Handling

```javascript
// For handling Email replies - using email headers
async function findEmailConversation(recipientEmail, emailHeaders) {
  let messageId = null;
  
  // Try to extract the original message ID from email headers
  if (emailHeaders.references) {
    // References header contains a list of message IDs in the thread
    const messageIds = emailHeaders.references.split(' ');
    // Use the first message ID (the original one)
    messageId = messageIds[0];
  } else if (emailHeaders.inReplyTo) {
    // In-Reply-To header contains the immediate parent message ID
    messageId = emailHeaders.inReplyTo;
  }
  
  if (messageId) {
    // Create a secondary index on message_id for efficient lookup
    const params = {
      TableName: "wa_conversation",
      IndexName: "MessageIdIndex",
      KeyConditionExpression: "message_id = :mid",
      FilterExpression: "channel_method = :channel",
      ExpressionAttributeValues: {
        ":mid": messageId,
        ":channel": "email"
      }
    };
    
    const result = await dynamoDB.query(params).promise();
    return result.Items;
  }
  
  // Fallback to recipient email if no message ID available
  const params = {
    TableName: "wa_conversation",
    KeyConditionExpression: "recipient_email = :email",
    FilterExpression: "channel_method = :channel",
    ExpressionAttributeValues: {
      ":email": recipientEmail,
      ":channel": "email"
    }
  };
  
  const result = await dynamoDB.query(params).promise();
  return result.Items;
}
```

This approach provides channel-specific handling while maintaining a consistent overall structure for conversation records. Each channel gets its own optimized identification strategy while sharing the same DynamoDB table.

## Status Tracking

Once the conversation record is created, the status is set to "received". The next steps would be:

1. **Retrieve API Credentials**:
   - Get OpenAI and Twilio credentials from AWS Secrets Manager using the credential references from the context object

2. **Initialize API Clients**:
   - Create OpenAI and Twilio API client instances with the retrieved credentials

3. **Update Status to "processing"**:
   - Update the conversation record status to "processing" before initiating the OpenAI API call
   - This update includes a timestamp for when processing began

At this point, the engine is ready to make the OpenAI API call, which will be the next step in the process. 