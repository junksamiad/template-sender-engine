# WhatsApp AI Chatbot - Architecture Diagrams v2.0

This document contains the latest visual representations of the WhatsApp AI chatbot architecture, with updated diagrams that reflect the current implementation of the Channel Router and related components.

## 1. System Overview

```mermaid
graph TD
    FE[Frontend Applications] -->|Send Payload| Router[Channel Router]
    Router -->|Authenticate & Validate| Router
    Router -->|Create Context Object| Router
    Router -->|Place in Queue| Queues[(Message Queues)]
    
    Queues -->|WhatsApp Messages| WhatsAppEngine[WhatsApp Engine]
    Queues -->|Email Messages| EmailEngine[Email Engine]
    Queues -->|SMS Messages| SMSEngine[SMS Engine]
    
    WhatsAppEngine -->|Process Request| Twilio[Twilio API]
    EmailEngine -->|Process Request| EmailSvc[Email Service]
    SMSEngine -->|Process Request| SMSSvc[SMS Service]
    
    WhatsAppEngine -.->|Failed Messages| DLQ[(Dead Letter Queues)]
    EmailEngine -.->|Failed Messages| DLQ
    SMSEngine -.->|Failed Messages| DLQ
    
    subgraph "AWS Cloud"
        Router
        Queues
        DLQ
        WhatsAppEngine
        EmailEngine
        SMSEngine
        
        subgraph "Storage & Security"
            CompanyDB[(DynamoDB<br/>wa_company_data)]
            ConvoDB[(DynamoDB<br/>wa_conversation)]
            MessageProcDB[(DynamoDB<br/>message_processing)]
            DLQDB[(DynamoDB<br/>dlq_messages)]
            SecretsManager[AWS Secrets Manager]
        end
        
        subgraph "External Services Integration"
            OpenAI[OpenAI Assistants API]
        end
        
        subgraph "Monitoring"
            CloudWatch[CloudWatch]
            DLQDashboard[DLQ Dashboard]
            Alarms[CloudWatch Alarms]
        end
        
        Router -->|Query Company/Project| CompanyDB
        Router -->|Get API Key| SecretsManager
        
        WhatsAppEngine -->|Update Conversation| ConvoDB
        WhatsAppEngine -->|Update Processing Status| MessageProcDB
        WhatsAppEngine -->|Create Thread| OpenAI
        OpenAI -->|Function Call| WhatsAppEngine
        
        SecretsManager -.->|Provide Secrets| WhatsAppEngine
        SecretsManager -.->|Provide Secrets| EmailEngine
        SecretsManager -.->|Provide Secrets| SMSEngine
        
        Router -.->|Logs & Metrics| CloudWatch
        WhatsAppEngine -.->|Logs & Metrics| CloudWatch
        EmailEngine -.->|Logs & Metrics| CloudWatch
        SMSEngine -.->|Logs & Metrics| CloudWatch
        
        DLQ -.->|Failed Messages| DLQDB
        DLQ -.->|Monitoring| DLQDashboard
        DLQ -.->|Alerts| Alarms
        Router -.->|Alerts| Alarms
    end
    
    Twilio -->|Send WhatsApp Message| User((End User))
    EmailSvc -->|Send Email| User
    SMSSvc -->|Send SMS| User
    User -->|Reply| Twilio
    
    style FE fill:#f9f,stroke:#333,stroke-width:2px
    style Router fill:#D6A2E8,stroke:#333,stroke-width:2px
    style Queues fill:#F5B041,stroke:#333,stroke-width:2px
    style DLQ fill:#E74C3C,stroke:#333,stroke-width:2px
    style WhatsAppEngine fill:#85C1E9,stroke:#333,stroke-width:2px
    style EmailEngine fill:#85C1E9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style SMSEngine fill:#85C1E9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style CompanyDB fill:#F8C471,stroke:#333,stroke-width:2px
    style ConvoDB fill:#F8C471,stroke:#333,stroke-width:2px
    style MessageProcDB fill:#F8C471,stroke:#333,stroke-width:2px
    style DLQDB fill:#F8C471,stroke:#333,stroke-width:2px
    style OpenAI fill:#7DCEA0,stroke:#333,stroke-width:2px
    style Twilio fill:#C39BD3,stroke:#333,stroke-width:2px
    style EmailSvc fill:#C39BD3,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style SMSSvc fill:#C39BD3,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style User fill:#5D6D7E,stroke:#333,stroke-width:2px,color:#fff
    style CloudWatch fill:#AED6F1,stroke:#333,stroke-width:2px
    style DLQDashboard fill:#AED6F1,stroke:#333,stroke-width:2px
    style Alarms fill:#F5B7B1,stroke:#333,stroke-width:2px
    style SecretsManager fill:#D6EAF8,stroke:#333,stroke-width:2px
```

