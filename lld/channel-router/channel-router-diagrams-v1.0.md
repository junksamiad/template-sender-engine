# Channel Router - Architecture Diagrams

## 1. High-Level Architecture

```mermaid
flowchart LR
    subgraph "Frontend Applications"
        FA1["Recruitment Agency"]
        FA2["IVA Company"]
        FA3["Other Clients"]
    end

    subgraph "Channel Router"
        API["API Gateway<br/>(Rate Limit: 10 req/sec<br/>Burst Limit: 20)"]
        LF["Router Lambda<br/>(Timeout: 30s)"]
        AUTH["Authentication"]
        VAL["Validation"]
        ROUTE["Routing Logic"]
    end

    subgraph "Message Queues"
        WQ["WhatsApp Queue<br/>(Visibility: 600s)"]
        EQ["Email Queue<br/>(Visibility: 600s)"]
        SQ["SMS Queue<br/>(Visibility: 600s)"]
        
        WDLQ["WhatsApp DLQ<br/>(Retention: 14 days)"]
        EDLQ["Email DLQ<br/>(Retention: 14 days)"]
        SDLQ["SMS DLQ<br/>(Retention: 14 days)"]
    end

    subgraph "Storage & Security"
        DDB["DynamoDB<br/>(wa_company_data)<br/>(On-Demand Capacity)"]
        SM["Secrets Manager<br/>(90-day Rotation)"]
    end

    subgraph "Monitoring"
        CW["CloudWatch"]
        DLQ_DASH["DLQ Dashboard"]
        ALARMS["CloudWatch Alarms"]
    end

    FA1 --> API
    FA2 --> API
    FA3 --> API
    
    API --> LF
    LF --> AUTH
    LF --> VAL
    LF --> ROUTE
    
    AUTH <--> DDB
    AUTH <--> SM
    
    ROUTE --> WQ
    ROUTE --> EQ
    ROUTE --> SQ
    
    WQ -.-> WDLQ
    EQ -.-> EDLQ
    SQ -.-> SDLQ
    
    WDLQ --> DLQ_DASH
    EDLQ --> DLQ_DASH
    SDLQ --> DLQ_DASH
    
    DLQ_DASH --> ALARMS
    
    LF -.-> CW
    DLQ_DASH -.-> CW
    
    style API fill:#D6A2E8,stroke:#333,stroke-width:2px
    style LF fill:#D6A2E8,stroke:#333,stroke-width:2px
    style AUTH fill:#D6A2E8,stroke:#333,stroke-width:2px
    style VAL fill:#D6A2E8,stroke:#333,stroke-width:2px
    style ROUTE fill:#D6A2E8,stroke:#333,stroke-width:2px
    style WQ fill:#F5B041,stroke:#333,stroke-width:2px
    style EQ fill:#F5B041,stroke:#333,stroke-width:2px
    style SQ fill:#F5B041,stroke:#333,stroke-width:2px
    style WDLQ fill:#E74C3C,stroke:#333,stroke-width:2px
    style EDLQ fill:#E74C3C,stroke:#333,stroke-width:2px
    style SDLQ fill:#E74C3C,stroke:#333,stroke-width:2px
    style DDB fill:#F8C471,stroke:#333,stroke-width:2px
    style SM fill:#D6EAF8,stroke:#333,stroke-width:2px
    style CW fill:#AED6F1,stroke:#333,stroke-width:2px
    style DLQ_DASH fill:#AED6F1,stroke:#333,stroke-width:2px
    style ALARMS fill:#F5B7B1,stroke:#333,stroke-width:2px
```

## 2. Request Flow Sequence

```mermaid
sequenceDiagram
    participant Client as Frontend Client
    participant API as API Gateway
    participant Router as Router Lambda
    participant DDB as DynamoDB
    participant SM as Secrets Manager
    participant Queue as Channel Queue
    participant DLQ as Dead Letter Queue
    
    Client->>API: POST /router (payload)
    Note over API: Rate Limit: 10 req/sec<br/>Burst Limit: 20
    API->>Router: Forward request
    
    Router->>Router: Validate request structure
    Note over Router: Timeout: 30s (Router Lambda)
    
    Router->>DDB: Query company/project record
    DDB-->>Router: Return company configuration
    
    Router->>SM: Get API key using reference
    SM-->>Router: Return API key
    
    Router->>Router: Authenticate & validate constraints
    
    Router->>Router: Create context object with:<br/>1. Original frontend payload<br/>2. Company configuration<br/>3. Channel config references<br/>4. AI configuration<br/>5. Metadata
    
    Router->>Queue: Place context object in channel queue
    Queue-->>Router: Acknowledge message receipt
    
    Router-->>API: Return success response
    API-->>Client: Forward success response
    
    Note over Client: Frontend flow complete
    
    Note over Queue,DLQ: If processing fails after 3 attempts
    Queue->>DLQ: Move message to DLQ
    Note over DLQ: Retention: 14 days
```

