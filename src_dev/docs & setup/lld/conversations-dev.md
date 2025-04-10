# `conversations-dev` DynamoDB Schema

This document defines the schema for the `conversations-dev` DynamoDB table, which stores conversation state and history for the AI multi-channel communications platform development environment.

## Table Purpose

The `conversations-dev` table serves as the state machine and historical record for each communication initiated through the platform in the development environment. It tracks:
- Individual conversation details and identifiers.
- The current status of the conversation (e.g., processing, sent, failed).
- Message history between the AI/system and the recipient.
- References to external system identifiers (e.g., OpenAI thread IDs).
- Metadata related to processing and configuration.

## Primary Keys

- **Physical Partition Key (PK)**: `primary_channel` (String) - This single attribute stores the primary identifier for the recipient based on the channel.
- **Physical Sort Key (SK)**: `conversation_id` (String) - Unique identifier for the conversation, generated by the Channel Router (e.g., `ci-aaa-001#pi-aaa-001#req123#447123456789`).

**Logical Key Structure (Implemented in Application Code):**
- If `channel_method` is `whatsapp` or `sms`, the `primary_channel` attribute is populated with the value from `recipient_tel`.
- If `channel_method` is `email`, the `primary_channel` attribute is populated with the value from `recipient_email`.

**Primary Channel Derivation Logic:**
The value for `primary_channel` is determined by the application code (specifically within `src_dev/channel-processor/whatsapp/lambda/services/dynamodb_service.py`) before writing the record:
*   If `channel_method` (from the Context Object) is `whatsapp` or `sms`, the value of `recipient_tel` (from the Context Object) is used.
*   If `channel_method` is `email`, the value of `recipient_email` (from the Context Object) is used.
*   The code includes checks to ensure the required identifier (`recipient_tel` or `recipient_email`) exists for the given `channel_method`.

This structure allows:
- A consistent physical key schema for the table definition.
- Efficient lookups of a specific conversation using the primary channel identifier (`primary_channel`) and the `conversation_id`.
- Querying all conversations associated with a specific primary channel identifier (phone number or email address).

## Attributes Table