## 2. Enhanced Channel Router Architecture

```mermaid
graph TD
    subgraph "Frontend Applications"
        FA1["Recruitment Agency"]
        FA2["IVA Company"]
        FA3["Other Clients"]
    end
    
    subgraph "Channel Router"
        APIG["API Gateway<br/>(Rate Limit: 10 req/sec<br/>Burst Limit: 20)"]
        
        subgraph "Router Lambda (Timeout: 30s)"
            VAL["Request Validation"]
            AUTH["Authentication"]
            CONTEXT["Context Object Creation"]
            ROUTE["Channel Routing"]
        end
    end
    
    subgraph "Message Queues"
        WQ["WhatsApp Queue<br/>(Visibility: 600s)"]
        EQ["Email Queue<br/>(Visibility: 600s)"]
        SQ["SMS Queue<br/>(Visibility: 600s)"]
        
        WDLQ["WhatsApp DLQ<br/>(Retention: 14 days)"]
        EDLQ["Email DLQ<br/>(Retention: 14 days)"]
        SDLQ["SMS DLQ<br/>(Retention: 14 days)"]
    end
    
    subgraph "Processing Engines"
        WL["WhatsApp Lambda<br/>(Timeout: 900s)"]
        EL["Email Lambda<br/>(Timeout: 900s)"]
        SL["SMS Lambda<br/>(Timeout: 900s)"]
        
        HB["Heartbeat Pattern<br/>(300s intervals)"]
    end
    
    subgraph "Storage & Security"
        DDB["wa_company_data<br/>(On-Demand Capacity)"]
        PITR["Point-in-Time Recovery"]
        SM["Secrets Manager"]
    end
    
    subgraph "Monitoring"
        CW["CloudWatch"]
        DLQM["DLQ Dashboard"]
        ALARMS["CloudWatch Alarms"]
    end
    
    FA1 --> APIG
    FA2 --> APIG
    FA3 --> APIG
    
    APIG --> VAL
    VAL --> AUTH
    AUTH --> CONTEXT
    CONTEXT --> ROUTE
    
    AUTH <--> DDB
    AUTH <--> SM
    CONTEXT <--> DDB
    
    ROUTE --> WQ
    ROUTE --> EQ
    ROUTE --> SQ
    
    WQ --> WL
    EQ --> EL
    SQ --> SL
    
    WL --> HB
    EL --> HB
    SL --> HB
    
    WQ -.-> WDLQ
    EQ -.-> EDLQ
    SQ -.-> SDLQ
    
    DDB --> PITR
    
    APIG -.-> CW
    VAL -.-> CW
    AUTH -.-> CW
    ROUTE -.-> CW
    WL -.-> CW
    EL -.-> CW
    SL -.-> CW
    
    WDLQ -.-> DLQM
    EDLQ -.-> DLQM
    SDLQ -.-> DLQM
    
    DLQM -.-> ALARMS
    CW -.-> ALARMS
    
    style FA1 fill:#f9f,stroke:#333,stroke-width:2px
    style FA2 fill:#f9f,stroke:#333,stroke-width:2px
    style FA3 fill:#f9f,stroke:#333,stroke-width:2px
    style APIG fill:#D6A2E8,stroke:#333,stroke-width:2px
    style VAL fill:#D6A2E8,stroke:#333,stroke-width:2px
    style AUTH fill:#D6A2E8,stroke:#333,stroke-width:2px
    style CONTEXT fill:#D6A2E8,stroke:#333,stroke-width:2px
    style ROUTE fill:#D6A2E8,stroke:#333,stroke-width:2px
    style WQ fill:#F5B041,stroke:#333,stroke-width:2px
    style EQ fill:#F5B041,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style SQ fill:#F5B041,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style WDLQ fill:#E74C3C,stroke:#333,stroke-width:2px
    style EDLQ fill:#E74C3C,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style SDLQ fill:#E74C3C,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style WL fill:#85C1E9,stroke:#333,stroke-width:2px
    style EL fill:#85C1E9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style SL fill:#85C1E9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style HB fill:#85C1E9,stroke:#333,stroke-width:2px
    style DDB fill:#F8C471,stroke:#333,stroke-width:2px
    style PITR fill:#F8C471,stroke:#333,stroke-width:2px
    style SM fill:#D6EAF8,stroke:#333,stroke-width:2px
    style CW fill:#AED6F1,stroke:#333,stroke-width:2px
    style DLQM fill:#AED6F1,stroke:#333,stroke-width:2px
    style ALARMS fill:#F5B7B1,stroke:#333,stroke-width:2px
```