## 3. Rate Limiting & Concurrency Architecture

```mermaid
flowchart TD
    subgraph "API Gateway"
        RL["Rate Limit: 10 req/sec"]
        BL["Burst Limit: 20 requests"]
        TH["Throttling"]
    end
    
    subgraph "Lambda Function"
        TO["Router Timeout: 30 seconds"]
    end
    
    subgraph "SQS Configuration"
        BS["Batch Size: 1"]
        BW["Batch Window: 0 seconds"]
        VT["Visibility Timeout: 600 seconds"]
        DLQ_RC["DLQ Max Receive Count: 3"]
        DLQ_RET["DLQ Retention: 14 days"]
    end
    
    subgraph "DynamoDB"
        OD["On-Demand Capacity"]
        PITR["Point-in-Time Recovery"]
    end
    
    subgraph "Monitoring"
        CWA["CloudWatch Alarms"]
        DLQM["DLQ Dashboard"]
        DLQA["DLQ Alarms (Threshold: 1)"]
    end
    
    Client[Client] --> RL
    RL --> BL
    BL --> TH
    
    TH --> TO
    
    TO --> BS
    BS --> BW
    BW --> VT
    VT --> DLQ_RC
    DLQ_RC --> DLQ_RET
    
    TO -.-> CWA
    TH -.-> CWA
    DLQM -.-> DLQA
    DLQA -.-> CWA
    
    OD -.-> CWA
    PITR -.-> OD
    
    style RL fill:#D6A2E8,stroke:#333,stroke-width:2px
    style BL fill:#D6A2E8,stroke:#333,stroke-width:2px
    style TH fill:#D6A2E8,stroke:#333,stroke-width:2px
    style TO fill:#D6A2E8,stroke:#333,stroke-width:2px
    style BS fill:#F5B041,stroke:#333,stroke-width:2px
    style BW fill:#F5B041,stroke:#333,stroke-width:2px
    style VT fill:#F5B041,stroke:#333,stroke-width:2px
    style DLQ_RC fill:#F5B041,stroke:#333,stroke-width:2px
    style DLQ_RET fill:#F5B041,stroke:#333,stroke-width:2px
    style OD fill:#F8C471,stroke:#333,stroke-width:2px
    style PITR fill:#F8C471,stroke:#333,stroke-width:2px
    style CWA fill:#AED6F1,stroke:#333,stroke-width:2px
    style DLQM fill:#AED6F1,stroke:#333,stroke-width:2px
    style DLQA fill:#AED6F1,stroke:#333,stroke-width:2px
    style Client fill:#f9f,stroke:#333,stroke-width:2px
```

## 4. Authentication Flow

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

## 5. Dead Letter Queue Management System

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
    
    WDLQ --> RETAIN
    EDLQ --> RETAIN
    SDLQ --> RETAIN
    
    WDLQ --> DASH
    EDLQ --> DASH
    SDLQ --> DASH
    
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
    style EDLQ fill:#E74C3C,stroke:#333,stroke-width:2px
    style SDLQ fill:#E74C3C,stroke:#333,stroke-width:2px
    style RETAIN fill:#E74C3C,stroke:#333,stroke-width:2px
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

## 6. Infrastructure Deployment with CDK

