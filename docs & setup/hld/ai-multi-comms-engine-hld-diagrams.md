# AI Multi-Communications Engine - HLD Diagrams

This document provides high-level diagrams illustrating the overall architecture and end-to-end flow of the AI Multi-Communications Engine.

## 1. Overall System Architecture

```mermaid
graph TD
    Client[Client Application] -->|1. POST Request (Payload, API Key)| APIGW[API Gateway];
    APIGW -->|2. Validate Key & Trigger| RouterLambda[Router Lambda];
    RouterLambda -->|3. Read Config| CompanyDB[(DynamoDB: Company Config)];
    RouterLambda -->|4. Send Context Object| SQS[SQS Queue];
    SQS -->|5. Trigger| ProcessorLambda[Processor Lambda];
    ProcessorLambda -->|6. Read/Write State| ConversationsDB[(DynamoDB: Conversations)];
    ProcessorLambda -->|7. Read Credentials| SecretsMgr[(Secrets Manager)];
    ProcessorLambda -->|8. Call AI| OpenAI[OpenAI API];
    ProcessorLambda -->|9. Send Message| ChannelAPI[Channel API (e.g., Twilio)];
    ProcessorLambda -->|10. Log Events| CloudWatch[CloudWatch];
    CloudWatch -->|11. Monitor/Alert| Monitoring[Alarms -> SNS];

    style Client fill:#f9f,stroke:#333,stroke-width:2px
    style APIGW fill:#ccf,stroke:#333,stroke-width:2px
    style RouterLambda fill:#ccf,stroke:#333,stroke-width:2px
    style SQS fill:#ccf,stroke:#333,stroke-width:2px
    style ProcessorLambda fill:#ccf,stroke:#333,stroke-width:2px
    style CompanyDB fill:#ddf,stroke:#333,stroke-width:2px
    style ConversationsDB fill:#ddf,stroke:#333,stroke-width:2px
    style SecretsMgr fill:#ddf,stroke:#333,stroke-width:2px
    style CloudWatch fill:#ddf,stroke:#333,stroke-width:2px
    style Monitoring fill:#ddf,stroke:#333,stroke-width:2px
    style OpenAI fill:#cfc,stroke:#333,stroke-width:2px
    style ChannelAPI fill:#cfc,stroke:#333,stroke-width:2px

    subgraph AWS Cloud Infrastructure
        APIGW
        RouterLambda
        CompanyDB
        SQS
        ProcessorLambda
        ConversationsDB
        SecretsMgr
        CloudWatch
        Monitoring
    end

    subgraph External Systems
        Client
        OpenAI
        ChannelAPI
    end
```

## 2. End-to-End Sequence Diagram (Successful WhatsApp Flow)

```mermaid
sequenceDiagram
    participant Client
    participant API Gateway
    participant RouterLambda [channel-router-dev]
    participant CompanyDB [company-data-dev]
    participant SQS [WhatsApp Queue]
    participant ProcessorLambda [whatsapp-processor-dev]
    participant ConversationsDB [conversations-dev]
    participant SecretsMgr
    participant OpenAI
    participant Twilio

    Client->>+API Gateway: POST /initiate-conversation (Payload, API Key)
    API Gateway->>API Gateway: Validate API Key
    API Gateway->>+RouterLambda: Trigger with Event
    RouterLambda->>RouterLambda: Parse & Validate Payload
    RouterLambda->>+CompanyDB: GetItem (Company/Project Config)
    CompanyDB-->>-RouterLambda: Return Config
    RouterLambda->>RouterLambda: Validate Config
    RouterLambda->>RouterLambda: Build Context Object (incl. conversation_id)
    RouterLambda->>+SQS: SendMessage (Context Object)
    SQS-->>-RouterLambda: Success Confirmation
    RouterLambda-->>-API Gateway: Return 200 OK Response
    API Gateway-->>-Client: Forward 200 OK

    SQS->>+ProcessorLambda: Trigger with Event (Context Object)
    ProcessorLambda->>ProcessorLambda: Parse & Validate Context
    ProcessorLambda->>ProcessorLambda: Start SQS Heartbeat
    ProcessorLambda->>+ConversationsDB: PutItem (Initial Record, Conditional)
    ConversationsDB-->>-ProcessorLambda: Success
    ProcessorLambda->>+SecretsMgr: GetSecretValue (OpenAI Key)
    SecretsMgr-->>-ProcessorLambda: OpenAI Key
    ProcessorLambda->>+SecretsMgr: GetSecretValue (Twilio Credentials)
    SecretsMgr-->>-ProcessorLambda: Twilio Credentials
    ProcessorLambda->>+OpenAI: Process Request (Create Thread, Run Assistant)
    OpenAI-->>-ProcessorLambda: AI Response
    ProcessorLambda->>+Twilio: Send WhatsApp Message
    Twilio-->>-ProcessorLambda: Success (Message SID)
    ProcessorLambda->>+ConversationsDB: UpdateItem (Final Status, History, Thread ID)
    ConversationsDB-->>-ProcessorLambda: Success
    ProcessorLambda->>ProcessorLambda: Stop SQS Heartbeat
    ProcessorLambda-->>-SQS: Finish (Message Deleted)

```

## 3. Logical Data Model (Key Entities & Relationships)

```mermaid
graph LR
    subgraph Incoming
        ClientRequest["Client Request (JSON Payload)"]
    end

    subgraph Configuration
        CompanyConfig["Company Config (DynamoDB Item)"]
        Secrets["Secrets (Secrets Manager)"]
    end

    subgraph Processing
        ContextObject["Context Object (SQS Message)"]
        ConversationRecord["Conversation Record (DynamoDB Item)"]
    end

    ClientRequest -- "Validated & Enriched by" --> RouterLambda[Router Lambda];
    CompanyConfig -- "Read by" --> RouterLambda;
    RouterLambda -- "Builds & Sends" --> ContextObject;
    ContextObject -- "Triggers & Consumed by" --> ProcessorLambda[Processor Lambda];
    Secrets -- "Read by" --> ProcessorLambda;
    CompanyConfig -- "References" --> Secrets;
    ProcessorLambda -- "Creates/Updates" --> ConversationRecord;
    ContextObject -- "Contains Initial Data For" --> ConversationRecord;
    ClientRequest -- "Contains User Input For" --> ConversationRecord;

    style ClientRequest fill:#f9d,stroke:#333
    style CompanyConfig fill:#ddf,stroke:#333
    style Secrets fill:#ddf,stroke:#333
    style ContextObject fill:#ccf,stroke:#333
    style ConversationRecord fill:#ddf,stroke:#333
    style RouterLambda fill:#eee,stroke:#999
    style ProcessorLambda fill:#eee,stroke:#999
``` 