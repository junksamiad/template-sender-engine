# WhatsApp AI Chatbot Architecture Diagrams

This document contains visual representations of the WhatsApp AI chatbot architecture using Mermaid diagrams.

## System Overview

```mermaid
graph TD
    FE[Frontend Applications] -->|Send Payload| Router[Channel Router]
    Router -->|Route by channel_method| API[API Gateway]
    API -->|Forward Request| Lambda[Lambda Function]
    
    subgraph "AWS Cloud"
        Router
        API
        Lambda -->|Lookup Company Config| CompanyDB[(DynamoDB<br/>wa_company_data)]
        Lambda -->|Create Conversation| ConvoDB[(DynamoDB<br/>wa_conversation)]
        Lambda -->|Create Thread| OpenAI[OpenAI Assistants API]
        OpenAI -->|Function Call| Lambda
        Lambda -->|Send Template Message| Twilio[Twilio API]
        
        SecretsManager[AWS Secrets Manager] -.->|Provide Secrets| Lambda
    end
    
    Twilio -->|Send WhatsApp Message| User((End User))
    User -->|Reply| Twilio
    
    style FE fill:#f9f,stroke:#333,stroke-width:2px
    style Router fill:#D6A2E8,stroke:#333,stroke-width:2px
    style Lambda fill:#85C1E9,stroke:#333,stroke-width:2px
    style CompanyDB fill:#F8C471,stroke:#333,stroke-width:2px
    style ConvoDB fill:#F8C471,stroke:#333,stroke-width:2px
    style OpenAI fill:#7DCEA0,stroke:#333,stroke-width:2px
    style Twilio fill:#C39BD3,stroke:#333,stroke-width:2px
    style User fill:#5D6D7E,stroke:#333,stroke-width:2px,color:#fff
```

## Channel Routing Architecture

```mermaid
graph TD
    FE[Frontend Applications] -->|Send Payload| Router[Channel Router]
    
    Router -->|channel_method = "whatsapp"| WhatsAppAPI[WhatsApp API Gateway]
    Router -->|channel_method = "email"| EmailAPI[Email API Gateway]
    Router -->|channel_method = "sms"| SMSAPI[SMS API Gateway]
    
    WhatsAppAPI -->|Forward Request| WhatsAppLambda[WhatsApp Lambda]
    EmailAPI -->|Forward Request| EmailLambda[Email Lambda]
    SMSAPI -->|Forward Request| SMSLambda[SMS Lambda]
    
    subgraph "WhatsApp Implementation"
        WhatsAppLambda -->|Process Request| WhatsAppFlow[WhatsApp Processing Flow]
        WhatsAppFlow -->|Send Message| Twilio[Twilio API]
    end
    
    subgraph "Email Implementation (Future)"
        EmailLambda -->|Process Request| EmailFlow[Email Processing Flow]
        EmailFlow -->|Send Email| EmailService[Email Service]
    end
    
    subgraph "SMS Implementation (Future)"
        SMSLambda -->|Process Request| SMSFlow[SMS Processing Flow]
        SMSFlow -->|Send SMS| SMSService[SMS Service]
    end
    
    Twilio -->|Deliver Message| User((End User))
    EmailService -->|Deliver Email| User
    SMSService -->|Deliver SMS| User
    
    style FE fill:#f9f,stroke:#333,stroke-width:2px
    style Router fill:#D6A2E8,stroke:#333,stroke-width:2px
    style WhatsAppAPI fill:#85C1E9,stroke:#333,stroke-width:2px
    style EmailAPI fill:#85C1E9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style SMSAPI fill:#85C1E9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style WhatsAppLambda fill:#85C1E9,stroke:#333,stroke-width:2px
    style EmailLambda fill:#85C1E9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style SMSLambda fill:#85C1E9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style EmailService fill:#C39BD3,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style SMSService fill:#C39BD3,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style User fill:#5D6D7E,stroke:#333,stroke-width:2px,color:#fff
```

## Frontend Request Flow

```mermaid
sequenceDiagram
    participant Frontend
    participant Router as Channel Router
    participant API as API Gateway
    participant Lambda
    participant CompanyDB as wa_company_data
    participant ConvoDB as wa_conversations
    participant OpenAI
    participant Twilio
    participant User
    
    Frontend->>Router: Send payload (user, content, company data, channel_method)
    Router->>API: Route based on channel_method="whatsapp"
    API->>Lambda: Forward request
    
    Note over Lambda,CompanyDB: Create Context Object
    Lambda->>CompanyDB: Lookup company config using company_id & project_id
    CompanyDB-->>Lambda: Return company configuration
    
    Note over Lambda: Add company data to context object
    
    Lambda->>ConvoDB: Create new conversation record (status = 'pending')
    ConvoDB-->>Lambda: Confirm record creation with conversation_id
    
    Lambda->>OpenAI: Create thread & attach assistant
    Lambda->>OpenAI: Add message with all data
    OpenAI-->>Lambda: Return thread_id
    
    Lambda->>OpenAI: Run assistant
    OpenAI-->>Lambda: Function calling (send_template_message)
    
    Lambda->>Twilio: Send template message
    Twilio-->>Lambda: Confirm message sent
    
    Lambda->>ConvoDB: Update conversation status to 'active'
    ConvoDB-->>Lambda: Confirm status update
    
    Lambda-->>API: Return success response with conversation_id
    API-->>Router: Return success response
    Router-->>Frontend: Return success response with conversation_id
    
    Twilio->>User: Deliver WhatsApp message
    
    Note over User: Future build will handle<br/>user replies via Twilio webhook
```