```mermaid
flowchart TD
    subgraph "AWS CDK"
        CDK["Channel Router CDK Stack"]
    end
    
    subgraph "API Resources"
        APIG["API Gateway"]
        THROTTLE["Throttling Config<br/>Rate: 10 req/sec<br/>Burst: 20"]
    end
    
    subgraph "Compute Resources"
        LAMBDA["Router Lambda Function"]
        TIMEOUT["Timeout: 30 seconds"]
    end
    
    subgraph "Queue Resources"
        WHATSAPP["WhatsApp Queue<br/>Visibility: 600s"]
        EMAIL["Email Queue<br/>Visibility: 600s"]
        SMS["SMS Queue<br/>Visibility: 600s"]
        WDLQ["WhatsApp DLQ<br/>Retention: 14 days"]
        EDLQ["Email DLQ<br/>Retention: 14 days"]
        SDLQ["SMS DLQ<br/>Retention: 14 days"]
    end
    
    subgraph "Storage Resources"
        DYNTABLE["wa_company_data Table"]
        PITR["Point-in-Time Recovery"]
        OD["On-Demand Capacity"]
    end
    
    subgraph "Monitoring Resources"
        ALARMS["CloudWatch Alarms"]
        DLQALARMS["DLQ Alarms<br/>(Threshold: 1)"]
        DASHBOARD["CloudWatch Dashboard"]
        DLQDASH["DLQ Dashboard"]
    end
    
    CDK --> APIG
    CDK --> LAMBDA
    CDK --> WHATSAPP
    CDK --> EMAIL
    CDK --> SMS
    CDK --> WDLQ
    CDK --> EDLQ
    CDK --> SDLQ
    CDK --> DYNTABLE
    CDK --> ALARMS
    CDK --> DASHBOARD
    CDK --> DLQALARMS
    CDK --> DLQDASH
    
    APIG --> THROTTLE
    LAMBDA --> TIMEOUT
    DYNTABLE --> PITR
    DYNTABLE --> OD
    
    WHATSAPP --> WDLQ
    EMAIL --> EDLQ
    SMS --> SDLQ
    
    WDLQ --> DLQALARMS
    EDLQ --> DLQALARMS
    SDLQ --> DLQALARMS
    
    style CDK fill:#85C1E9,stroke:#333,stroke-width:2px
    style APIG fill:#D6A2E8,stroke:#333,stroke-width:2px
    style THROTTLE fill:#D6A2E8,stroke:#333,stroke-width:2px
    style LAMBDA fill:#D6A2E8,stroke:#333,stroke-width:2px
    style TIMEOUT fill:#D6A2E8,stroke:#333,stroke-width:2px
    style WHATSAPP fill:#F5B041,stroke:#333,stroke-width:2px
    style EMAIL fill:#F5B041,stroke:#333,stroke-width:2px
    style SMS fill:#F5B041,stroke:#333,stroke-width:2px
    style WDLQ fill:#E74C3C,stroke:#333,stroke-width:2px
    style EDLQ fill:#E74C3C,stroke:#333,stroke-width:2px
    style SDLQ fill:#E74C3C,stroke:#333,stroke-width:2px
    style DYNTABLE fill:#F8C471,stroke:#333,stroke-width:2px
    style PITR fill:#F8C471,stroke:#333,stroke-width:2px
    style OD fill:#F8C471,stroke:#333,stroke-width:2px
    style ALARMS fill:#F5B7B1,stroke:#333,stroke-width:2px
    style DLQALARMS fill:#F5B7B1,stroke:#333,stroke-width:2px
    style DASHBOARD fill:#AED6F1,stroke:#333,stroke-width:2px
    style DLQDASH fill:#AED6F1,stroke:#333,stroke-width:2px
```

## 7. Context Object Structure

```mermaid
classDiagram
    class ContextObject {
        +frontend_payload
        +wa_company_data_payload
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
    
    class WhatsAppConfig {
        +whatsapp_credentials_id
        +company_whatsapp_number
    }
    
    class SMSConfig {
        +sms_credentials_id
        +company_sms_number
    }
    
    class EmailConfig {
        +email_credentials_id
        +company_email
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
    ChannelConfig --* WhatsAppConfig
    ChannelConfig --* SMSConfig
    ChannelConfig --* EmailConfig
```

> **Note**: The diagrams above have been updated to specifically reflect the Channel Router component as described in the channel_router_documentation-v1.0.md file. Key changes include:
> 1. Corrected the Router Lambda timeout to 30 seconds (not 900)
> 2. Added details about API Gateway rate limits (10 req/sec, 20 burst)
> 3. Specified that DLQs have a retention period of 14 days
> 4. Added the DLQ Dashboard monitoring with threshold of 1 message
> 5. Clarified the context object structure
> 6. Removed Processing Engines from the Channel Router diagrams as they're separate components
> 7. Added styling to improve clarity and readability
> 8. Specified the DynamoDB table as wa_company_data with On-Demand Capacity
> 9. Added the 90-day rotation policy for API keys in Secrets Manager 