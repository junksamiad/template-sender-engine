# wa_company_data DynamoDB Schema

This document defines the schema for the `wa_company_data` DynamoDB table, which stores company and project configuration data for the WhatsApp AI chatbot system.

## Table Purpose

The `wa_company_data` table serves as the central repository for:
- Company and project identification
- API authentication references
- Channel permissions and configurations
- Rate limiting and quota management
- Project status tracking

## Primary Keys

- **Partition Key**: `company_id` (String) - Unique identifier for each company
- **Sort Key**: `project_id` (String) - Unique identifier for each project within a company

This key structure allows:
- Efficient lookups of specific company/project combinations
- Queries for all projects belonging to a specific company
- Separation of data between different companies for security

## Attributes

| Attribute | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `company_id` | String | Yes | Unique identifier for the company | "cucumber-recruitment" |
| `project_id` | String | Yes | Unique identifier for the project | "cv-analysis" |
| `company_name` | String | Yes | Human-readable company name | "Cucumber Recruitment Ltd" |
| `project_name` | String | Yes | Human-readable project name | "CV Analysis Bot" |
| `api_key_reference` | String | Yes | Reference to API key in Secrets Manager | "secret/api-keys/cucumber-recruitment/cv-analysis" |
| `allowed_channels` | List(String) | Yes | List of channels this project can use | ["whatsapp", "email"] |
| `rate_limits` | Map | Yes | Rate limiting configuration | See below |
| `project_status` | String | Yes | Current status of the project | "active" |
| `company_rep` | Map | No | Company representatives information | See below |
| `ai_config` | Map | No | OpenAI-specific configuration | See below |
| `channel_config` | Map | No | Channel-specific configurations | See below |
| `created_at` | String | Yes | ISO 8601 timestamp of creation | "2023-06-15T14:30:45.123Z" |
| `updated_at` | String | Yes | ISO 8601 timestamp of last update | "2023-06-15T14:30:45.123Z" |

## Complex Attribute Structures

### rate_limits
```json
{
  "requests_per_minute": 100,
  "requests_per_day": 10000,
  "concurrent_conversations": 50,
  "max_message_length": 4096
}
```

> **Note: Current Implementation Status**
> While these rate limits are defined in the schema and included in the context object, they are **not currently enforced** in the Channel Router implementation. The system currently relies only on the API Gateway's global rate limits. Per-client rate limiting is planned for future implementation.

### company_rep
```json
{
  "company_rep_1": "Carol",
  "company_rep_2": "Mark",
  "company_rep_3": null,
  "company_rep_4": null,
  "company_rep_5": null
}
```

This structure stores up to 5 company representatives that may be involved in conversations:
- All fields are optional and can be set to null if not needed
- These values will be transferred to the conversation records during conversation creation
- When creating new company records, you need not specify all 5 representatives
- For consistency, always include the structure with null values for unneeded fields

### ai_config
```json
{
  "assistant_id_template_sender": "asst_Ds59ylP35Pn84pasJQVglC2Q",
  "assistant_id_replies": "asst_Ds59ylP35Pn84pesJQVglC2Q",
  "assistant_id_3": "",
  "assistant_id_4": "",
  "assistant_id_5": "",
  "ai_api_key_reference": "ai-api-key/global"
}
```

| Field | Description |
|-------|-------------|
| `assistant_id_template_sender` | OpenAI Assistant ID for sending initial templates |
| `assistant_id_replies` | OpenAI Assistant ID for handling replies |
| `assistant_id_3` | Additional OpenAI Assistant ID (optional) |
| `assistant_id_4` | Additional OpenAI Assistant ID (optional) |
| `assistant_id_5` | Additional OpenAI Assistant ID (optional) |
| `ai_api_key_reference` | Reference to AI API key in Secrets Manager that is used across all channels |

### channel_config
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

| Channel | Field | Description |
|---------|-------|-------------|
| whatsapp | `whatsapp_credentials_id` | Reference to WhatsApp (Twilio) credentials in Secrets Manager using format: whatsapp-credentials/{company_id}/{project_id}/twilio |
| whatsapp | `company_whatsapp_number` | The WhatsApp phone number assigned to this company/project |
| sms | `sms_credentials_id` | Reference to SMS (Twilio) credentials in Secrets Manager using format: sms-credentials/{company_id}/{project_id}/twilio |
| sms | `company_sms_number` | The SMS phone number assigned to this company/project |
| email | `email_credentials_id` | Reference to Email (SendGrid) credentials in Secrets Manager using format: email-credentials/{company_id}/{project_id}/sendgrid |
| email | `company_email` | The email address assigned to this company/project |

## Status Values

The `project_status` field can have the following values:
- `active`: Project is active and can process requests
- `inactive`: Project is temporarily disabled
- `pending`: Project is in setup phase
- `suspended`: Project has been suspended due to policy violation or billing issues
- `archived`: Project is no longer in use but data is retained

## Example Item

```json
{
  "company_id": "cucumber-recruitment",
  "project_id": "cv-analysis",
  "company_name": "Cucumber Recruitment Ltd",
  "project_name": "CV Analysis Bot",
  "api_key_reference": "secret/api-keys/cucumber-recruitment/cv-analysis",
  "allowed_channels": ["whatsapp", "email", "sms"],
  "rate_limits": {
    "requests_per_minute": 100,
    "requests_per_day": 10000,
    "concurrent_conversations": 50,
    "max_message_length": 4096
  },
  "project_status": "active",
  "company_rep": {
    "company_rep_1": "Carol",
    "company_rep_2": "Mark",
    "company_rep_3": null,
    "company_rep_4": null,
    "company_rep_5": null
  },
  "ai_config": {
    "assistant_id_template_sender": "asst_Ds59ylP35Pn84pasJQVglC2Q",
    "assistant_id_replies": "asst_Ds59ylP35Pn84pesJQVglC2Q",
    "assistant_id_3": "",
    "assistant_id_4": "",
    "assistant_id_5": "",
    "ai_api_key_reference": "ai-api-key/global"
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
  "created_at": "2023-06-15T14:30:45.123Z",
  "updated_at": "2023-06-15T14:30:45.123Z"
}
```

## Access Patterns

The table is designed to support the following access patterns:

1. Get company/project configuration by company_id and project_id (primary key lookup)
2. List all projects for a specific company (query on partition key only)
3. Check if a project is active and allowed to use a specific channel
4. Validate API key references during authentication
5. Enforce rate limits based on company/project configuration

## Security Considerations

- No sensitive credentials are stored directly in this table
- References to Secrets Manager are used for all sensitive information
- IAM policies should restrict access to this table to only the necessary services
- All changes to this table should be logged and audited

## DynamoDB Capacity Settings

- **Read Capacity**: On-demand (to handle variable authentication loads)
- **Write Capacity**: On-demand (writes are infrequent, mostly during setup)
- **Point-in-time Recovery**: Enabled (for disaster recovery)
- **TTL**: Not enabled (data should be retained indefinitely)

## Indexes

### Global Secondary Indexes

1. **CompanyNameIndex**
   - Partition Key: `company_name`
   - Sort Key: `project_name`
   - Projected Attributes: All
   - Purpose: Allow lookups by human-readable names for admin interfaces

2. **StatusIndex**
   - Partition Key: `project_status`
   - Sort Key: `updated_at`
   - Projected Attributes: `company_id`, `project_id`, `company_name`, `project_name`
   - Purpose: Find recently changed projects with a specific status 