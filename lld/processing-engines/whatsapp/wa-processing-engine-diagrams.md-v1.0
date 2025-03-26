# WhatsApp Processing Engine - System Diagrams

> **Diagrams and Visual References for the WhatsApp Processing Engine**

## 1. System Architecture Overview

```mermaid
flowchart LR
    CR[Channel Router] --> SQS[WhatsApp SQS Queue]
    SQS --> WPE[WhatsApp Processing Engine]
    WPE --> DDB[(DynamoDB\nConversations)]
    WPE --> OAI[OpenAI API]
    OAI --> TWI[Twilio API]
    TWI --> EU[End User]
    WPE -.-> SM[AWS Secrets Manager]
    SM -.-> OAI
    SM -.-> TWI
    
    subgraph Flow
    direction TB
    f1[1. Create conversation record]
    f2[2. Update status to processing]
    f3[3. Update with OpenAI results]
    f4[4. Retrieve credentials]
    f5[5. Update with final status]
    end
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
    S1[SQS Message\nConsumption] --> S2[Create\nConversation\nRecord]
    S2 --> S3[Process with\nOpenAI]
    S3 --> S4[Send Template\nvia Twilio]
    S4 --> S5[Update Final\nStatus]
```

## 3. SQS Heartbeat Pattern

```mermaid
flowchart TD
    SQS[SQS Queue] --> LF[Lambda Function]
    LF --> PM[Process Message]
    PM --> HB[Start Heartbeat Timer]
    HB --> PO[Process OpenAI\n(Long-running)]
    PO --> Success{Success?}
    
    PO --> EV[Every 5 minutes:\nExtend Visibility\nTimeout]
    EV --> PO
    
    Success -->|Yes| CH[Clear Heartbeat\nDelete Message]
    Success -->|No| CE[Clear Heartbeat\nRe-throw Error\n(SQS will retry)]
```

## 4. Credential Management Flow

```mermaid
flowchart LR
    CO[Context Object\nwith Reference] --> SM[AWS Secrets\nManager]
    SM --> CRED[API\nCredentials]
    CRED --> INIT[API Client\nInitialization]
```

## 5. OpenAI Integration Flow

```mermaid
flowchart LR
    CT[Create OpenAI\nThread] --> AM[Add Context\nas Message]
    AM --> CR[Create Run\nwith Assistant]
    CR --> PR[Poll Run\nUntil Complete]
    PR --> PJ[Parse JSON\nResponse]
    PJ --> ECV[Extract\nContent Vars]
```

## 6. Template Message Sending Flow

```mermaid
flowchart LR
    GWC[Get WhatsApp\nCredentials] --> ITC[Initialize\nTwilio Client]
    ITC --> STM[Send Template\nMessage]
    STM --> UC[Update\nConversation]
```

## 7. Error Handling Strategy

```mermaid
flowchart TD
    EO[Error Occurs] --> CE[Categorize Error]
    CE --> DET[Determine Error Type]
    
    DET --> TE[Transient Error]
    DET --> PE[Permanent Error]
    DET --> CE1[Configuration Error]
    
    TE --> RWB[Retry with Backoff]
    PE --> SD[Send to DLQ\nLog Details]
    CE1 --> AOT[Alert Ops Team\nUpdate Status\nin DynamoDB]
    
    RWB --> MR{Max Retries?}
    MR -->|Yes| SD2[Send to DLQ]
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
    SM[System Metrics\n& Logs] --> CW[CloudWatch\nLogs & Metrics]
    CW --> CD[CloudWatch\nDashboards]
    CD --> CA[CloudWatch\nAlarms]
    CD --> SN[SNS\nNotifications]
```

## 10. OpenAI Run Polling Loop

```mermaid
flowchart TD
    CR[Create Run] --> GRS[Get Run Status]
    GRS --> SC{Status = queued,\nin_progress,\nor cancelling?}
    SC -->|Yes| WB[Wait with Backoff]
    WB --> GRS
    SC -->|No| CMP{Status =\ncompleted?}
    CMP -->|Yes| GAR[Get Assistant Response]
    GAR --> PJ[Parse JSON &\nExtract Vars]
    CMP -->|No| HE[Handle Error]
```

## 11. Alarm Notification Flow

```mermaid
flowchart LR
    CWA[CloudWatch\nAlarm] --> SNS[SNS Topic]
    SNS --> NOT[Email/SMS\nNotification]
```

## 12. DynamoDB Conversation Record Schema

```mermaid
classDiagram
    class ConversationRecord {
        +String recipient_tel (Partition Key)
        +String conversation_id (Sort Key) 
        +String company_id
        +String project_id
        +String channel_method
        +String company_whatsapp_number
        +String conversation_status
        +String thread_id
        +Message[] messages
        +String request_id
        +Boolean task_complete
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
    }
    
    ConversationRecord "1" *-- "many" Message : contains
```

## 13. Exponential Backoff for API Calls

```mermaid
flowchart TD
    API[API Call] --> SC{Success?}
    SC -->|Yes| RR[Return Result]
    SC -->|No| RE{Retryable\nError?}
    RE -->|No| TE[Throw Error]
    RE -->|Yes| MRE{Max Retries\nExceeded?}
    MRE -->|Yes| TE2[Throw Error]
    MRE -->|No| CD[Calculate Delay\nwith Backoff+Jitter]
    CD --> WAIT[Wait]
    WAIT --> RAC[Retry API Call]
    RAC --> API
```

## 14. Adaptive Rate Limiting for API Calls

```mermaid
flowchart TD
    REQ[API Request\nInitiated] --> TA{Tokens\nAvailable?}
    TA -->|No| WFR[Wait for\nRefill]
    WFR --> CT
    TA -->|Yes| CT[Consume Token\nMake API Call]
    CT --> CARH[Check API\nResponse\nHeaders]
    CARH --> ARD[Adapt Rate\nBased on Data]
```

## 15. Circuit Breaker Pattern

```mermaid
flowchart TD
    REQ[API Request] --> CO{Circuit\nOpen?}
    CO -->|Yes| FF[Fail Fast]
    CO -->|No| CHO{Circuit\nHalf Open?}
    CHO -->|Yes| ASR[Allow Single\nTest Request]
    CHO -->|No| MAC[Make API Call]
    ASR --> MAC
    MAC --> CS{Call\nSuccessful?}
    CS -->|Yes| RSC[Record Success\nClose Circuit]
    CS -->|No| RF[Record Failure]
    RF --> OCT[Open Circuit if\nThreshold Met]
``` 