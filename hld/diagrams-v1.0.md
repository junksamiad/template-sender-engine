# WhatsApp AI Chatbot - Architecture Diagrams v1.0

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

    DLQProc[DLQ Processor]
    DLQ --> DLQProc
    
    subgraph "AWS Cloud"
        Router
        Queues
        DLQ
        DLQProc
        WhatsAppEngine
        EmailEngine
        SMSEngine
        
        subgraph "Storage & Security"
            CompanyDB[(DynamoDB<br/>wa_company_data)]
            ConvoDB[(DynamoDB<br/>conversations)]
            SecretsManager[AWS Secrets Manager]
        end
        
        subgraph "External Services Integration"
            OpenAI[OpenAI Assistants API]
            CircuitBreaker[Circuit Breaker]
        end
        
        subgraph "Monitoring"
            CloudWatch[CloudWatch]
            DLQDashboard[DLQ Dashboard]
            AIConfigDashboard[AI Config Dashboard]
            Alarms[CloudWatch Alarms]
        end
        
        Router -->|Query Company/Project| CompanyDB
        Router -->|Get API Key Reference| CompanyDB
        Router -->|Resolve Reference| SecretsManager
        
        WhatsAppEngine -->|Create/Update Conversation| ConvoDB
        WhatsAppEngine -->|Get Credentials References| SecretsManager
        WhatsAppEngine -->|Creates OpenAI Thread| OpenAI
        WhatsAppEngine -->|Manages API Calls| CircuitBreaker
        CircuitBreaker -->|Protected Calls| OpenAI
        OpenAI -->|Structured JSON Response| WhatsAppEngine
        
        SecretsManager -.->|Provide Secrets| WhatsAppEngine
        SecretsManager -.->|Provide Secrets| EmailEngine
        SecretsManager -.->|Provide Secrets| SMSEngine
        
        Router -.->|Logs & Metrics| CloudWatch
        WhatsAppEngine -.->|Logs & Metrics| CloudWatch
        WhatsAppEngine -.->|AI Config Issues| AIConfigDashboard
        EmailEngine -.->|Logs & Metrics| CloudWatch
        SMSEngine -.->|Logs & Metrics| CloudWatch
        
        DLQProc -->|Update Failed Status| ConvoDB
        DLQProc -.->|Metrics| CloudWatch
        DLQ -.->|Monitoring| DLQDashboard
        DLQ -.->|Alerts| Alarms
        AIConfigDashboard -.->|Alerts| Alarms
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
    style DLQProc fill:#E74C3C,stroke:#333,stroke-width:2px
    style WhatsAppEngine fill:#85C1E9,stroke:#333,stroke-width:2px
    style EmailEngine fill:#85C1E9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style SMSEngine fill:#85C1E9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style CompanyDB fill:#F8C471,stroke:#333,stroke-width:2px
    style ConvoDB fill:#F8C471,stroke:#333,stroke-width:2px
    style CircuitBreaker fill:#7DCEA0,stroke:#333,stroke-width:2px
    style OpenAI fill:#7DCEA0,stroke:#333,stroke-width:2px
    style Twilio fill:#C39BD3,stroke:#333,stroke-width:2px
    style EmailSvc fill:#C39BD3,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style SMSSvc fill:#C39BD3,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style User fill:#5D6D7E,stroke:#333,stroke-width:2px,color:#fff
    style CloudWatch fill:#AED6F1,stroke:#333,stroke-width:2px
    style DLQDashboard fill:#AED6F1,stroke:#333,stroke-width:2px
    style AIConfigDashboard fill:#AED6F1,stroke:#333,stroke-width:2px
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
            VAL["Request Validation<br/>- Schema validation<br/>- Required fields<br/>- Data type checks"]
            AUTH["Authentication<br/>- API key validation<br/>- Reference-based credentials<br/>- Rate limiting"]
            CONTEXT["Context Object Creation<br/>- Frontend payload<br/>- Company config<br/>- Channel references<br/>- AI configuration"]
            ROUTE["Channel Routing<br/>- WhatsApp<br/>- Email<br/>- SMS"]
        end
    end
    
    subgraph "Message Queues"
        WQ["WhatsApp Queue<br/>(Visibility: 600s)"]
        EQ["Email Queue<br/>(Visibility: 600s)"]
        SQ["SMS Queue<br/>(Visibility: 600s)"]
        
        WDLQ["WhatsApp DLQ<br/>(Retention: 14 days)<br/>maxReceiveCount: 3"]
        EDLQ["Email DLQ<br/>(Retention: 14 days)<br/>maxReceiveCount: 3"]
        SDLQ["SMS DLQ<br/>(Retention: 14 days)<br/>maxReceiveCount: 3"]
    end
    
    subgraph "Processing Engines"
        WL["WhatsApp Lambda<br/>(Timeout: 900s)"]
        EL["Email Lambda<br/>(Timeout: 900s)"]
        SL["SMS Lambda<br/>(Timeout: 900s)"]
        
        HB["Heartbeat Pattern<br/>(300s intervals)"]
    end
    
    subgraph "Storage & Security"
        DDB["wa_company_data<br/>(On-Demand Capacity)"]
        CONVODB["conversations<br/>(Channel-specific keys)"]
        SM["Secrets Manager<br/>(Reference-based access)"]
        REF["Reference Format:<br/>{credential_type}/<br/>{company_id}/<br/>{project_id}/<br/>{provider}"]
    end
    
    subgraph "Monitoring"
        CW["CloudWatch"]
        CWMETRICS["Custom Metrics<br/>- OpenAICallDuration<br/>- TokenUsage<br/>- MessageProcessingTime<br/>- ConfigurationIssues"]
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
    SM --- REF
    
    ROUTE --> WQ
    ROUTE --> EQ
    ROUTE --> SQ
    
    WQ --> WL
    EQ --> EL
    SQ --> SL
    
    WL --> HB
    EL --> HB
    SL --> HB
    
    WL --> CONVODB
    EL --> CONVODB
    SL --> CONVODB
    
    WQ -.-> WDLQ
    EQ -.-> EDLQ
    SQ -.-> SDLQ
    
    WL -.-> CW
    WL -.-> CWMETRICS
    EL -.-> CW
    SL -.-> CW
    
    APIG -.-> CW
    VAL -.-> CW
    AUTH -.-> CW
    ROUTE -.-> CW
    
    WDLQ -.-> DLQM
    EDLQ -.-> DLQM
    SDLQ -.-> DLQM
    
    DLQM -.-> ALARMS
    CWMETRICS -.-> ALARMS
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
    style CONVODB fill:#F8C471,stroke:#333,stroke-width:2px
    style REF fill:#F8C471,stroke:#333,stroke-width:2px
    style SM fill:#D6EAF8,stroke:#333,stroke-width:2px
    style CW fill:#AED6F1,stroke:#333,stroke-width:2px
    style CWMETRICS fill:#AED6F1,stroke:#333,stroke-width:2px
    style DLQM fill:#AED6F1,stroke:#333,stroke-width:2px
    style ALARMS fill:#F5B7B1,stroke:#333,stroke-width:2px