| Attribute | Type | Required | Description | Example | Notes |
|---|---|---|---|---|---|
| `primary_channel` | String | Yes | Primary identifier for the recipient (phone for WhatsApp/SMS, email for Email). | `"+447123456789"` or `"j.doe@example.com"` | Physical Partition Key. Value derived from `recipient_tel` or `recipient_email` in application logic. |
| `conversation_id` | String | Yes | Unique conversation identifier. | `"ci-aaa-001#pi-aaa-001#req123#447123456789"` | Physical Sort Key. Created by Channel Router. |
| `recipient_tel` | String | Conditional | Recipient's phone number (international format). Always stored if available. | `"+447123456789"` | Required in Context Object if `channel_method` is `whatsapp` or `sms`. |
| `recipient_email` | String | Conditional | Recipient's email address. Always stored if available. | `"john.doe@example.com"` | Required in Context Object if `channel_method` is `email`. |
| `company_id` | String | Yes | Identifier for the company. | `"ci-aaa-001"` | Copied from Context Object. Used in GSI. |
| `project_id` | String | Yes | Identifier for the project. | `"pi-aaa-001"` | Copied from Context Object. Used in GSI. |
| `channel_method` | String | Yes | Communication channel used. | `"whatsapp"` | Valid values: `whatsapp`, `email`, `sms`. |
| `conversation_status` | String | Yes | Current state of the conversation. | `"processing"`, `"initial_message_sent"`, `"failed"` | Updated by Channel Processor. |
| `request_id` | String | Yes | Original request ID from frontend payload. | `"req123"` | Copied from Context Object. |
| `messages` | List (L) | Yes | List of message maps exchanged. Initialized as empty list `[]`. | See Complex Structures | Appended to by Channel Processor. |
| `created_at` | String | Yes | ISO 8601 timestamp of record creation. | `"2023-11-01T12:00:00Z"` | Set on initial creation. |
| `updated_at` | String | Yes | ISO 8601 timestamp of last update. | `"2023-11-01T12:05:00Z"` | Updated on every modification. |
| `initial_request_timestamp` | String | No | ISO 8601 timestamp from the original frontend request. | `"2023-09-15T11:45:32.789Z"` | Copied from Context Object. Useful for E2E latency tracking. |
| `processor_version` | String | No | Version of the Channel Processor Lambda that processed the message. | `"1.0.0"` | Extracted from Lambda env var. |
| `router_version` | String | No | Version of the Channel Router that created the Context Object. | `"1.0.1-dev"` | Copied from Context Object metadata. |
| `thread_id` | String | No | OpenAI Assistant Thread ID. | `"thread_abc123xyz"` | Populated after OpenAI interaction. |
| `email_id` | String | No | Unique identifier for email thread (e.g., Message-ID). | `"<CAJ=z1q...>` | For future use by Email Processor. Null initially. |
| `task_complete` | Number (N) | Yes | Indicates if the initial processing task is complete (0=false, 1=true). | `0`, `1` | Initialized `0`, set `1` on success. Used for LSI. Stored as Number for LSI key compatibility. |
| `processing_time_ms` | Number (N) | No | Total time taken by Channel Processor Lambda in ms. | `1500` | Populated on task completion. |
| `recipient_first_name` | String | No | Recipient's first name. | `"John"` | Copied from Context Object. |
| `recipient_last_name` | String | No | Recipient's last name. | `"Doe"` | Copied from Context Object. |
| `comms_consent` | Boolean (BOOL) | Yes | Indicates if recipient provided explicit consent. | `true`, `false` | Copied from Context Object. Defaults `false` if missing. |
| `project_data` | Map (M) | No | Arbitrary project-specific data from frontend payload. | `{"job_ref": "JR123"}` | Copied from Context Object. Stored for potential human agent use. |
| `company_name` | String | No | Human-readable company name. | `"Cucumber Recruitment"` | Copied from Context Object. |
| `project_name` | String | No | Human-readable project name. | `"Clarify CV"` | Copied from Context Object. |
| `company_rep` | Map (M) | No | Company representative details. | See `company-data-dev.md` | Copied from Context Object. |
| `allowed_channels` | List (L) | No | List of channels allowed for the project. | `["whatsapp", "email"]` | Copied from Context Object. For future use. |
| `project_status` | String | No | Status of the project. | `"active"` | Copied from Context Object. For future use. |
| `auto_queue_initial_message` | Boolean (BOOL) | No | Routing rule flag. | `false` | Copied from Context Object. For reply handling logic. |
| `auto_queue_initial_message_from_number` | List (L) of Strings | No | Routing rule numbers. | `["+447..."]` | Copied from Context Object. For reply handling logic. |
| `auto_queue_initial_message_from_email` | List (L) of Strings | No | Routing rule emails. | `["support@..."]` | Copied from Context Object. For reply handling logic. |
| `auto_queue_reply_message` | Boolean (BOOL) | No | Routing rule flag. | `true` | Copied from Context Object. For reply handling logic. |
| `auto_queue_reply_message_from_number` | List (L) of Strings | No | Routing rule numbers. | `["+447..."]` | Copied from Context Object. For reply handling logic. |
| `auto_queue_reply_message_from_email` | List (L) of Strings | No | Routing rule emails. | `["agent@..."]` | Copied from Context Object. For reply handling logic. |
| `ai_config` | Map (M) | No | AI configuration details used. | See `company-data-db-dev.md` | Copied from Context Object. Stored for audit/context. |
| `channel_config` | Map (M) | No | Channel configuration details used. | See `company-data-db-dev.md` | Copied from Context Object. Stored for audit/context/future use. |
| `function_call` | Boolean (BOOL) | Yes | Indicates if an AI function call is pending/occurred. | `false`, `true` | Initialized `false`. |
| `function_call_type` | String | No | Type/name of the function call requested by AI. | `"submit_application"` | Initialized null. |
| `hand_off_to_human` | Boolean (BOOL) | Yes | Flag indicating request for human intervention. | `false`, `true` | Initialized `false`. |
| `hand_off_to_human_reason` | String | No | Reason provided by AI for hand-off request. | `"User requested agent"` | Initialized null. |
| `ttl` | Number (N) | No | DynamoDB Time-to-Live attribute (epoch timestamp). | `1678886400` | Optional for auto-deletion. |

