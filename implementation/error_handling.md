# Error Handling Strategies for WhatsApp AI Chatbot

This document outlines error handling strategies for different components of the WhatsApp AI chatbot system.

## Error Handling Flow Diagram

```mermaid
sequenceDiagram
    participant Frontend
    participant API as API Gateway
    participant Lambda
    participant CompanyDB as wa_company_data
    participant ConvoDB as wa_conversations
    participant OpenAI
    participant Twilio
    participant DLQ as Dead Letter Queue
    participant CloudWatch
    
    Frontend->>API: Send payload
    Note over API: Rate limiting<br/>Authentication errors
    
    alt API Gateway Error
        API-->>Frontend: Return 4xx/5xx error
        API->>CloudWatch: Log error details
    else Success
        API->>Lambda: Forward request
        
        Lambda->>CompanyDB: Lookup company config
        
        alt Company Config Not Found
            CompanyDB-->>Lambda: Return empty result
            Lambda->>CloudWatch: Log error
            Lambda-->>API: Return 404 - Company not found
            API-->>Frontend: Return error response
        else Database Error
            CompanyDB-->>Lambda: Throw database exception
            Lambda->>CloudWatch: Log error
            Lambda->>DLQ: Send failed request to DLQ
            Lambda-->>API: Return 500 - Database error
            API-->>Frontend: Return error response
        else Success
            CompanyDB-->>Lambda: Return company configuration
            
            Lambda->>ConvoDB: Create conversation record
            
            alt Database Write Error
                ConvoDB-->>Lambda: Throw database exception
                Lambda->>CloudWatch: Log error
                Lambda->>DLQ: Send failed request to DLQ
                Lambda-->>API: Return 500 - Database error
                API-->>Frontend: Return error response
            else Success
                ConvoDB-->>Lambda: Confirm record creation
                
                Lambda->>OpenAI: Create thread & attach assistant
                
                alt OpenAI API Error
                    OpenAI-->>Lambda: Return API error
                    Lambda->>CloudWatch: Log error details
                    Lambda->>ConvoDB: Update record with error status
                    Lambda-->>API: Return 502 - OpenAI service error
                    API-->>Frontend: Return error response
                else Success
                    OpenAI-->>Lambda: Return thread_id
                    
                    Lambda->>OpenAI: Run assistant
                    
                    alt OpenAI Execution Error
                        OpenAI-->>Lambda: Return execution error
                        Lambda->>CloudWatch: Log error details
                        Lambda->>ConvoDB: Update record with error status
                        Lambda-->>API: Return 502 - OpenAI execution error
                        API-->>Frontend: Return error response
                    else Success
                        OpenAI-->>Lambda: Function calling (send_template_message)
                        
                        Lambda->>Twilio: Send template message
                        
                        alt Twilio API Error
                            Twilio-->>Lambda: Return API error
                            Lambda->>CloudWatch: Log error details
                            Lambda->>ConvoDB: Update record with error status
                            Lambda->>DLQ: Queue message for retry
                            Lambda-->>API: Return 502 - Twilio service error
                            API-->>Frontend: Return error response
                        else Success
                            Twilio-->>Lambda: Confirm message sent
                            
                            Lambda->>ConvoDB: Update conversation record
                            
                            alt Final DB Update Error
                                ConvoDB-->>Lambda: Throw database exception
                                Lambda->>CloudWatch: Log error
                                Note over Lambda: Message already sent, just log error
                                Lambda-->>API: Return 200 with warning
                                API-->>Frontend: Return success with warning
                            else Complete Success
                                ConvoDB-->>Lambda: Confirm record update
                                Lambda-->>API: Return 200 - Success
                                API-->>Frontend: Return success response
                            end
                        end
                    end
                end
            end
        end
    end
```

## Error Handling Strategy by Component