```

## 3. Context Object Creation and Flow

```mermaid
sequenceDiagram
    participant Client as Frontend Client
    participant APIG as API Gateway
    participant Router as Router Lambda
    participant CompanyDB as DynamoDB (wa_company_data)
    participant ConvoDb as DynamoDB (conversations)
    participant SM as Secrets Manager
    participant Queue as Channel Queue
    participant Lambda as Channel Lambda
    participant HB as Heartbeat Mechanism
    participant CB as Circuit Breaker
    participant OpenAI as OpenAI API
    participant Twilio as Twilio API
    participant User as End User
    participant DLQ as Dead Letter Queue
    
    Client->>APIG: POST /router (payload)
    Note over APIG: Rate Limit: 10 req/sec<br/>Burst Limit: 20
    APIG->>Router: Forward request
    
    Router->>Router: Validate request structure
    Note over Router: Timeout: 30s (Router Lambda)
    
    Router->>CompanyDB: Query company/project record
    CompanyDB-->>Router: Return company configuration
    
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
    
    Lambda->>Lambda: Generate conversation ID<br/>based on channel type
    Lambda->>ConvoDb: Create conversation record
    ConvoDb-->>Lambda: Confirm creation
    
    Lambda->>Lambda: Extract channel config from context
    
    Lambda->>SM: Get channel credentials using reference
    SM-->>Lambda: Return channel credentials
    
    Lambda->>SM: Get AI API key using reference
    SM-->>Lambda: Return AI API key
    
    Lambda->>CB: Check circuit state
    Note over CB: Circuit Breaker States:<br/>CLOSED: Normal operation<br/>OPEN: No API calls (failing)<br/>HALF_OPEN: Testing recovery
    
    alt Circuit CLOSED
        CB-->>Lambda: Circuit OK, proceed
        
        Lambda->>OpenAI: Create thread & process message
        
        Note over Lambda,HB: After 300 seconds (5 min)
        Lambda->>HB: Check processing duration
        HB->>Queue: Extend Visibility Timeout (+600s)
        Queue-->>HB: Acknowledge Extension
        
        OpenAI-->>Lambda: Return response
        
        Lambda->>Lambda: Parse template variables<br/>from assistant response
        
        Lambda->>Twilio: Send message via Twilio
        Twilio-->>Lambda: Confirm delivery
        
        Lambda->>ConvoDb: Update conversation record<br/>Add message history<br/>Set status to "initial_message_sent"
        ConvoDb-->>Lambda: Confirm update
        
    else Circuit OPEN
        CB-->>Lambda: Circuit OPEN, API unavailable
        Lambda->>ConvoDb: Update conversation status to "processing_failed"
        Lambda->>DLQ: Send to DLQ (system error)
    end
    
    Lambda->>Queue: Delete message if successful
    Queue-->>Lambda: Acknowledge deletion
    
    Twilio->>User: Deliver message
    
    Note over Queue,DLQ: If processing fails after 3 attempts
    Queue->>DLQ: Move message to DLQ
    Note over DLQ: Retention: 14 days
    
    Note over Lambda: Error Handling categorizes errors:<br/>- Transient (network, temporary)<br/>- Permanent (validation, auth)<br/>- System (infrastructure)<br/>- Integration (external services)
