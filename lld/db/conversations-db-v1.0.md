# wa_conversation DynamoDB Schema

This document defines the schema for the `wa_conversation` DynamoDB table, which stores conversation data across multiple channels (WhatsApp, SMS, Email) for the AI messaging system.

## Table Purpose

The `wa_conversation` table serves as the central repository for:
- Conversation tracking and management
- Message history and context
- Processing status and metadata
- Cross-channel conversation support
- Reply matching and threading

## Primary Keys Structure

The table uses a composite key structure to efficiently support multi-channel conversations:

- **Partition Key**: Channel-specific identifier
  - For WhatsApp/SMS: `recipient_tel` (Recipient's phone number)
  - For Email: `recipient_email` (Recipient's email address)
  
- **Sort Key**: `conversation_id` (Format: `{company_id}#{project_id}#{request_id}#{channel_specific_identifier}`)
  - WhatsApp: `{company_id}#{project_id}#{request_id}#{company_whatsapp_number}`
  - SMS: `{company_id}#{project_id}#{request_id}#{company_sms_number}`
  - Email: `{company_id}#{project_id}#{request_id}#{message_id}`

This key structure enables:
- Efficient lookups of specific conversations
- Channel-specific query patterns
- Reply matching for all supported channels
- Segmentation by company and project

## Attributes

| Attribute | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `recipient_tel` | String | Conditional | Primary key for WhatsApp/SMS conversations | "+447700900123" |
| `recipient_email` | String | Conditional | Primary key for Email conversations | "john.doe@example.com" |
| `conversation_id` | String | Yes | Sort key constructed for cross-channel support | "cucumber-recruitment#cv-analysis#550e8400-e29b-41d4-a716-446655440000#14155238886" |
| `company_id` | String | Yes | Company identifier | "cucumber-recruitment" |
| `project_id` | String | Yes | Project identifier | "cv-analysis" |
| `company_name` | String | Yes | Human-readable company name | "Cucumber Recruitment Ltd" |
| `project_name` | String | Yes | Human-readable project name | "CV Analysis Bot" |
| `channel_method` | String | Yes | Communication channel | "whatsapp", "sms", or "email" |
| `request_id` | String | Yes | Original request ID from frontend | "550e8400-e29b-41d4-a716-446655440000" |
| `router_version` | String | Yes | Version of Channel Router that processed the request | "1.0.0" |
| `whatsapp_credentials_reference` | String | Yes | Reference to WhatsApp credentials in Secrets Manager | "twilio/cucumber-recruitment/cv-analysis/whatsapp-credentials" |
| `sms_credentials_reference` | String | Yes | Reference to SMS credentials in Secrets Manager | "twilio/cucumber-recruitment/cv-analysis/sms-credentials" |
| `email_credentials_reference` | String | Yes | Reference to Email credentials in Secrets Manager | "sendgrid/cucumber-recruitment/cv-analysis/email-credentials" |
| `processing_metadata` | Map | Yes | Status tracking and processing info | See below |
| `ai_metadata` | Map | No | AI processing details | See below |
| `messages` | List | No | History of messages in conversation | See below |
| `company_phone_number` | String | Conditional | For WhatsApp/SMS - Company's phone number | "+14155238886" |
| `company_email` | String | Conditional | For Email - Company's email address | "jobs@cucumber-recruitment.com" |
| `message_id` | String | Conditional | For Email - Unique message identifier for threading | "<550e8400.1625097083@cucumber.recruitment.mail>" |
| `recipient_first_name` | String | No | Recipient's first name | "John" |
| `recipient_last_name` | String | No | Recipient's last name | "Doe" |
| `created_at` | String | Yes | ISO 8601 timestamp of creation | "2023-06-15T14:30:45.123Z" |
| `updated_at` | String | Yes | ISO 8601 timestamp of last update | "2023-06-15T14:30:45.123Z" |

## Complex Attribute Structures

### processing_metadata
```json
{
  "conversation_status": "received|processing|delivered|failed|completed",
  "processing_started_at": "2023-06-15T14:30:45.123Z",
  "processing_completed_at": "2023-06-15T14:31:22.456Z",
  "delivery_timestamp": "2023-06-15T14:31:20.789Z",
  "retry_count": 0,
  "error_details": {
    "error_code": "string",
    "error_message": "string",
    "error_timestamp": "string",
    "component": "string" // Which component failed (openai, twilio, etc.)
  }
}
```

### ai_metadata
```json
{
  "assistant_id": "asst_Ds59ylP35Pn84pasJQVglC2Q",
  "thread_id": "thread_abc123def456",
  "model": "gpt-4-turbo",
  "completion_tokens": 1420,
  "prompt_tokens": 560,
  "total_tokens": 1980,
  "processing_time_ms": 3500
}
```

### messages
```json
[
  {
    "message_id": "msg_abc123def456",
    "direction": "outbound|inbound",
    "content": "Hello John, thank you for your job application...",
    "timestamp": "2023-06-15T14:31:20.789Z",
    "status": "delivered|read|failed",
    "channel_message_id": "SMa1b2c3d4e5f6", // Twilio/SendGrid message ID
    "metadata": {
      // Channel-specific message metadata
    }
  },
  // Additional messages...
]
```

## Channel-Specific Attributes

### WhatsApp
```json
{
  "recipient_tel": "+447700900123",
  "conversation_id": "cucumber-recruitment#cv-analysis#550e8400-e29b-41d4-a716-446655440000#14155238886",
  "channel_method": "whatsapp",
  "company_phone_number": "+14155238886",
  // Common attributes...
}
```

### Email
```json
{
  "recipient_email": "john.doe@example.com",
  "conversation_id": "cucumber-recruitment#cv-analysis#550e8400-e29b-41d4-a716-446655440000#550e8400.1625097083",
  "channel_method": "email",
  "company_email": "jobs@cucumber-recruitment.com",
  "message_id": "<550e8400.1625097083@cucumber.recruitment.mail>",
  // Common attributes...
}
```

## Secondary Indexes

The table includes the following Global Secondary Indexes (GSIs) to support various query patterns:

### 1. ChannelMethodConversationIndex
- **Partition Key**: `channel_method`
- **Sort Key**: `conversation_id`
- **Projected Attributes**: All
- **Purpose**: Query all conversations by channel type, with optional filtering by conversation_id pattern

### 2. CompanyProjectIndex
- **Partition Key**: `company_id`
- **Sort Key**: `project_id`
- **Projected Attributes**: `conversation_id`, `channel_method`, `created_at`, `updated_at`, `processing_metadata`
- **Purpose**: Find all conversations for a specific company, optionally filtered by project

### 3. MessageIdIndex
- **Partition Key**: `message_id`
- **Sort Key**: None
- **Projected Attributes**: All
- **Purpose**: Support email threading by allowing lookup by message_id for email replies

### 4. StatusIndex
- **Partition Key**: `channel_method`
- **Sort Key**: `processing_metadata.conversation_status`
- **Projected Attributes**: `conversation_id`, `company_id`, `project_id`, `created_at`, `updated_at`
- **Purpose**: Find conversations by status (e.g., all failed WhatsApp conversations)

### 5. TimestampIndex
- **Partition Key**: `channel_method`
- **Sort Key**: `created_at`
- **Projected Attributes**: `conversation_id`, `company_id`, `project_id`, `processing_metadata`
- **Purpose**: Time-based queries like "all SMS conversations in the last 24 hours"

## Access Patterns

The table and its indexes support the following key access patterns:

1. **Find conversation by recipient contact and conversation_id** (Primary Key lookup)
   - WhatsApp/SMS: `recipient_tel` + `conversation_id`
   - Email: `recipient_email` + `conversation_id`

2. **Find all conversations for a channel type** (GSI: ChannelMethodConversationIndex)
   - `channel_method` = 'whatsapp'

3. **Find conversations by company and project** (GSI: CompanyProjectIndex)
   - `company_id` = 'cucumber-recruitment' AND `project_id` = 'cv-analysis'

4. **Match email replies using message_id** (GSI: MessageIdIndex)
   - `message_id` = '<message-id-from-email-header>'

5. **Find conversations by status** (GSI: StatusIndex)
   - `channel_method` = 'whatsapp' AND `processing_metadata.conversation_status` = 'failed'

6. **Find recent conversations** (GSI: TimestampIndex)
   - `channel_method` = 'email' AND `created_at` > '2023-06-14T00:00:00Z'

7. **Find WhatsApp/SMS reply conversations** (Primary key + Filter)
   - `recipient_tel` = '+447700900123' AND `company_phone_number` = '+14155238886'

8. **Find Email reply conversations** (Primary key + Filter)
   - `recipient_email` = 'john.doe@example.com' AND `company_email` = 'jobs@cucumber-recruitment.com'

## Example Items

### WhatsApp Conversation Example

```json
{
  "recipient_tel": "+447700900123",
  "conversation_id": "cucumber-recruitment#cv-analysis#550e8400-e29b-41d4-a716-446655440000#14155238886",
  "company_id": "cucumber-recruitment",
  "project_id": "cv-analysis",
  "channel_method": "whatsapp",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "whatsapp_credentials_reference": "twilio/cucumber-recruitment/cv-analysis/whatsapp-credentials",
  "company_phone_number": "+14155238886",
  "recipient_first_name": "John",
  "recipient_last_name": "Doe",
  "processing_metadata": {
    "conversation_status": "completed",
    "processing_started_at": "2023-06-15T14:30:45.123Z",
    "processing_completed_at": "2023-06-15T14:31:22.456Z",
    "delivery_timestamp": "2023-06-15T14:31:20.789Z",
    "retry_count": 0
  },
  "ai_metadata": {
    "assistant_id": "asst_Ds59ylP35Pn84pasJQVglC2Q",
    "thread_id": "thread_abc123def456",
    "model": "gpt-4-turbo",
    "completion_tokens": 1420,
    "prompt_tokens": 560,
    "total_tokens": 1980,
    "processing_time_ms": 3500
  },
  "messages": [
    {
      "message_id": "msg_abc123def456",
      "direction": "outbound",
      "content": "Hello John, thank you for your job application for the Software Engineer position at Cucumber Recruitment Ltd. We're delighted to inform you that your application has been shortlisted for the next round of our hiring process.",
      "timestamp": "2023-06-15T14:31:20.789Z",
      "status": "delivered",
      "channel_message_id": "SMa1b2c3d4e5f6"
    }
  ],
  "created_at": "2023-06-15T14:30:45.123Z",
  "updated_at": "2023-06-15T14:31:25.789Z"
}
```

### Email Conversation Example

```json
{
  "recipient_email": "john.doe@example.com",
  "conversation_id": "cucumber-recruitment#cv-analysis#550e8400-e29b-41d4-a716-446655440000#550e8400.1625097083",
  "company_id": "cucumber-recruitment",
  "project_id": "cv-analysis",
  "channel_method": "email",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "whatsapp_credentials_reference": "twilio/cucumber-recruitment/cv-analysis/whatsapp-credentials",
  "sms_credentials_reference": "twilio/cucumber-recruitment/cv-analysis/sms-credentials",
  "email_credentials_reference": "sendgrid/cucumber-recruitment/cv-analysis/email-credentials",
  "company_email": "jobs@cucumber-recruitment.com",
  "message_id": "<550e8400.1625097083@cucumber.recruitment.mail>",
  "recipient_first_name": "John",
  "recipient_last_name": "Doe",
  "processing_metadata": {
    "conversation_status": "completed",
    "processing_started_at": "2023-06-15T14:30:45.123Z",
    "processing_completed_at": "2023-06-15T14:31:22.456Z",
    "delivery_timestamp": "2023-06-15T14:31:20.789Z",
    "retry_count": 0
  },
  "ai_metadata": {
    "assistant_id": "asst_Ds59ylP35Pn84pasJQVglC2Q",
    "thread_id": "thread_def456ghi789",
    "model": "gpt-4-turbo",
    "completion_tokens": 1720,
    "prompt_tokens": 620,
    "total_tokens": 2340,
    "processing_time_ms": 4200
  },
  "messages": [
    {
      "message_id": "msg_def456ghi789",
      "direction": "outbound",
      "content": "Hello John,\n\nThank you for your job application for the Software Engineer position at Cucumber Recruitment Ltd. We're delighted to inform you that your application has been shortlisted for the next round of our hiring process.\n\nPlease let us know your availability for an interview next week.\n\nBest regards,\nRecruitment Team\nCucumber Recruitment Ltd",
      "timestamp": "2023-06-15T14:31:20.789Z",
      "status": "delivered",
      "channel_message_id": "SGx1y2z3a4b5c6",
      "metadata": {
        "subject": "Your Job Application for Software Engineer",
        "html_content": "<html><body>Hello John,<br><br>Thank you for your job application...</body></html>"
      }
    }
  ],
  "created_at": "2023-06-15T14:30:45.123Z",
  "updated_at": "2023-06-15T14:31:25.789Z"
}
```

## DynamoDB Capacity Settings

- **Read Capacity**: On-demand (to handle variable loads)
- **Write Capacity**: On-demand (for unpredictable write patterns)
- **Point-in-time Recovery**: Enabled (for disaster recovery)
- **TTL**: Optional, can be set on `updated_at` with a configurable retention period

## Implementation Considerations

1. **Sparse Indexes and Conditional Attributes**:
   - The table uses a sparse index pattern where certain attributes only exist for specific channel types
   - This optimizes storage and index size while maintaining query efficiency

2. **Conversation Status Tracking**:
   - The status flow follows: received → processing → delivered → completed
   - Failed status can occur at any stage and includes detailed error information

3. **Message History Management**:
   - Messages list grows over time as conversations continue
   - Consider implementing pagination or windowing for conversations with many messages
   - For very long conversations, consider archiving older messages to a separate table

4. **Reply Matching Strategy**:
   - WhatsApp/SMS: Match on recipient phone number and company phone number
   - Email: Primary match on message_id from email headers, fallback to recipient email

5. **Data Consistency**:
   - Channel-specific attributes should always align with the channel_method
   - Required fields should be strictly enforced based on channel type

6. **Security Considerations**:
   - IAM policies should restrict access to specific company/project combinations
   - Consider field-level encryption for sensitive message content
   - Implement audit logging for all conversation data access 