## Simplified Conversation Management Flow

```mermaid
flowchart TD
    Start([Receive Frontend Request]) --> RouteChannel[Route by Channel Method]
    
    RouteChannel --> ValidChannel{Valid<br/>Channel?}
    
    ValidChannel -->|No| ReturnError[Return Error]
    
    ValidChannel -->|Yes| CreateContext[Create Context Object]
    
    CreateContext --> LookupCompany[Lookup Company Data]
    
    LookupCompany --> ValidCompany{Company<br/>Valid?}
    
    ValidCompany -->|No| ReturnError
    
    ValidCompany -->|Yes| CreateConvo[Create New Conversation Record]
    
    CreateConvo --> ProcessRequest[Process Request with OpenAI]
    
    ProcessRequest --> SendMessage[Send Message via Channel]
    
    SendMessage --> UpdateStatus[Update Conversation Status]
    
    UpdateStatus --> SendResponse([Return Response])
    
    ReturnError --> End([End])
    SendResponse --> End
    
    style Start fill:#bbf,stroke:#333,stroke-width:2px
    style RouteChannel fill:#D6A2E8,stroke:#333,stroke-width:2px
    style CreateContext fill:#bfb,stroke:#333,stroke-width:2px
    style LookupCompany fill:#bfb,stroke:#333,stroke-width:2px
    style ReturnError fill:#fbb,stroke:#333,stroke-width:2px
    style CreateConvo fill:#f9a,stroke:#333,stroke-width:2px
    style SendResponse fill:#bbf,stroke:#333,stroke-width:2px
    style End fill:#bbf,stroke:#333,stroke-width:2px
```

## Context Object Pattern

```mermaid
classDiagram
    class RequestContext {
        +object payload
        +string channelMethod
        +object companyData
        +object conversationData
        +string threadId
        +string messageId
        +object channelResponse
        +array errors
        +setChannelMethod(method)
        +addCompanyData(data)
        +addConversationData(data)
        +setThreadId(id)
        +setMessageId(id)
        +addChannelResponse(response)
        +addError(error)
        +isValid()
    }
    
    class ProcessingStep {
        +execute(context)
        +rollback(context)
    }
    
    class ChannelRoutingStep {
        +execute(context)
        +rollback(context)
    }
    
    class CompanyLookupStep {
        +execute(context)
        +rollback(context)
    }
    
    class ConversationCreateStep {
        +execute(context)
        +rollback(context)
    }
    
    class OpenAIStep {
        +execute(context)
        +rollback(context)
    }
    
    class ChannelDeliveryStep {
        +execute(context)
        +rollback(context)
    }
    
    ProcessingStep <|-- ChannelRoutingStep
    ProcessingStep <|-- CompanyLookupStep
    ProcessingStep <|-- ConversationCreateStep
    ProcessingStep <|-- OpenAIStep
    ProcessingStep <|-- ChannelDeliveryStep
    
    ChannelRoutingStep --> RequestContext
    CompanyLookupStep --> RequestContext
    ConversationCreateStep --> RequestContext
    OpenAIStep --> RequestContext
    ChannelDeliveryStep --> RequestContext
```

## Database Schema

```mermaid
erDiagram
    COMPANY_DATA {
        string company_id PK
        string project_id SK
        string company_name
        string project_name
        object openai_config
        object twilio_config
        object email_config
        object sms_config
        object db_secrets
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
    
    COMPANY_DATA ||--o{ CONVERSATIONS : "has"
```

## Component Architecture