## Complex Attribute Structures

### `messages` (List of Maps)
Stores the sequence of interactions within the conversation. Each element in the list is a map.
```json
[
  { // Example AI interaction message entry
    "entry_id": {"S": "uuid-generated-1"},
    "message_timestamp": {"S": "2023-11-01T12:05:00Z"},
    "role": {"S": "assistant"}, // "user" or "assistant"
    "content": {"S": "Hello, this is a message from the AI."},
    "ai_prompt_tokens": {"N": "150"},
    "ai_completion_tokens": {"N": "50"},
    "ai_total_tokens": {"N": "200"},
    "processing_time_ms": {"N": "850"}
  }
  // ... more message maps added chronologically
]
```
- `entry_id`: Unique identifier for this message within the conversation.
- `message_timestamp`: When the message was added/processed.
- `role`: Who sent the message (`user` for incoming/initial prompt, `assistant` for AI response).
- `content`: The text content of the message.
- `ai_*_tokens`: Token counts from OpenAI API interaction.
- `processing_time_ms`: Time taken specifically for this step (e.g., AI call).

### `company_rep` (Map)
See schema definition in `company-data-dev.md`. Copied from the Context Object.

### `ai_config` (Map)
See schema definition in `company-data-db-dev.md`. Copied from the Context Object.

### `channel_config` (Map)
See schema definition in `company-data-db-dev.md`. Copied from the Context Object.

### `project_data` (Map)
Flexible map to store any project-specific key-value pairs passed in the `frontend_payload`.

## Global Secondary Index (GSI)

- **Index Name**: `company-id-project-id-index`
- **Key Schema**:
    - **Partition Key (PK)**: `company_id` (String)
    - **Sort Key (SK)**: `project_id` (String)
- **Projection Type**: `ALL` (All attributes are projected from the table to the index).
- **Provisioned Throughput**: Uses the table's billing mode (`PAY_PER_REQUEST`).

**Purpose**: Allows querying conversations filtered by `company_id` and `project_id`, useful for company/project-level reporting or dashboards.

## Local Secondary Indexes (LSIs)

The following LSIs are defined to support efficient queries within a specific `primary_channel` partition. LSIs must be defined at table creation.

1.  **`created-at-index`**
    *   **Key Schema**:
        *   Partition Key (PK): `primary_channel` (String)
        *   Sort Key (SK): `created_at` (String)
    *   **Projection Type**: `ALL` (Implicitly projects all attributes; queries can fetch any attribute, potentially requiring reads back to the base table if not a key).
    *   **Purpose**: Allows querying conversations for a specific recipient within a date/time range.

2.  **`task-complete-index`**
    *   **Key Schema**:
        *   Partition Key (PK): `primary_channel` (String)
        *   Sort Key (SK): `task_complete` (**Number**) # 0=False, 1=True
    *   **Projection Type**: `ALL`
    *   **Purpose**: Allows efficiently querying conversations for a specific recipient based on whether the initial task is complete (`1`) or not (`0`).
    *   **Note**: The application must map boolean `true` to `1` and `false` to `0` when writing/querying this index key.

3.  **`conversation-status-index`**
    *   **Key Schema**:
        *   Partition Key (PK): `primary_channel` (String)
        *   Sort Key (SK): `conversation_status` (String)
    *   **Projection Type**: `ALL`
    *   **Purpose**: Allows efficiently querying conversations for a specific recipient based on their status (e.g., `processing`, `initial_message_sent`, `failed`).

4.  **`channel-method-index`**
    *   **Key Schema**:
        *   Partition Key (PK): `primary_channel` (String)
        *   Sort Key (SK): `channel_method` (String)
    *   **Projection Type**: `ALL`
    *   **Purpose**: Allows efficiently querying conversations for a specific recipient based on the communication channel used.

## Table Settings

- **Billing Mode**: `PAY_PER_REQUEST` (On-Demand). Recommended for development.
- **Point-in-Time Recovery (PITR)**: Disabled. Recommended for development to save costs.
- **Encryption**: Default AWS owned key (`AWS_OWNED_CMK`). Standard practice.
- **Deletion Protection**: Disabled.
- **Contributor Insights**: Disabled. 