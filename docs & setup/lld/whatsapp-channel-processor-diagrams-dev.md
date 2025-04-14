# WhatsApp Channel Processor - Diagrams

This document provides supplementary diagrams visualizing the data flows, structure, and interactions related to the WhatsApp Channel Processor Lambda (`whatsapp-channel-processor-dev`).

## 1. High-Level System Architecture (Development)

This diagram shows the main AWS services and external APIs involved in Part B (WhatsApp Channel Processor).

```mermaid
graph TD
    subgraph "AWS SQS (Queue - Dev)"
        SQS_W[ai-multi-comms-whatsapp-queue-dev]
    end

    subgraph "AWS Lambda (whatsapp-channel-processor-dev)"
        LambdaFunc[whatsapp-channel-processor-dev]
    end

    subgraph "AWS DynamoDB (conversations-dev)"
        DynamoConv[conversations-dev Table]
    end

    subgraph "AWS Secrets Manager"
        SecretsMan[Secrets Manager]
    end

    subgraph "External Services"
        OpenAI[OpenAI Assistants API]
        Twilio[Twilio WhatsApp API]
    end

    subgraph "AWS CloudWatch"
        CWLogs[Logs]
        CWMetrics[Metrics]
        CWAlarms[Alarms]
        SNS[ai-comms-critical-alerts-dev]
    end

    SQS_W -- Triggers --> LambdaFunc
    LambdaFunc -- Reads/Writes --> DynamoConv
    LambdaFunc -- Reads Secrets --> SecretsMan
    LambdaFunc -- Calls --> OpenAI
    LambdaFunc -- Calls --> Twilio
    LambdaFunc -- Writes Logs --> CWLogs
    CWLogs -- Metric Filter --> CWMetrics
    CWMetrics -- Evaluated by --> CWAlarms
    CWAlarms -- Sends Notification --> SNS
```

## 2. Detailed Sequence Diagram (Single Message Processing)

This diagram details the internal processing steps for a single SQS message received by the Lambda.

```mermaid
sequenceDiagram
    participant SQS
    participant Lambda [whatsapp-channel-processor-dev]
    participant HeartbeatThread
    participant DynamoDB [conversations-dev]
    participant SecretsManager
    participant OpenAI
    participant Twilio
    participant CloudWatch

    SQS->>+Lambda: SQS Event (Contains Message Record)
    Lambda->>Lambda: Parse Context Object from Body
    Lambda->>Lambda: Validate Context Object
    Lambda->>+HeartbeatThread: Start Heartbeat (receiptHandle)
    HeartbeatThread-->>Lambda: Heartbeat Started
    Lambda->>+DynamoDB: PutItem (Initial Record, Condition: attribute_not_exists(conversation_id))
    DynamoDB-->>-Lambda: Success or ConditionalCheckFailedException
    Lambda->>+SecretsManager: GetSecretValue (OpenAI Ref)
    SecretsManager-->>-Lambda: OpenAI Key
    Lambda->>+SecretsManager: GetSecretValue (Twilio Ref)
    SecretsManager-->>-Lambda: Twilio Credentials
    Lambda->>+OpenAI: Create/Run Assistant Thread
    OpenAI-->>-Lambda: AI Response
    Lambda->>+Twilio: Send WhatsApp Message
    Twilio-->>-Lambda: Success/Failure (Message SID)
    Lambda->>+DynamoDB: UpdateItem (Final Status, History, Thread ID)
    alt Final DB Update Fails
        Lambda->>Lambda: Log CRITICAL Error
        Lambda->>+CloudWatch: Log Event -> Metric -> Alarm -> SNS
        CloudWatch-->>-Lambda: (Error Logged)
        DynamoDB-->>-Lambda: Update Failure
        Lambda->>-HeartbeatThread: Stop Heartbeat
        Lambda-->>SQS: Return batchItemFailures (incl. this messageId)
    else Final DB Update Succeeds
        DynamoDB-->>-Lambda: Update Success
        Lambda->>-HeartbeatThread: Stop Heartbeat
        Lambda-->>-SQS: Success (AWS deletes message)
    end

```

## 3. SQS Heartbeat Mechanism

This diagram illustrates the operation of the SQS heartbeat utility.

