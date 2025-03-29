# WhatsApp Processing Engine - System Diagrams

> **Diagrams and Visual References for the WhatsApp Processing Engine**

## 1. System Architecture Overview

```mermaid
flowchart LR
    CR[Channel Router] --> SQS[WhatsApp SQS Queue]
    SQS --> WPE[WhatsApp Processing Engine]
    WPE --> DDB[(DynamoDB<br>Conversations)]
    WPE --> OAI[OpenAI API]
    OAI --> TWI[Twilio API]
    TWI --> EU[End User]
    WPE -.-> SM[AWS Secrets Manager]
    SM -.-> OAI
    SM -.-> TWI
    
    %% Process Steps Note
    classDef noteClass fill:#ffffde,stroke:#aaaa33,stroke-width:1px
    NOTE[Process Steps:<br>1. Create conversation record<br>2. Update status to processing<br>3. Update with OpenAI results<br>4. Retrieve credentials<br>5. Update with final status]
    class NOTE noteClass
```

Process flow:
1. Create conversation record in DynamoDB with status "received"
2. Update conversation status to "processing"
3. Update conversation with OpenAI processing results
4. Retrieve API credentials from Secrets Manager when needed:
   - For OpenAI API access before AI processing
   - For Twilio API access before message delivery
5. Update conversation with final status after delivery

## 2. Message Processing Flow

```mermaid
flowchart LR
    S1["SQS Message<br>Consumption"] --> S2["Create<br>Conversation<br>Record"]
    S2 --> S3["Process with<br>OpenAI"]
    S3 --> S4["Send Template<br>via Twilio"]
    S4 --> S5["Update Final<br>Status"]
```

## 3. SQS Heartbeat Pattern

```mermaid
flowchart TD
    SQS["SQS Queue"] --> LF["Lambda Function"]
    LF --> PM["Process Message"]
    PM --> HB["Start Heartbeat Timer"]
    HB --> PO["Process OpenAI<br>(Long-running)"]
    PO --> Success{"Success?"}
    
    PO --> EV["Every 5 minutes:<br>Extend Visibility<br>Timeout"]
    EV --> PO
    
    Success -->|Yes| CH["Clear Heartbeat<br>Delete Message"]
    Success -->|No| CE["Clear Heartbeat<br>Re-throw Error<br>(SQS will retry)"]
```

## 4. Credential Management Flow

```mermaid
flowchart LR
    CO["Context Object<br>with Reference"] --> SM["AWS Secrets<br>Manager"]
    SM --> CRED["API<br>Credentials"]
    CRED --> INIT["API Client<br>Initialization"]
```

## 5. OpenAI Integration Flow

```mermaid
flowchart LR
    CT["Create OpenAI<br>Thread"] --> AM["Add Context<br>as Message"]
    AM --> CR["Create Run<br>with Assistant"]
    CR --> PR["Poll Run<br>Until Complete"]
    PR --> PJ["Parse JSON<br>Response"]
    PJ --> ECV["Extract<br>Content Vars"]
```

## 6. Template Message Sending Flow

```mermaid
flowchart LR
    GWC["Get WhatsApp<br>Credentials"] --> ITC["Initialize<br>Twilio Client"]
    ITC --> STM["Send Template<br>Message"]
    STM --> UC["Update<br>Conversation"]
```

## 7. Error Handling Strategy

```mermaid
flowchart TD
    EO["Error Occurs"] --> CE["Categorize Error"]
    CE --> DET["Determine Error Type"]
    
    DET --> TE["Transient Error"]
    DET --> PE["Permanent Error"]
    DET --> CE1["Configuration Error"]
    
    TE --> RWB["Retry with Backoff"]
    PE --> SD["Send to DLQ<br>Log Details"]
    CE1 --> AOT["Alert Ops Team<br>Update Status<br>in DynamoDB"]
    
    RWB --> MR{"Max Retries?"}
    MR -->|Yes| SD2["Send to DLQ"]
    MR -->|No| RAC["Retry API Call"]
    RAC --> EO
```

## 8. Conversation Status Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Received
    Received --> Processing
    Processing --> InitialMessageSent: Message sent successfully
    Processing --> Failed: Processing error
    Received --> Failed: Initial error
    InitialMessageSent --> Failed: Delivery error