```

## 4. Error Handling Strategy

```mermaid
graph TD
    MSG[Message Processing]
    
    MSG -->|Try-Catch| ERR[Error Detected]
    ERR --> CAT[Categorize Error]
    
    CAT -->|Transient Error| TE[Transient Error Handling]
    CAT -->|Permanent Error| PE[Permanent Error Handling]
    CAT -->|System Error| SE[System Error Handling]
    CAT -->|Integration Error| IE[Integration Error Handling]
    
    TE -->|Network, Throttling| RET[Exponential Backoff Retry]
    RET -->|Max Retries<br/>Exceeded| DLQ[Dead Letter Queue]
    
    PE -->|Validation, Auth| LOG[Log Detailed Error]
    PE --> DLQ
    
    SE -->|Infrastructure| CIR[Circuit Breaker Pattern]
    CIR -->|OPEN State| DLQ
    CIR -->|HALF-OPEN| TEST[Test Request]
    TEST -->|Success| RESET[Reset Circuit]
    TEST -->|Failure| CIR
    
    IE -->|OpenAI Issues| AI[OpenAI Error Handling]
    IE -->|Twilio Issues| TWI[Twilio Error Handling]
    
    AI -->|MissingFunctionCall| CMERR[Configuration Metric]
    AI -->|TokenLimits| RETRY[Retry with Adjusted Prompt]
    AI -->|ServiceUnavailable| CIR
    
    TWI -->|InvalidTemplate| LOGT[Log Twilio Error]
    TWI -->|Auth/Credentials| ALCRE[Alert Credential Issue]
    TWI -->|Network/Throttling| RETT[Retry with Backoff]
    
    DLQ --> PROC[DLQ Processor]
    PROC --> UPDATE[Update Conversation Status]
    UPDATE --> METRIC[Emit CloudWatch Metrics]
    METRIC --> ALERT[Trigger Alarms]
    
    LOG --> STRUCT[Structured Error Logging]
    STRUCT --> CONTEXT[Include Context Info]
    CONTEXT --> REDACT[Redact Sensitive Data]
    
    subgraph "Monitoring & Alerting"
        METRIC
        ALERT
        CMERR
        ALCRE
    end
    
    subgraph "Recovery Mechanisms"
        RET
        CIR
        TEST
        RESET
    end
    
    style MSG fill:#85C1E9,stroke:#333,stroke-width:2px
    style ERR fill:#F5B7B1,stroke:#333,stroke-width:2px
    style CAT fill:#F5B7B1,stroke:#333,stroke-width:2px
    style TE fill:#F5B7B1,stroke:#333,stroke-width:2px
    style PE fill:#F5B7B1,stroke:#333,stroke-width:2px
    style SE fill:#F5B7B1,stroke:#333,stroke-width:2px
    style IE fill:#F5B7B1,stroke:#333,stroke-width:2px
    style RET fill:#ABEBC6,stroke:#333,stroke-width:2px
    style CIR fill:#ABEBC6,stroke:#333,stroke-width:2px
    style TEST fill:#ABEBC6,stroke:#333,stroke-width:2px
    style RESET fill:#ABEBC6,stroke:#333,stroke-width:2px
    style DLQ fill:#E74C3C,stroke:#333,stroke-width:2px
    style PROC fill:#E74C3C,stroke:#333,stroke-width:2px
    style UPDATE fill:#F8C471,stroke:#333,stroke-width:2px
    style LOG fill:#D6A2E8,stroke:#333,stroke-width:2px
    style STRUCT fill:#D6A2E8,stroke:#333,stroke-width:2px
    style CONTEXT fill:#D6A2E8,stroke:#333,stroke-width:2px
    style REDACT fill:#D6A2E8,stroke:#333,stroke-width:2px
    style AI fill:#7DCEA0,stroke:#333,stroke-width:2px
    style RETRY fill:#7DCEA0,stroke:#333,stroke-width:2px
    style TWI fill:#C39BD3,stroke:#333,stroke-width:2px
    style LOGT fill:#C39BD3,stroke:#333,stroke-width:2px
    style RETT fill:#C39BD3,stroke:#333,stroke-width:2px
    style METRIC fill:#AED6F1,stroke:#333,stroke-width:2px
    style ALERT fill:#F5B7B1,stroke:#333,stroke-width:2px
    style CMERR fill:#AED6F1,stroke:#333,stroke-width:2px
    style ALCRE fill:#F5B7B1,stroke:#333,stroke-width:2px
