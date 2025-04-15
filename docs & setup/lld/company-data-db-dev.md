# `company-data-dev` DynamoDB Schema

This document defines the schema for the `company-data-dev` DynamoDB table, which stores company and project configuration data for the AI multi-channel communications platform development environment.

## Table Purpose

The `company-data-dev` table serves as the central repository in the development environment for:
- Company and project identification
- API authentication key references (for correlation/tracking)
- Channel permissions and configurations
- Rate limiting settings (for future use)
- Project status tracking

## Context Object Construction

When the Channel Router Lambda (`src_dev/channel-router/lambda/index.py`) processes a request, it retrieves the corresponding item from this table using `company_id` and `project_id`. 

This fetched data (`company_data_dict`) is then passed, along with the original `frontend_payload_dict` and the router `VERSION`, to the `build_context_object` function in `src_dev/channel-router/lambda/core/context_builder.py`. 

The `build_context_object` function uses this information to construct the final `context_object` sent to the SQS queue. Refer to `context_builder.py` for the precise structure of the generated context object.

## Primary Keys

- **Partition Key**: `company_id` (String) - Unique identifier for each company (e.g., `ci-aaa-001`).
- **Sort Key**: `project_id` (String) - Unique identifier for each project within a company (e.g., `pi-aaa-001`).

This key structure allows:
- Efficient lookups of specific company/project combinations using `GetItem`.
- Potential queries for all projects belonging to a specific company.

## Attributes Table

| Attribute | Type | Required | Description | Example | Notes |
|---|---|---|---|---|---|
| `company_id` | String | Yes | Unique identifier for the company (lowercase, use hyphens). | `"ci-aaa-001"` | Partition Key |
| `project_id` | String | Yes | Unique identifier for the project (lowercase, use hyphens). | `"pi-aaa-001"` | Sort Key |
| `company_name` | String | Yes | Human-readable company name. | `"Cucumber Recruitment"` |  |
| `project_name` | String | Yes | Human-readable project name. | `"Clarify CV"` |  |
| `api_key_reference` | String | Yes | **API Gateway Key ID** (not the value) associated with this project. Used for reference/correlation. | `"a1b2c3d4e5"` | Must match the ID generated in API Gateway (see onboarding docs). |
| `allowed_channels` | List (String Set - SS) | Yes | List of channel methods this project is permitted to use. | `["whatsapp"]` | Valid values: `whatsapp`, `email`, `sms`. |
| `rate_limits` | Map (M) | Yes | Rate limiting configuration values. | See Complex Structures | Currently informational; not enforced by router. |
| `project_status` | String | Yes | Current status (`active` or `inactive`). Only `active` projects can process requests. | `"active"` |  |
| `company_rep` | Map (M) | No | Optional company representatives information. | See Complex Structures |  |
| `ai_config` | Map (M) | No | Optional OpenAI-specific configuration. | See Complex Structures |  |
| `channel_config` | Map (M) | Yes | Channel-specific configurations (at least one channel config must match `allowed_channels`). | See Complex Structures |  |
| `created_at` | String | Yes | ISO 8601 timestamp of item creation. | `"2023-10-27T10:00:00Z"` | Set on creation. |
| `updated_at` | String | Yes | ISO 8601 timestamp of last update. | `"2023-10-27T10:00:00Z"` | Updated on modification. |

## Complex Attribute Structures

### `rate_limits` (Map)
Defines throttling parameters.
```json
{
  "requests_per_minute": {"N": "60"},
  "requests_per_day": {"N": "2000"},
  "concurrent_conversations": {"N": "30"},
  "max_message_length": {"N": "4096"}
}
```
*Note: These limits are currently informational and included in the context object but **not enforced** by the Channel Router.* Enforcement relies on API Gateway usage plans.

### `company_rep` (Map)
Stores optional contact information for up to 5 company representatives.
```json
{
  "company_rep_1": {"S": "Carol"},
  "company_rep_2": {"NULL": true},
  "company_rep_3": {"NULL": true},
  "company_rep_4": {"NULL": true},
  "company_rep_5": {"NULL": true}
}
```
*Note: Include all keys (`company_rep_1` to `company_rep_5`), setting the value to `{"NULL": true}` if not used.* 

