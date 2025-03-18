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
        API["API Gateway"]
        LF["Lambda Function"]
        AUTH["Authentication"]
        VAL["Validation"]
        ROUTE["Routing Logic"]
    end

    subgraph "Message Queues"
        WQ["WhatsApp Queue"]
        EQ["Email Queue"]
        SQ["SMS Queue"]
    end

    subgraph "Processing Engines"
        WPE["WhatsApp Processing"]
        EPE["Email Processing"]
        SPE["SMS Processing"]
    end

    subgraph "Storage & Security"
        DDB["DynamoDB"]
        SM["Secrets Manager"]
    end

    subgraph "Monitoring"
        CW["CloudWatch"]
        DLQ["Dead Letter Queues"]
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
    
    WQ --> WPE
    EQ --> EPE
    SQ --> SPE
    
    WQ -.-> DLQ
    EQ -.-> DLQ
    SQ -.-> DLQ
    
    LF -.-> CW
    DLQ -.-> CW
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
    API->>Router: Forward request
    
    Router->>Router: Validate request structure
    
    Router->>DDB: Query company/project record
    DDB-->>Router: Return record with API key reference
    
    Router->>SM: Get API key
    SM-->>Router: Return API key
    
    Router->>Router: Authenticate & validate constraints
    
    Router->>SM: Get channel-specific secrets
    SM-->>Router: Return secrets (Twilio, OpenAI, etc.)
    
    Router->>Router: Create context object with payload & config
    
    Router->>Queue: Place context object in appropriate channel queue
    Queue-->>Router: Acknowledge message receipt
    
    Router-->>API: Return success response
    API-->>Client: Forward success response
    
    Note over Queue,DLQ: If processing fails after multiple attempts
    Queue->>DLQ: Move message to DLQ
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
        CL["Concurrency Limit: 25"]
        TO["Timeout: 900 seconds"]
        HB["Heartbeat Pattern"]
    end
    
    subgraph "SQS Configuration"
        BS["Batch Size: 1"]
        BW["Batch Window: 0 seconds"]
        VT["Visibility Timeout: 600 seconds"]
    end
    
    subgraph "DynamoDB"
        OD["On-Demand Capacity"]
        PITR["Point-in-Time Recovery"]
    end
    
    subgraph "Monitoring"
        CWA["CloudWatch Alarms"]
        DLQM["DLQ Monitoring"]
    end
    
    Client[Client] --> RL
    RL --> BL
    BL --> TH
    
    TH --> CL
    CL --> TO
    
    TO --> BS
    BS --> BW
    BW --> VT
    VT --> HB
    
    CL -.-> CWA
    TH -.-> CWA
    DLQM -.-> CWA
    
    OD -.-> CWA
    PITR -.-> OD
```

## 4. Authentication Flow

```mermaid
flowchart TD
    subgraph "Request"
        REQ["Incoming Request"]
        HEADER["Authorization Header"]
    end
    
    subgraph "Authentication Process"
        EXTRACT["Extract API Key"]
        QUERY["Query DynamoDB"]
        FETCH["Fetch from Secrets Manager"]
        COMPARE["Compare Keys"]
        VALIDATE["Validate Constraints"]
    end
    
    subgraph "DynamoDB"
        COMPANY["Company Record"]
        KEY_REF["API Key Reference"]
    end
    
    subgraph "Secrets Manager"
        SECRET["Stored API Key"]
    end
    
    subgraph "Result"
        SUCCESS["Authentication Success"]
        FAILURE["Authentication Failure"]
    end
    
    REQ --> HEADER
    HEADER --> EXTRACT
    
    EXTRACT --> QUERY
    QUERY --> COMPANY
    COMPANY --> KEY_REF
    KEY_REF --> FETCH
    FETCH --> SECRET
    SECRET --> COMPARE
    COMPARE --> VALIDATE
    
    VALIDATE --> SUCCESS
    VALIDATE --> FAILURE
```

## 5. Dead Letter Queue Management

```mermaid
flowchart TD
    subgraph "Message Processing"
        MSG["Message"]
        PROC["Processing"]
        FAIL["Failure"]
        RETRY["Retry (max 3)"]
    end
    
    subgraph "Dead Letter Queue"
        DLQ["Dead Letter Queue"]
        RETAIN["Retention: 14 days"]
    end
    
    subgraph "Monitoring & Alerting"
        DASH["DLQ Dashboard"]
        ALARM["CloudWatch Alarm"]
        NOTIFY["Notification"]
    end
    
    subgraph "Investigation & Recovery"
        VIEW["View Message"]
        LOGS["Access Logs"]
        PATTERN["Identify Patterns"]
        REPROCESS["Reprocess Message"]
    end
    
    MSG --> PROC
    PROC --> FAIL
    FAIL --> RETRY
    RETRY --> PROC
    
    RETRY -- "After 3 failures" --> DLQ
    DLQ --> RETAIN
    
    DLQ --> DASH
    DLQ --> ALARM
    ALARM --> NOTIFY
    
    NOTIFY --> VIEW
    VIEW --> LOGS
    LOGS --> PATTERN
    PATTERN --> REPROCESS
    REPROCESS --> MSG
```

## 6. Infrastructure Deployment

```mermaid
flowchart TD
    subgraph "AWS CDK"
        CDK["CDK Stack"]
    end
    
    subgraph "API Resources"
        APIG["API Gateway"]
        THROTTLE["Throttling Config"]
    end
    
    subgraph "Compute Resources"
        LAMBDA["Lambda Function"]
        CONCUR["Concurrency Limit"]
        TIMEOUT["Timeout Config"]
    end
    
    subgraph "Queue Resources"
        WHATSAPP["WhatsApp Queue"]
        EMAIL["Email Queue"]
        SMS["SMS Queue"]
        WDLQ["WhatsApp DLQ"]
        EDLQ["Email DLQ"]
        SDLQ["SMS DLQ"]
    end
    
    subgraph "Storage Resources"
        DYNTABLE["DynamoDB Table"]
        PITR["Point-in-Time Recovery"]
    end
    
    subgraph "Monitoring Resources"
        ALARMS["CloudWatch Alarms"]
        DASHBOARD["CloudWatch Dashboard"]
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
    
    APIG --> THROTTLE
    LAMBDA --> CONCUR
    LAMBDA --> TIMEOUT
    DYNTABLE --> PITR
    
    WHATSAPP --> WDLQ
    EMAIL --> EDLQ
    SMS --> SDLQ
    
    WDLQ --> ALARMS
    EDLQ --> ALARMS
    SDLQ --> ALARMS
    LAMBDA --> ALARMS
    APIG --> ALARMS
```

## 7. Heartbeat Pattern Implementation

```mermaid
sequenceDiagram
    participant Lambda as Lambda Function
    participant Queue as SQS Queue
    participant External as External API (OpenAI)
    
    Lambda->>Queue: Receive Message
    Queue-->>Lambda: Message with Visibility Timeout (600s)
    
    Lambda->>External: Process with External API
    
    Note over Lambda: After 300 seconds (5 min)
    Lambda->>Queue: Extend Visibility Timeout (+600s)
    Queue-->>Lambda: Acknowledge Extension
    
    External-->>Lambda: Response (delayed)
    
    Note over Lambda: If still processing after another 300s
    Lambda->>Queue: Extend Visibility Timeout Again (+600s)
    Queue-->>Lambda: Acknowledge Extension
    
    Lambda->>Lambda: Complete Processing
    Lambda->>Queue: Delete Message
    Queue-->>Lambda: Acknowledge Deletion
``` 