## 3. Context Object Creation and Flow

```mermaid
sequenceDiagram
    participant Client as Frontend Client
    participant APIG as API Gateway
    participant Router as Router Lambda
    participant DDB as DynamoDB
    participant SM as Secrets Manager
    participant Queue as Channel Queue
    participant Lambda as Channel Lambda
    participant OpenAI as OpenAI API
    participant Twilio as Twilio API
    participant User as End User
    participant DLQ as Dead Letter Queue
    
    Client->>APIG: POST /router (payload)
    Note over APIG: Rate Limit: 10 req/sec<br/>Burst Limit: 20
    APIG->>Router: Forward request
    
    Router->>Router: Validate request structure
    
    Router->>DDB: Query company/project record
    DDB-->>Router: Return company configuration
    
    Router->>SM: Get API key using reference
    SM-->>Router: Return API key
    
    Router->>Router: Authenticate & validate constraints
    
    Router->>Router: Create context object with:<br/>1. Original frontend payload<br/>2. Company configuration<br/>3. Channel config references<br/>4. AI configuration<br/>5. Metadata
    
    Router->>Queue: Place context object in channel queue
    Queue-->>Router: Acknowledge message receipt
    
    Router-->>APIG: Return success response
    APIG-->>Client: Forward success response
    
    Note over Client: Frontend flow complete
    
    Queue->>Lambda: Trigger Lambda (batch size: 1)
    Note over Lambda: Visibility Timeout: 600s
    
    Lambda->>Lambda: Extract channel config from context
    
    Lambda->>SM: Get channel credentials using reference
    SM-->>Lambda: Return channel credentials
    
    Lambda->>OpenAI: Process with OpenAI API
    
    Note over Lambda: After 300 seconds (5 min)
    Lambda->>Queue: Extend Visibility Timeout (+600s)
    Queue-->>Lambda: Acknowledge Extension
    
    OpenAI-->>Lambda: Return response
    
    Lambda->>Twilio: Send message via Twilio
    Twilio-->>Lambda: Confirm delivery
    
    Lambda->>Queue: Delete message
    Queue-->>Lambda: Acknowledge deletion
    
    Twilio->>User: Deliver message
    
    Note over Queue,DLQ: If processing fails after 3 attempts
    Queue->>DLQ: Move message to DLQ
    Note over DLQ: Retention: 14 days
```

## 4. Authentication and Security Flow

```mermaid
flowchart TD
    subgraph "Request Processing"
        REQ["Incoming Request"]
        HEADER["Authorization Header"]
        PAYLOAD["Request Payload"]
    end
    
    subgraph "Authentication Process"
        EXTRACT["Extract API Key"]
        QUERY["Query wa_company_data"]
        FETCH["Fetch from Secrets Manager"]
        COMPARE["Compare Keys"]
        VALIDATE["Validate Constraints"]
    end
    
    subgraph "DynamoDB"
        COMPANY["Company Record<br/>(On-Demand Capacity)"]
        KEY_REF["API Key Reference"]
        CHANNELS["Allowed Channels"]
        RATE["Rate Limits"]
        STATUS["Account Status"]
    end
    
    subgraph "Secrets Manager"
        SECRET["Stored API Key"]
        ROTATION["90-day Rotation Policy"]
        AUDIT["Audit Logging"]
    end
    
    subgraph "Validation Checks"
        CHANNEL_CHECK["Channel Allowed Check"]
        RATE_CHECK["Rate Limit Check"]
        STATUS_CHECK["Account Status Check"]
    end
    
    subgraph "Result"
        SUCCESS["Authentication Success"]
        FAILURE["Authentication Failure"]
    end
    
    REQ --> HEADER
    REQ --> PAYLOAD
    HEADER --> EXTRACT
    
    EXTRACT --> QUERY
    QUERY --> COMPANY
    COMPANY --> KEY_REF
    COMPANY --> CHANNELS
    COMPANY --> RATE
    COMPANY --> STATUS
    
    KEY_REF --> FETCH
    FETCH --> SECRET
    SECRET --> COMPARE
    
    CHANNELS --> CHANNEL_CHECK
    RATE --> RATE_CHECK
    STATUS --> STATUS_CHECK
    
    COMPARE --> VALIDATE
    CHANNEL_CHECK --> VALIDATE
    RATE_CHECK --> VALIDATE
    STATUS_CHECK --> VALIDATE
    
    VALIDATE --> SUCCESS
    VALIDATE --> FAILURE
    
    SECRET --> ROTATION
    SECRET --> AUDIT
    
    style REQ fill:#f9f,stroke:#333,stroke-width:2px
    style COMPANY fill:#F8C471,stroke:#333,stroke-width:2px
    style SECRET fill:#D6EAF8,stroke:#333,stroke-width:2px
    style ROTATION fill:#D6EAF8,stroke:#333,stroke-width:2px
    style AUDIT fill:#D6EAF8,stroke:#333,stroke-width:2px
    style SUCCESS fill:#7DCEA0,stroke:#333,stroke-width:2px
    style FAILURE fill:#E74C3C,stroke:#333,stroke-width:2px
    style CHANNEL_CHECK fill:#D6A2E8,stroke:#333,stroke-width:2px
    style RATE_CHECK fill:#D6A2E8,stroke:#333,stroke-width:2px 
    style STATUS_CHECK fill:#D6A2E8,stroke:#333,stroke-width:2px
```