### `ai_config` (Map)
Contains configuration for OpenAI assistants and channel-specific API keys.
```json
{
  "openai_config": {
    "M": {
      "whatsapp": {
        "M": {
          "api_key_reference": {"S": "openai-api-key/whatsapp"},
          "assistant_id_template_sender": {"S": "asst_..."},
          "assistant_id_replies": {"S": "asst_..."},
          "assistant_id_3": {"S": ""},
          "assistant_id_4": {"S": ""},
          "assistant_id_5": {"S": ""}
        }
      },
      "sms": {
        "M": {
          "api_key_reference": {"S": "openai-api-key/sms"},
          "assistant_id_template_sender": {"S": "asst_..."},
          "assistant_id_replies": {"S": "asst_..."},
          "assistant_id_3": {"S": ""},
          "assistant_id_4": {"S": ""},
          "assistant_id_5": {"S": ""}
        }
      },
      "email": {
        "M": {
          "api_key_reference": {"S": "openai-api-key/email"},
          "assistant_id_template_sender": {"S": "asst_..."},
          "assistant_id_replies": {"S": "asst_..."},
          "assistant_id_3": {"S": ""},
          "assistant_id_4": {"S": ""},
          "assistant_id_5": {"S": ""}
        }
      }
    }
  }
}
```
- The top-level `ai_config` map now contains an `openai_config` map.
- The `openai_config` map contains nested maps for each channel (`whatsapp`, `sms`, `email`).
- Each channel map contains:
    - `api_key_reference`: Path/name of the secret in AWS Secrets Manager holding the **channel-specific** OpenAI API key.
    - `assistant_id_*`: Holds the relevant OpenAI Assistant IDs used for this channel.

### `channel_config` (Map)
Contains nested configuration maps for each potential communication channel. At least one channel configuration matching an entry in `allowed_channels` must be present.

```json
{
  "whatsapp": { // Required if "whatsapp" is in allowed_channels
    "M": {
      "company_whatsapp_number": {"S": "+447588713814"}, 
      "whatsapp_credentials_id": {"S": "whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio"} 
      // --- Optional WhatsApp fields ---
      // "whatsapp_template_namespace": {"S": "your_namespace"}, 
      // "whatsapp_business_account_id": {"S": "1234567890"}, 
      // "default_language": {"S": "en_GB"}
    }
  },
  "email": {    // Required if "email" is in allowed_channels
    "M": {
      "company_email": {"S": "replies@cucumber-recruitment.com"}, 
      "email_credentials_id": {"S": "email-credentials/cucumber-recruitment/cv-analysis/sendgrid"}, 
      "message_id": {"S": "example-cv-clarification-email"}, // Added based on context_builder
      // --- Optional Email fields ---
      // "email_from_name": {"S": "Recruitment Team"}, 
      // "default_subject_line": {"S": "Regarding Your Application"} 
    }
  },
  "sms": {      // Required if "sms" is in allowed_channels
    "M": {
      "company_sms_number": {"S": "+447700900444"}, 
      "sms_credentials_id": {"S": "sms-credentials/cucumber-recruitment/cv-analysis/twilio"} 
      // --- Optional SMS fields ---
      // "sms_provider": {"S": "twilio"} 
    }
  }
}
```
**Notes on `channel_config`:**
- Phone numbers (`company_whatsapp_number`, `company_sms_number`) **must** be stored with the international prefix (e.g., `+44`). The `context_builder` removes the `+` only for the `conversation_id` generation.
- Fields ending in `_id` or `_reference` typically store the name/path of a secret in AWS Secrets Manager containing the actual credentials.
- Include configuration blocks only for channels the project might use (even if not currently in `allowed_channels`).
- The specific required fields within each channel block depend on what the downstream channel-specific processing engines need. The examples show common fields.
