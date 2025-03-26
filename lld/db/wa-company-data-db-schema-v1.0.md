# wa_company_data DynamoDB Schema

This document defines the schema for the `wa_company_data` DynamoDB table, which stores company and project configuration data for the WhatsApp AI chatbot system.

## Table Purpose

The `wa_company_data` table serves as the central repository for:
- Company and project identification
- API authentication references
- Channel permissions and configurations
- Rate limiting and quota management
- Project status tracking

## Context Object Integration

When the Channel Router processes a request, it maps data from this table into several sections of the context object. This mapping ensures all necessary configuration is available to downstream services without additional database queries.

### Data Mapping

1. **wa_company_data_payload**
   ```javascript
   {
     "company_name": "From company_name field",
     "project_name": "From project_name field",
     "project_status": "From project_status field",
     "allowed_channels": ["From allowed_channels array"],
     "company_rep": {
       // Direct copy of company_rep structure
       "company_rep_1": "From company_rep.company_rep_1",
       "company_rep_2": "From company_rep.company_rep_2",
       // ... etc
     }
   }
   ```

2. **project_rate_limits**
   ```javascript
   {
     "requests_per_minute": "From rate_limits.requests_per_minute",
     "requests_per_day": "From rate_limits.requests_per_day",
     "concurrent_conversations": "From rate_limits.concurrent_conversations",
     "max_message_length": "From rate_limits.max_message_length"
   }
   ```

3. **channel_config**
   ```javascript
   {
     // Only the relevant channel config is included based on the request
     "whatsapp": {
       "whatsapp_credentials_id": "From channel_config.whatsapp.whatsapp_credentials_id",
       "company_whatsapp_number": "From channel_config.whatsapp.company_whatsapp_number"
     }
   }
   ```

4. **ai_config**
   ```javascript
   {
     // Direct copy of ai_config structure
     "assistant_id_template_sender": "From ai_config.assistant_id_template_sender",
     "assistant_id_replies": "From ai_config.assistant_id_replies",
     "assistant_id_3": "From ai_config.assistant_id_3",
     "assistant_id_4": "From ai_config.assistant_id_4",
     "assistant_id_5": "From ai_config.assistant_id_5",
     "ai_api_key_reference": "From ai_config.ai_api_key_reference"
   }
   ```

For the complete context object structure and how this data is used, refer to [Context Object Documentation](../context-object/context-object-v1.0.md).

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
| `ai_api_key_reference` | Reference to OpenAI API key |