## 5. Context Object Structure

```mermaid
classDiagram
    class ContextObject {
        +frontend_payload
        +db_payload
        +project_rate_limits
        +channel_config
        +ai_config
        +metadata
    }
    
    class FrontendPayload {
        +company_data
        +recipient_data
        +project_data
        +request_data
    }
    
    class DatabasePayload {
        +company_id
        +project_id
        +company_name
        +project_name
        +project_status
        +allowed_channels
    }
    
    class ProjectRateLimits {
        +requests_per_minute
        +requests_per_day
        +concurrent_conversations
        +max_message_length
    }
    
    class ChannelConfig {
        +whatsapp
        +sms
        +email
    }
    
    class AIConfig {
        +assistant_id_template_sender
        +assistant_id_replies
        +assistant_id_3
        +assistant_id_4
        +assistant_id_5
    }
    
    class Metadata {
        +context_creation_timestamp
        +router_version
        +request_id
    }
    
    ContextObject --* FrontendPayload
    ContextObject --* DatabasePayload
    ContextObject --* ProjectRateLimits
    ContextObject --* ChannelConfig
    ContextObject --* AIConfig
    ContextObject --* Metadata
```

## 6. Enhanced DLQ Management System

```mermaid
flowchart TD
    subgraph "Message Processing"
        MSG["Message with Context Object"]
        PROC["Processing"]
        FAIL["Failure"]
        RETRY["Retry (max 3)"]
    end
    
    subgraph "Dead Letter Queue System"
        WDLQ["WhatsApp DLQ"]
        EDLQ["Email DLQ"]
        SDLQ["SMS DLQ"]
        RETAIN["Retention: 14 days"]
        DLQDB["DLQ Messages DynamoDB Table"]
    end
    
    subgraph "Monitoring & Alerting"
        DASH["DLQ Dashboard"]
        METRICS["DLQ Metrics"]
        ALARM["CloudWatch Alarms<br/>(Threshold: 1 message)"]
        NOTIFY["Operations Team Notification"]
    end
    
    subgraph "Investigation & Recovery"
        VIEW["View Message Contents"]
        LOGS["Access CloudWatch Logs"]
        PATTERN["Identify Failure Patterns"]
        REPROCESS["Reprocess Message"]
        DOC["Document Common Failures"]
    end
    
    MSG --> PROC
    PROC --> FAIL
    FAIL --> RETRY
    RETRY --> PROC
    
    RETRY -- "After 3 failures" --> WDLQ
    RETRY -- "After 3 failures" --> EDLQ
    RETRY -- "After 3 failures" --> SDLQ
    
    WDLQ --> DLQDB
    EDLQ --> DLQDB
    SDLQ --> DLQDB
    
    WDLQ --> RETAIN
    EDLQ --> RETAIN
    SDLQ --> RETAIN
    
    DLQDB --> DASH
    
    DASH --> METRICS
    METRICS --> ALARM
    ALARM --> NOTIFY
    
    NOTIFY --> VIEW
    VIEW --> LOGS
    LOGS --> PATTERN
    PATTERN --> REPROCESS
    PATTERN --> DOC
    REPROCESS --> MSG
    
    style MSG fill:#f9f,stroke:#333,stroke-width:2px
    style PROC fill:#85C1E9,stroke:#333,stroke-width:2px
    style FAIL fill:#E74C3C,stroke:#333,stroke-width:2px
    style RETRY fill:#F5B041,stroke:#333,stroke-width:2px
    style WDLQ fill:#E74C3C,stroke:#333,stroke-width:2px
    style EDLQ fill:#E74C3C,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style SDLQ fill:#E74C3C,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style RETAIN fill:#E74C3C,stroke:#333,stroke-width:2px
    style DLQDB fill:#F8C471,stroke:#333,stroke-width:2px
    style DASH fill:#AED6F1,stroke:#333,stroke-width:2px
    style METRICS fill:#AED6F1,stroke:#333,stroke-width:2px
    style ALARM fill:#F5B7B1,stroke:#333,stroke-width:2px
    style NOTIFY fill:#F5B7B1,stroke:#333,stroke-width:2px
    style VIEW fill:#7DCEA0,stroke:#333,stroke-width:2px
    style LOGS fill:#7DCEA0,stroke:#333,stroke-width:2px
    style PATTERN fill:#7DCEA0,stroke:#333,stroke-width:2px
    style REPROCESS fill:#7DCEA0,stroke:#333,stroke-width:2px
    style DOC fill:#7DCEA0,stroke:#333,stroke-width:2px
```