```mermaid
graph TD
    subgraph "API Layer"
        Router[Channel Router]
        Endpoint[API Endpoint]
        Validation[Input Validation]
        Auth[Authentication]
        RateLimit[Rate Limiting]
    end
    
    subgraph "Business Logic Layer"
        ChannelManager[Channel Manager]
        CompanyConfig[Company Config Manager]
        ConversationManager[Conversation Manager]
        OpenAIManager[OpenAI Integration]
        ChannelIntegration[Channel Integration]
    end
    
    subgraph "Channel Integrations"
        WhatsAppIntegration[WhatsApp/Twilio]
        EmailIntegration[Email Service]
        SMSIntegration[SMS Service]
    end
    
    subgraph "Data Layer"
        CompanyRepo[Company Repository]
        ConvoRepo[Conversation Repository]
        SecretManager[Secret Manager]
    end
    
    Router --> Endpoint
    Endpoint --> Validation
    Validation --> Auth
    Auth --> RateLimit
    
    RateLimit --> ChannelManager
    ChannelManager --> CompanyConfig
    CompanyConfig --> ConversationManager
    ConversationManager --> OpenAIManager
    OpenAIManager --> ChannelIntegration
    
    ChannelIntegration --> WhatsAppIntegration
    ChannelIntegration --> EmailIntegration
    ChannelIntegration --> SMSIntegration
    
    ChannelManager --> CompanyRepo
    CompanyConfig --> CompanyRepo
    ConversationManager --> ConvoRepo
    ChannelManager --> SecretManager
    CompanyConfig --> SecretManager
    OpenAIManager --> SecretManager
    ChannelIntegration --> SecretManager
    
    style Router fill:#D6A2E8,stroke:#333,stroke-width:2px
    style Endpoint fill:#f9f,stroke:#333,stroke-width:2px
    style ChannelManager fill:#D6A2E8,stroke:#333,stroke-width:2px
    style CompanyConfig fill:#85C1E9,stroke:#333,stroke-width:2px
    style OpenAIManager fill:#7DCEA0,stroke:#333,stroke-width:2px
    style WhatsAppIntegration fill:#C39BD3,stroke:#333,stroke-width:2px
    style EmailIntegration fill:#C39BD3,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style SMSIntegration fill:#C39BD3,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style CompanyRepo fill:#F8C471,stroke:#333,stroke-width:2px
    style ConvoRepo fill:#F8C471,stroke:#333,stroke-width:2px
```

## Deployment Architecture

```mermaid
graph TD
    subgraph "Development Environment"
        LocalAPI[Local API Server]
        MockDB[Mock DynamoDB]
        LocalTests[Local Tests]
    end
    
    subgraph "AWS Cloud - Production"
        Router[Channel Router]
        APIG[API Gateway]
        LambdaFn[Lambda Function]
        DynamoDB[DynamoDB Tables]
        Secrets[Secrets Manager]
        CloudWatch[CloudWatch]
    end
    
    subgraph "External Services"
        OpenAIAPI[OpenAI API]
        TwilioAPI[Twilio API]
        EmailAPI[Email Service API]
        SMSAPI[SMS Service API]
    end
    
    CDK[AWS CDK] -->|Deploy| Router
    CDK -->|Deploy| APIG
    CDK -->|Deploy| LambdaFn
    CDK -->|Deploy| DynamoDB
    CDK -->|Deploy| Secrets
    
    Router -->|Route| APIG
    APIG -->|Invoke| LambdaFn
    LambdaFn -->|Read/Write| DynamoDB
    LambdaFn -->|Get Secrets| Secrets
    LambdaFn -->|Call| OpenAIAPI
    LambdaFn -->|Call| TwilioAPI
    LambdaFn -->|Call| EmailAPI
    LambdaFn -->|Call| SMSAPI
    LambdaFn -->|Log| CloudWatch
    
    style CDK fill:#5DADE2,stroke:#333,stroke-width:2px
    style Router fill:#D6A2E8,stroke:#333,stroke-width:2px
    style APIG fill:#85C1E9,stroke:#333,stroke-width:2px
    style LambdaFn fill:#85C1E9,stroke:#333,stroke-width:2px
    style DynamoDB fill:#F8C471,stroke:#333,stroke-width:2px
    style OpenAIAPI fill:#7DCEA0,stroke:#333,stroke-width:2px
    style TwilioAPI fill:#C39BD3,stroke:#333,stroke-width:2px
    style EmailAPI fill:#C39BD3,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style SMSAPI fill:#C39BD3,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
```

## Future Reply Handling (Next Build)

```mermaid
graph TD
    User((End User)) -->|Reply| Twilio[Twilio API]
    Twilio -->|Webhook Event| APIG[API Gateway]
    APIG -->|Trigger| ReplyLambda[Reply Handler Lambda]
    
    subgraph "AWS Cloud - Future Build"
        ReplyLambda -->|Lookup Latest Conversation| ConvoDB[(DynamoDB<br/>wa_conversation)]
        ReplyLambda -->|Continue Thread| OpenAI[OpenAI Assistants API]
        ReplyLambda -->|Send Response| Twilio
        
        SecretsManager[AWS Secrets Manager] -.->|Provide Secrets| ReplyLambda
    end
    
    Twilio -->|Deliver Response| User
    
    style User fill:#5D6D7E,stroke:#333,stroke-width:2px,color:#fff
    style Twilio fill:#C39BD3,stroke:#333,stroke-width:2px
    style APIG fill:#85C1E9,stroke:#333,stroke-width:2px
    style ReplyLambda fill:#85C1E9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    style ConvoDB fill:#F8C471,stroke:#333,stroke-width:2px
    style OpenAI fill:#7DCEA0,stroke:#333,stroke-width:2px
    style SecretsManager fill:#D6EAF8,stroke:#333,stroke-width:2px
``` 