```

## 5. AI Assistant Configuration and Flow

```mermaid
graph TD
    subgraph "Business Onboarding"
        BRA[Business Requirements<br/>Analysis]
        TS[Template Design<br/>& Submission]
        SCM[Secrets Manager<br/>Configuration]
        AC[AI Assistant<br/>Configuration]
    end
    
    subgraph "Assistant Setup"
        AD[Assistant Definition]
        SI[System Instructions]
        ACV[Content Variables<br/>Structure Definition]
        TV[Template Variables<br/>Mapping]
        ER[Error Response<br/>Guidelines]
        TST[Test Scenarios]
    end
    
    subgraph "Processing Flow"
        CTX[Context Object]
        TH[Thread Creation]
        MSG[Message Creation]
        RUN[Run Creation]
        POLL[Poll Run Status]
        PARSE[Parse Response]
        VAL[Validate Content<br/>Variables]
        TEMP[Template Population]
    end
    
    subgraph "Configuration Monitoring"
        CM[Configuration<br/>Metrics]
        JSON[JSON Parsing<br/>Metrics]
        VARI[Variable Validation<br/>Metrics]
        DASH[AI Config<br/>Dashboard]
        ALERT[Configuration<br/>Alerts]
    end
    
    BRA --> TS
    TS --> SCM
    SCM --> AC
    
    AC --> AD
    AD --> SI
    SI --> ACV
    SI --> TV
    SI --> ER
    AD --> TST
    
    CTX --> TH
    TH --> MSG
    MSG --> RUN
    RUN --> POLL
    POLL --> PARSE
    PARSE -->|Valid JSON| VAL
    PARSE -->|Invalid JSON| CM
    VAL -->|Valid Variables| TEMP
    VAL -->|Invalid Variables| VARI
    
    CM --> DASH
    JSON --> DASH
    VARI --> DASH
    DASH --> ALERT
    
    style BRA fill:#F9E79F,stroke:#333,stroke-width:2px
    style TS fill:#F9E79F,stroke:#333,stroke-width:2px
    style SCM fill:#F9E79F,stroke:#333,stroke-width:2px
    style AC fill:#F9E79F,stroke:#333,stroke-width:2px
    
    style AD fill:#7DCEA0,stroke:#333,stroke-width:2px
    style SI fill:#7DCEA0,stroke:#333,stroke-width:2px
    style ACV fill:#7DCEA0,stroke:#333,stroke-width:2px
    style TV fill:#7DCEA0,stroke:#333,stroke-width:2px
    style ER fill:#7DCEA0,stroke:#333,stroke-width:2px
    style TST fill:#7DCEA0,stroke:#333,stroke-width:2px
    
    style CTX fill:#85C1E9,stroke:#333,stroke-width:2px
    style TH fill:#85C1E9,stroke:#333,stroke-width:2px
    style MSG fill:#85C1E9,stroke:#333,stroke-width:2px
    style RUN fill:#85C1E9,stroke:#333,stroke-width:2px
    style POLL fill:#85C1E9,stroke:#333,stroke-width:2px
    style PARSE fill:#85C1E9,stroke:#333,stroke-width:2px
    style VAL fill:#85C1E9,stroke:#333,stroke-width:2px
    style TEMP fill:#85C1E9,stroke:#333,stroke-width:2px
    
    style CM fill:#AED6F1,stroke:#333,stroke-width:2px
    style JSON fill:#AED6F1,stroke:#333,stroke-width:2px
    style VARI fill:#AED6F1,stroke:#333,stroke-width:2px
    style DASH fill:#AED6F1,stroke:#333,stroke-width:2px
    style ALERT fill:#F5B7B1,stroke:#333,stroke-width:2px