```mermaid
sequenceDiagram
    participant LambdaHandler [index.lambda_handler]
    participant SQSHeartbeat [utils.sqs_heartbeat.SQSHeartbeat]
    participant BackgroundThread
    participant SQS_API [AWS SQS API]

    LambdaHandler->>SQSHeartbeat: Instantiate (queue_url, receipt_handle, interval, visibility_timeout)
    LambdaHandler->>SQSHeartbeat: start()
    SQSHeartbeat->>BackgroundThread: Create and Start Thread
    activate BackgroundThread
    loop Every 'interval' seconds
        BackgroundThread->>SQS_API: ChangeMessageVisibility(receiptHandle, visibility_timeout)
        SQS_API-->>BackgroundThread: Success/Failure
        BackgroundThread->>SQSHeartbeat: Record Success/Failure
    end
    LambdaHandler->>SQSHeartbeat: stop()
    SQSHeartbeat->>BackgroundThread: Signal Thread to Stop
    deactivate BackgroundThread
    SQSHeartbeat-->>LambdaHandler: Return (Indicates if heartbeat failed at any point)
```

## 4. CloudWatch Critical Alert Flow

Visualizes the flow from a critical log message to an email notification.

```mermaid
graph TD
    A[Lambda logs CRITICAL 'Final DB Update Failed' message] --> B{CloudWatch Logs receives event};
    B --> C{Metric Filter 'FinalDbUpdateFailureFilter-Dev' scans log group};
    C -- Pattern Match --> D[Custom Metric 'FinalDbUpdateFailureCount' increments by 1];
    D --> E{CloudWatch Alarm 'WhatsAppProcessorFinalDbUpdateFailureAlarm-Dev' evaluates metric};
    E -- Metric >= 1 (Sum over 5min) --> F[Alarm enters ALARM state];
    F --> G[Alarm publishes message to SNS Topic 'ai-comms-critical-alerts-dev'];
    G --> H[SNS sends notification to subscribed Email Endpoint];
    H --> I[Developer Receives Email Alert];
```

## 5. Lambda Module Interactions

Shows the primary call flow between Python modules within the `whatsapp-channel-processor-dev` Lambda.

```mermaid
graph LR
    Handler[index.lambda_handler] --> ContextProc[utils.context_processor]
    Handler --> Heartbeat[utils.sqs_heartbeat]
    Handler --> DynamoService[services.dynamodb_service]
    Handler --> SecretsService[services.secrets_manager_service]
    Handler --> OpenAIService[core.openai_processor]
    Handler --> TwilioService[services.twilio_service]
    Handler --> Logging[utils.logging_config]

    ContextProc -- parses/validates context --> Handler
    Heartbeat -- manages visibility timeout --> Handler
    DynamoService -- interacts with conversations-dev --> Handler
    SecretsService -- fetches API keys --> Handler
    OpenAIService -- calls OpenAI API --> Handler
    TwilioService -- calls Twilio API --> Handler
    Logging -- configures logger --> Handler
```

## 6. Error Handling Flow (SQS Message Outcome)

Illustrates how different processing outcomes affect the SQS message handling.

```mermaid
graph TD
    Start[Lambda receives SQS message record] --> Process{Process Message}

    Process -- Success --> StopHeartbeatSuccess{Stop Heartbeat}
    StopHeartbeatSuccess -- OK --> FinishSuccess[Processing Complete: Message Deleted by AWS]
    StopHeartbeatSuccess -- Heartbeat Failed During Run --> LogHBError[Log Heartbeat Error]
    LogHBError --> ReportFailure[Report batchItemFailure]

    Process -- Validation Error --> ErrorPath{Log Error}
    Process -- Idempotency Check Failed (Already Processed) --> LogWarning[Log Warning]
    LogWarning --> StopHeartbeatWarning{Stop Heartbeat}
    StopHeartbeatWarning --> FinishSuccess 
    Process -- Credential Error --> ErrorPath
    Process -- OpenAI Error --> ErrorPath
    Process -- Twilio Error --> ErrorPath
    Process -- Final DB Update Error (CRITICAL) --> CriticalErrorPath{Log CRITICAL Error}
    Process -- Other DB Error --> ErrorPath

    ErrorPath --> AttemptFinalDBUpdate{Attempt Final DB Status Update (Failed)}
    AttemptFinalDBUpdate --> StopHeartbeatError{Stop Heartbeat}
    StopHeartbeatError --> ReportFailure

    CriticalErrorPath --> TriggerAlarm[Trigger CloudWatch Alarm]
    TriggerAlarm --> AttemptFinalDBUpdate

    ReportFailure --> FinishFailure[Processing Failed: Return messageId in batchItemFailures]
``` 