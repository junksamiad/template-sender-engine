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
// Generate a unique conversation ID that incorporates multiple attributes for tracking and retrieval
// Format: {company_id}#{project_id}#{request_id}#{company_whatsapp_number}
// This structure allows for comprehensive data tracking while still enabling efficient reply handling
const conversation_id = generateConversationId(
  company_data.company_id,
  company_data.project_id,
  request_data.request_id,
  channel_config.whatsapp.phone_number
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

### Conversation ID Generation Logic

```javascript
function generateConversationId(companyId, projectId, requestId, companyWhatsAppNumber) {
  // Sanitize phone number by removing any non-alphanumeric characters
  const sanitizedCompanyNumber = companyWhatsAppNumber.replace(/\D/g, '');
  
  // Combine into a single string with a delimiter
  return `${companyId}#${projectId}#${requestId}#${sanitizedCompanyNumber}`;
}
```

### Rationale for this Key Structure

This key structure was chosen for several specific reasons:

1. **Comprehensive data tracking**: The four-attribute structure (company_id, project_id, request_id, company_whatsapp_number) provides complete traceability and context for each conversation.

2. **Hierarchical querying**: Allows for querying conversations at various levels of the hierarchy (by company, by project, by request, by WhatsApp number).

3. **Optimized for the reply flow**: For handling replies, we can efficiently query based on recipient_tel (partition key) and use a begins_with condition on the conversation_id that includes the company WhatsApp number.

4. **Edge case handling**: The inclusion of request_id provides additional uniqueness in the unlikely event of multiple conversations between the same numbers.

5. **Follows DynamoDB best practices**: Designs the key structure based on the application's access patterns while maintaining flexibility.

### Querying for Reply Handling

When a reply comes in via Twilio, we receive the recipient's phone number and the company's WhatsApp number. We can efficiently retrieve the conversation with:

```javascript
// For handling replies
async function findConversationForReply(recipientTel, companyWhatsAppNumber) {
  // Sanitize phone number
  const sanitizedCompanyNumber = companyWhatsAppNumber.replace(/\D/g, '');
  
  // Query DynamoDB
  const params = {
    TableName: "wa_conversation",
    KeyConditionExpression: "recipient_tel = :tel AND contains(conversation_id, :companyNumber)",
    ExpressionAttributeValues: {
      ":tel": recipientTel,
      ":companyNumber": sanitizedCompanyNumber
    }
  };
  
  const result = await dynamoDB.query(params).promise();
  return result.Items;
}
```

Alternatively, since the company WhatsApp number is also stored as a separate attribute:

```javascript
// Alternative approach using a query on the partition key and filter
async function findConversationForReply(recipientTel, companyWhatsAppNumber) {
  const params = {
    TableName: "wa_conversation",
    KeyConditionExpression: "recipient_tel = :tel",
    FilterExpression: "company_phone_number = :companyNumber",
    ExpressionAttributeValues: {
      ":tel": recipientTel,
      ":companyNumber": companyWhatsAppNumber
    }
  };
  
  const result = await dynamoDB.query(params).promise();
  return result.Items;
}
```

This approach provides both comprehensive data organization and efficient querying for the reply handling flow.

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