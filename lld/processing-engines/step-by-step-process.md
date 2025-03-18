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
   - Sort key would be `conversation_id` (which could incorporate the company's WhatsApp number)

4. **Channel Configuration Access**:
   - The company's WhatsApp number is stored in the `channel_config.whatsapp` object in DynamoDB rather than in Secrets Manager
   - This makes sense as the phone number itself isn't sensitive credentials (unlike API keys)
   - Makes it easier to create the conversation record without additional Secrets Manager calls

5. **Multi-Channel Support in Conversations Table**:
   - A `channel_method` field differentiates between WhatsApp/SMS/Email records
   - This allows the same table to store conversations across all channels
   - Each channel would have its own specific fields:
     - WhatsApp/SMS: `recipient_tel` as primary key
     - Email: `recipient_email` as primary key

## Configuration Details

The WhatsApp channel configuration in the `wa_company_data` DynamoDB table would look like:

```json
"channel_config": {
  "whatsapp": {
    "phone_number": "+14155238886",  // Company's WhatsApp number for this project
    "whatsapp_credentials_id": "twilio/company-123/whatsapp-credentials"  // Reference to auth credentials in Secrets Manager
  },
  "sms": { /* SMS configuration */ },
  "email": { /* Email configuration */ }
}
```

## Conversation Record Creation

When creating the conversation record:

```javascript
// Generate a unique conversation ID that incorporates the company WhatsApp number
const conversation_id = generateConversationId(
  recipient_data.recipient_tel, 
  channel_config.whatsapp.phone_number,
  request_data.request_id
);

// Create conversation record
const newConversation = {
  recipient_tel: recipient_data.recipient_tel,  // Partition key
  conversation_id: conversation_id,  // Sort key
  company_id: company_data.company_id,
  project_id: company_data.project_id,
  channel_method: "whatsapp",  // Indicates this is a WhatsApp conversation
  company_phone_number: channel_config.whatsapp.phone_number,  // Store company's WhatsApp number
  request_id: request_data.request_id,
  processing_metadata: {
    conversation_status: "received",
    processing_started_at: new Date().toISOString(),
    retry_count: 0
  },
  // ... other fields as in our schema
};
```

This approach provides a flexible structure that works across all channels while maintaining the channel-specific details needed for each type of conversation.

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