```mermaid
graph TD
    subgraph "API Gateway Errors"
        RateLimit[Rate Limiting Exceeded]
        AuthError[Authentication Failure]
        BadRequest[Malformed Request]
    end
    
    subgraph "Lambda Function Errors"
        Timeout[Lambda Timeout]
        MemoryExceeded[Memory Limit Exceeded]
        CodeError[Code Exception]
    end
    
    subgraph "DynamoDB Errors"
        ProvisionedThroughput[Throughput Exceeded]
        ConditionalCheckFailed[Conditional Check Failed]
        ItemSizeTooLarge[Item Size Too Large]
    end
    
    subgraph "OpenAI API Errors"
        RateLimitExceeded[Rate Limit Exceeded]
        InvalidRequest[Invalid Request]
        ModelOverloaded[Model Overloaded]
    end
    
    subgraph "Twilio API Errors"
        InvalidNumber[Invalid Phone Number]
        TemplateMismatch[Template Parameter Mismatch]
        AccountIssue[Account/Billing Issue]
    end
    
    RateLimit -->|429 Response| RetryWithBackoff[Retry with Exponential Backoff]
    AuthError -->|401 Response| LogAndAlert[Log Error & Alert Admin]
    BadRequest -->|400 Response| ValidateRequest[Validate Request Schema]
    
    Timeout -->|Monitor| AdjustTimeout[Adjust Timeout Settings]
    MemoryExceeded -->|Monitor| IncreaseMemory[Increase Memory Allocation]
    CodeError -->|Try/Catch| FallbackBehavior[Implement Fallback Behavior]
    
    ProvisionedThroughput -->|Retry| AutoScaling[Enable Auto Scaling]
    ConditionalCheckFailed -->|Handle| RetryLogic[Implement Retry Logic]
    ItemSizeTooLarge -->|Redesign| SplitItems[Split Large Items]
    
    RateLimitExceeded -->|Queue| TokenBucket[Implement Token Bucket]
    InvalidRequest -->|Validate| RequestValidation[Validate Before Sending]
    ModelOverloaded -->|Fallback| SimplerModel[Use Simpler Model]
    
    InvalidNumber -->|Validate| NumberValidation[Validate Phone Numbers]
    TemplateMismatch -->|Check| TemplateValidation[Validate Template Parameters]
    AccountIssue -->|Monitor| AccountAlerts[Set Up Account Alerts]
    
    style RetryWithBackoff fill:#f9a,stroke:#333,stroke-width:2px
    style LogAndAlert fill:#f9a,stroke:#333,stroke-width:2px
    style ValidateRequest fill:#f9a,stroke:#333,stroke-width:2px
    style AdjustTimeout fill:#aaf,stroke:#333,stroke-width:2px
    style IncreaseMemory fill:#aaf,stroke:#333,stroke-width:2px
    style FallbackBehavior fill:#aaf,stroke:#333,stroke-width:2px
    style AutoScaling fill:#afa,stroke:#333,stroke-width:2px
    style RetryLogic fill:#afa,stroke:#333,stroke-width:2px
    style SplitItems fill:#afa,stroke:#333,stroke-width:2px
    style TokenBucket fill:#faa,stroke:#333,stroke-width:2px
    style RequestValidation fill:#faa,stroke:#333,stroke-width:2px
    style SimplerModel fill:#faa,stroke:#333,stroke-width:2px
    style NumberValidation fill:#aff,stroke:#333,stroke-width:2px
    style TemplateValidation fill:#aff,stroke:#333,stroke-width:2px
    style AccountAlerts fill:#aff,stroke:#333,stroke-width:2px
```

## Retry Strategy

```mermaid
graph TD
    Error[Error Occurs] --> Classify[Classify Error]
    
    Classify --> Transient{Transient Error?}
    Classify --> Critical{Critical Error?}
    
    Transient -->|Yes| RetryStrategy[Apply Retry Strategy]
    Transient -->|No| NoRetry[No Retry]
    
    Critical -->|Yes| Alert[Alert & Log]
    Critical -->|No| StandardLog[Standard Logging]
    
    RetryStrategy --> ExponentialBackoff[Exponential Backoff]
    RetryStrategy --> Jitter[Add Jitter]
    RetryStrategy --> MaxRetries[Set Max Retries]
    
    ExponentialBackoff --> DLQ{Max Retries<br/>Exceeded?}
    Jitter --> DLQ
    MaxRetries --> DLQ
    
    DLQ -->|Yes| DeadLetterQueue[Send to Dead Letter Queue]
    DLQ -->|No| RetryAttempt[Retry Attempt]
    
    RetryAttempt --> Success{Success?}
    
    Success -->|Yes| ContinueFlow[Continue Normal Flow]
    Success -->|No| BackToRetry[Back to Retry Strategy]
    
    DeadLetterQueue --> ManualReview[Manual Review/Reprocessing]
    DeadLetterQueue --> FallbackAction[Execute Fallback Action]
    
    style Error fill:#f99,stroke:#333,stroke-width:2px
    style RetryStrategy fill:#9f9,stroke:#333,stroke-width:2px
    style ExponentialBackoff fill:#9f9,stroke:#333,stroke-width:2px
    style Jitter fill:#9f9,stroke:#333,stroke-width:2px
    style DeadLetterQueue fill:#f99,stroke:#333,stroke-width:2px
    style ContinueFlow fill:#9f9,stroke:#333,stroke-width:2px
```

## Circuit Breaker Pattern for External Services

```mermaid
stateDiagram-v2
    [*] --> Closed
    
    Closed --> Open: Failure threshold exceeded
    Open --> HalfOpen: Timeout period elapsed
    HalfOpen --> Closed: Success threshold met
    HalfOpen --> Open: Failure occurs
    
    state Closed {
        [*] --> Normal
        Normal --> Counting: Failure occurs
        Counting --> Normal: Success occurs
        Counting --> [*]: Threshold reached
    }
    
    state Open {
        [*] --> Rejecting
        Rejecting --> [*]: Timeout elapses
    }
    
    state HalfOpen {
        [*] --> Testing
        Testing --> [*]: Decision made
    }
```

## Error Monitoring and Alerting

```mermaid
graph TD
    Error[Error Occurs] --> Log[Log to CloudWatch]
    
    Log --> Severity{Severity Level}
    
    Severity -->|Critical| SNS[SNS Topic]
    Severity -->|High| SNS
    Severity -->|Medium| Dashboard[CloudWatch Dashboard]
    Severity -->|Low| Dashboard
    
    SNS --> Email[Email Alert]
    SNS --> SMS[SMS Alert]
    SNS --> Slack[Slack Notification]
    
    Dashboard --> Metrics[Metrics & Alarms]
    
    Metrics --> Threshold{Threshold<br/>Exceeded?}
    
    Threshold -->|Yes| AutoRemediation[Auto-Remediation]
    Threshold -->|Yes| SNS
    
    AutoRemediation --> ScaleUp[Scale Up Resources]
    AutoRemediation --> Failover[Failover to Backup]
    AutoRemediation --> Throttle[Throttle Requests]
    
    style Error fill:#f99,stroke:#333,stroke-width:2px
    style SNS fill:#9af,stroke:#333,stroke-width:2px
    style AutoRemediation fill:#9f9,stroke:#333,stroke-width:2px
``` 