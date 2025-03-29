# Context Object Implementation

This document describes the implementation details of the Context Object created by the Channel Router and passed to the channel-specific queues for processing in the AI Multi-Communications Engine.

## Overview

The Context Object serves as a comprehensive package containing:

1. The original request payload from the frontend
2. Company and project configuration from the DynamoDB database
3. Channel-specific configuration and credentials
4. AI service configuration and credentials
5. Metadata for tracking and debugging
6. Conversation reference data for downstream processing

This approach eliminates the need for downstream services to query the database again, providing all necessary information in one place.

## Implementation Details

The Context Object implementation consists of three main components:

1. **Models**: Data classes defining the structure of the Context Object and its subcomponents
2. **Serialization**: Utilities for serializing and deserializing Context Objects to and from JSON
3. **Validation**: Functions for validating Context Objects to ensure they contain all required fields

### Module Structure

```
src/shared/context/
├── __init__.py             # Module exports
├── models.py               # Context Object data models
├── serialization.py        # Serialization utilities
└── validation.py           # Validation functions
```

### Models

The models are implemented as Python dataclasses, with the main `ContextObject` class containing nested dataclasses for each component:

```python
@dataclass
class ContextObject:
    frontend_payload: FrontendPayload
    wa_company_data_payload: WaCompanyDataPayload
    project_rate_limits: ProjectRateLimits
    channel_config: ChannelConfig
    ai_config: AIConfigContext
    conversation_data: ConversationData
    metadata: Metadata
```

For channel-specific configurations, a `ChannelConfig` class contains optional configurations for each channel:

```python
@dataclass
class ChannelConfig:
    whatsapp: Optional[WhatsAppConfig] = None
    sms: Optional[SMSConfig] = None
    email: Optional[EmailConfig] = None
```

The Context Object provides helper methods for common operations:

- `get_channel_method()`: Get the channel method from the frontend payload
- `get_active_channel_config()`: Get the configuration for the active channel
- `get_credentials_reference()`: Get the credentials reference for the active channel

### Serialization

Serialization utilities convert Context Objects to and from JSON strings:

- `serialize_context(context)`: Converts a Context Object to a JSON string
- `deserialize_context(json_str)`: Converts a JSON string to a Context Object

The serialization process handles special cases like datetime objects, converting them to ISO format strings.

### Validation

Validation functions ensure that Context Objects contain all required fields and that data is in the correct format:

- `validate_context(context)`: Validates the entire Context Object
- Various component-specific validation functions

The validation includes checks for:

- Required fields
- Valid formats for phone numbers, emails, UUIDs, etc.
- Valid credential references
- Channel-specific validation based on the active channel

## Sample Usage

### Creating a Context Object

```python
context = ContextObject(
    frontend_payload=FrontendPayload(
        company_data=CompanyData(
            company_id="cucumber-recruitment",
            project_id="cv-analysis"
        ),
        recipient_data=RecipientData(
            recipient_first_name="John",
            recipient_last_name="Doe",
            recipient_tel="+447700900123",
            recipient_email="john.doe@example.com",
            comms_consent=True
        ),
        request_data=RequestData(
            request_id=str(uuid.uuid4()),
            channel_method=ChannelMethod.WHATSAPP,
            initial_request_timestamp=datetime.now().isoformat()
        ),
        project_data=ProjectData(
            job_title="Software Engineer",
            job_description="We are looking for a skilled software engineer...",
            application_deadline="2023-07-30T23:59:59Z"
        )
    ),
    wa_company_data_payload=WaCompanyDataPayload(
        company_name="Cucumber Recruitment Ltd",
        project_name="CV Analysis Bot",
        project_status="active",
        allowed_channels=["whatsapp", "email"],
        company_rep=CompanyRep(
            company_rep_1="Carol",
            company_rep_2="Mark"
        )
    ),
    project_rate_limits=ProjectRateLimits(
        requests_per_minute=100,
        requests_per_day=10000,
        concurrent_conversations=50,
        max_message_length=4096
    ),
    channel_config=ChannelConfig(
        whatsapp=WhatsAppConfig(
            whatsapp_credentials_id="whatsapp-credentials/cucumber-recruitment/cv-analysis/twilio",
            company_whatsapp_number="+14155238886"
        )
    ),
    ai_config=AIConfigContext(
        assistant_id_template_sender="asst_Ds59ylP35Pn84pasJQVglC2Q",
        assistant_id_replies="asst_Ds59ylP35Pn84pesJQVglC2Q",
        ai_api_key_reference="ai-api-key/global/global/global"
    ),
    conversation_data=ConversationData(
        conversation_id="cucumber-recruitment#cv-analysis#550e8400-e29b-41d4-a716-446655440000#14155238886"
    ),
    metadata=Metadata(
        router_version="1.0.0",
        created_at=datetime.now().isoformat()
    )
)
```

### Serializing and Deserializing

```python
# Serialize to JSON string
json_str = serialize_context(context)

# Deserialize from JSON string
context = deserialize_context(json_str)
```

### Validating

```python
# Validate the context object
errors = validate_context(context)
if errors:
    raise ValueError(f"Context validation failed: {errors}")
```

### Accessing Active Channel Configuration

```python
# Get the active channel method
channel_method = context.get_channel_method()

# Get the configuration for the active channel
channel_config = context.get_active_channel_config()

# Get the credentials reference for the active channel
credentials_ref = context.get_credentials_reference()
```

## Testing

The Context Object implementation includes comprehensive unit tests that verify:

1. Object creation with all required fields
2. Serialization and deserialization
3. Helper methods for channel-specific operations
4. Validation of valid and invalid objects

## Integration with Other Components

The Context Object is designed to integrate with the following components:

1. **Channel Router**: Creates the initial Context Object from frontend payload and database queries
2. **SQS Queues**: Transmits the serialized Context Object to channel-specific processors
3. **Channel Processors**: Deserialize and use the Context Object for processing
4. **Monitoring**: Use metadata from the Context Object for tracking and debugging

## Future Enhancements

Potential future enhancements to the Context Object implementation:

1. **Schema Versioning**: Add version information to handle schema changes
2. **Partial Updates**: Support for partial updates to Context Objects during processing
3. **Compression**: Add support for compressing large Context Objects
4. **Custom Validation Rules**: Allow for company/project-specific validation rules 