```

## 6. Business Onboarding Process

```mermaid
graph TD
    START[Business Onboarding<br/>Request]
    
    subgraph "Initial Phase"
        BRA[Business Requirements<br/>Analysis]
        UC[Use Case Definition]
        TR[Template Requirements]
        DR[Data Requirements]
        CF[Conversation Flow]
    end
    
    subgraph "Twilio & WhatsApp Setup"
        TA[Twilio Account Setup]
        WA[WhatsApp Business<br/>Connection]
        TD[Template Drafting]
        TS[Template Submission]
        TA[Template Approval]
    end
    
    subgraph "Database & Security Configuration"
        DBE[Create Company/Project<br/>Entry in DynamoDB]
        API[Generate API Key]
        SMC[Store Credentials in<br/>Secrets Manager]
        REF[Configure References<br/>in DynamoDB]
    end
    
    subgraph "AI Configuration"
        AIC[Create OpenAI Assistant]
        SI[Define System Instructions]
        FM[Template Function<br/>Mapping]
        AT[Assistant Testing]
    end
    
    subgraph "Frontend & Deployment"
        FE[Frontend Development]
        IT[Integration Testing]
        LT[Load Testing]
        DEPLOY[Deployment]
    end
    
    subgraph "Post-Deployment"
        MON[Monitoring Setup]
        ALERT[Configure Alerts]
        DOCS[Documentation<br/>& Handover]
        TRAIN[Client Training]
    end
    
    START --> BRA
    BRA --> UC
    BRA --> TR
    BRA --> DR
    BRA --> CF
    
    UC --> TA
    TR --> TD
    TD --> TS
    TS --> TA
    
    TA --> DBE
    TA --> API
    API --> SMC
    SMC --> REF
    
    TA --> AIC
    DR --> SI
    CF --> FM
    AIC --> AT
    SI --> AT
    FM --> AT
    
    DBE --> FE
    REF --> FE
    AT --> IT
    FE --> IT
    IT --> LT
    LT --> DEPLOY
    
    DEPLOY --> MON
    MON --> ALERT
    DEPLOY --> DOCS
    DOCS --> TRAIN
    
    style START fill:#F9E79F,stroke:#333,stroke-width:2px
    style BRA fill:#F9E79F,stroke:#333,stroke-width:2px
    style UC fill:#F9E79F,stroke:#333,stroke-width:2px
    style TR fill:#F9E79F,stroke:#333,stroke-width:2px
    style DR fill:#F9E79F,stroke:#333,stroke-width:2px
    style CF fill:#F9E79F,stroke:#333,stroke-width:2px
    
    style TA fill:#C39BD3,stroke:#333,stroke-width:2px
    style WA fill:#C39BD3,stroke:#333,stroke-width:2px
    style TD fill:#C39BD3,stroke:#333,stroke-width:2px
    style TS fill:#C39BD3,stroke:#333,stroke-width:2px
    
    style DBE fill:#F8C471,stroke:#333,stroke-width:2px
    style API fill:#F8C471,stroke:#333,stroke-width:2px
    style SMC fill:#D6EAF8,stroke:#333,stroke-width:2px
    style REF fill:#D6EAF8,stroke:#333,stroke-width:2px
    
    style AIC fill:#7DCEA0,stroke:#333,stroke-width:2px
    style SI fill:#7DCEA0,stroke:#333,stroke-width:2px
    style FM fill:#7DCEA0,stroke:#333,stroke-width:2px
    style AT fill:#7DCEA0,stroke:#333,stroke-width:2px
    
    style FE fill:#D6A2E8,stroke:#333,stroke-width:2px
    style IT fill:#D6A2E8,stroke:#333,stroke-width:2px
    style LT fill:#D6A2E8,stroke:#333,stroke-width:2px
    style DEPLOY fill:#D6A2E8,stroke:#333,stroke-width:2px
    
    style MON fill:#AED6F1,stroke:#333,stroke-width:2px
    style ALERT fill:#F5B7B1,stroke:#333,stroke-width:2px
    style DOCS fill:#85C1E9,stroke:#333,stroke-width:2px
    style TRAIN fill:#85C1E9,stroke:#333,stroke-width:2px
``` 