## 7. Heartbeat Pattern for Long-Running Operations

```mermaid
sequenceDiagram
    participant Lambda as Channel Lambda
    participant Queue as SQS Queue
    participant OpenAI as OpenAI API
    participant Twilio as Twilio API
    
    Lambda->>Queue: Receive Message
    Queue-->>Lambda: Message with Visibility Timeout (600s)
    
    Lambda->>Lambda: Extract Context Object
    
    Lambda->>OpenAI: Process with OpenAI API
    
    Note over Lambda: Heartbeat Timer Starts
    
    Note over Lambda: After 300 seconds (5 min)
    Lambda->>Queue: Extend Visibility Timeout (+600s)
    Queue-->>Lambda: Acknowledge Extension
    
    OpenAI-->>Lambda: Response (delayed)
    
    Note over Lambda: If still processing after another 300s
    Lambda->>Queue: Extend Visibility Timeout Again (+600s)
    Queue-->>Lambda: Acknowledge Extension
    
    Lambda->>Twilio: Send message via Twilio
    Twilio-->>Lambda: Confirm delivery
    
    Lambda->>Lambda: Complete Processing
    Lambda->>Queue: Delete Message
    Queue-->>Lambda: Acknowledge Deletion
    
    Note over Lambda: Timeout: 900s (Maximum allowed for Lambda)
```

## 8. Database Schema Overview

```mermaid
erDiagram
    COMPANY_DATA {
        string company_id PK
        string project_id SK
        string company_name
        string project_name
        string api_key_reference
        array allowed_channels
        object rate_limits
        object concurrent_conversations
        string status
        object openai_config
        object channel_config
        string created_at
        string updated_at
    }
    
    CONVERSATIONS {
        string phone_number PK
        string conversation_id SK
        string company_id FK
        string project_id FK
        string channel_method
        string company_channel_id
        string account_sid
        string thread_id
        object user_data
        object content_data
        object company_data
        array messages
        string conversation_status
        string last_user_message_at
        string last_system_message_at
        string created_at
        string updated_at
    }
    
    MESSAGE_PROCESSING {
        string request_id PK
        string channel_method
        string processing_status
        number retry_count
        string company_id FK
        string project_id FK
        object payload
        object error_details
        string created_at
        string updated_at
        string last_processed_at
        string visibility_timeout_expires_at
    }
    
    DLQ_MESSAGES {
        string request_id PK
        string original_queue SK
        string channel_method
        string failure_reason
        number attempt_count
        string company_id FK
        string project_id FK
        object payload
        object error_details
        string created_at
        string first_failure_at
        string last_failure_at
    }
    
    COMPANY_DATA ||--o{ CONVERSATIONS : "has"
    COMPANY_DATA ||--o{ MESSAGE_PROCESSING : "has"
    COMPANY_DATA ||--o{ DLQ_MESSAGES : "has"
``` 