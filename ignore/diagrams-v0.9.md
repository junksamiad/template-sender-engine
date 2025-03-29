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
            ConvoDB[(DynamoDB<br/>conversations)]
            MessageProcDB[(DynamoDB<br/>message_processing<br/><i>Future Enhancement</i>)]
            DLQDB[(DynamoDB<br/>dlq_messages<br/><i>Monitoring Component</i>)]
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
        WhatsAppEngine -.->|Update Processing Status<br/><i>Future Enhancement</i>| MessageProcDB
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
    style MessageProcDB fill:#F8C471,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style DLQDB fill:#F8C471,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
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
    Note over Router: Timeout: 30s (Router Lambda)
    
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
    Note over Lambda: Timeout: 900s (Processing Lambda)<br/>Visibility Timeout: 600s
    
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