```

## 9. Monitoring & Observability Architecture

```mermaid
flowchart LR
    SM["System Metrics<br>& Logs"] --> CW["CloudWatch<br>Logs & Metrics"]
    CW --> CD["CloudWatch<br>Dashboards"]
    CD --> CA["CloudWatch<br>Alarms"]
    CD --> SN["SNS<br>Notifications"]
```

## 10. OpenAI Run Polling Loop

```mermaid
flowchart TD
    CR["Create Run"] --> GRS["Get Run Status"]
    GRS --> SC{"Status = queued,<br>in_progress,<br>or cancelling?"}
    SC -->|Yes| WB["Wait with Backoff"]
    WB --> GRS
    SC -->|No| CMP{"Status =<br>completed?"}
    CMP -->|Yes| GAR["Get Assistant Response"]
    GAR --> PJ["Parse JSON &<br>Extract Vars"]
    CMP -->|No| HE["Handle Error"]
```

## 11. Alarm Notification Flow

```mermaid
flowchart LR
    CWA["CloudWatch<br>Alarm"] --> SNS["SNS Topic"]
    SNS --> NOT["Email/SMS<br>Notification"]
```

## 12. DynamoDB Conversation Record Schema

```mermaid
classDiagram
    class ConversationRecord {
        +String recipient_tel (Partition Key)
        +String conversation_id (Sort Key) 
        +String company_id
        +String project_id
        +String company_name
        +String project_name
        +Map company_rep
        +String channel_method
        +String company_whatsapp_number
        +String request_id
        +String router_version
        +String whatsapp_credentials_reference
        +String sms_credentials_reference
        +String email_credentials_reference
        +String thread_id
        +String conversation_status
        +Message[] messages
        +Boolean task_complete
        +String recipient_first_name
        +String recipient_last_name
        +Boolean comms_consent
        +Map project_data
        +Map ai_config
        +Number processing_time_ms
        +String created_at
        +String updated_at
    }
    
    class Message {
        +String entry_id
        +String message_timestamp
        +String role
        +String content
        +Number ai_prompt_tokens
        +Number ai_completion_tokens
        +Number ai_total_tokens
        +Number processing_time_ms
    }
    
    class CompanyRep {
        +String company_rep_1
        +String company_rep_2
        +String company_rep_3
        +String company_rep_4
        +String company_rep_5
    }
    
    class AIConfig {
        +String assistant_id_template_sender
        +String assistant_id_replies
        +String assistant_id_3
        +String assistant_id_4
        +String assistant_id_5
        +String ai_api_key_reference
    }
    
    ConversationRecord "1" *-- "many" Message : contains
    ConversationRecord "1" *-- "1" CompanyRep : contains
    ConversationRecord "1" *-- "1" AIConfig : contains
```

## 13. Exponential Backoff for API Calls

```mermaid
flowchart TD
    API["API Call"] --> SC{"Success?"}
    SC -->|Yes| RR["Return Result"]
    SC -->|No| RE{"Retryable<br>Error?"}
    RE -->|No| TE["Throw Error"]
    RE -->|Yes| MRE{"Max Retries<br>Exceeded?"}
    MRE -->|Yes| TE2["Throw Error"]
    MRE -->|No| CD["Calculate Delay<br>with Backoff+Jitter"]
    CD --> WAIT["Wait"]
    WAIT --> RAC["Retry API Call"]
    RAC --> API
```

## 14. Adaptive Rate Limiting for API Calls

```mermaid
flowchart TD
    REQ["API Request<br>Initiated"] --> TA{"Tokens<br>Available?"}
    TA -->|No| WFR["Wait for<br>Refill"]
    WFR --> CT
    TA -->|Yes| CT["Consume Token<br>Make API Call"]
    CT --> CARH["Check API<br>Response<br>Headers"]
    CARH --> ARD["Adapt Rate<br>Based on Data"]
```

## 15. Circuit Breaker Pattern

```mermaid
flowchart TD
    REQ["API Request"] --> CO{"Circuit<br>Open?"}
    CO -->|Yes| FF["Fail Fast"]
    CO -->|No| CHO{"Circuit<br>Half Open?"}
    CHO -->|Yes| ASR["Allow Single<br>Test Request"]
    CHO -->|No| MAC["Make API Call"]
    ASR --> MAC
    MAC --> CS{"Call<br>Successful?"}
    CS -->|Yes| RSC["Record Success<br>Close Circuit"]
    CS -->|No| RF["Record Failure"]
    RF --> OCT["Open Circuit if<br>Threshold Met"]
``` 