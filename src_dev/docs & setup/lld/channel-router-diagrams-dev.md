# Channel Router - Diagrams

## 1. High-Level System Architecture (Development)

This diagram shows the main AWS services involved in Part A (Channel Router) of the system.

```mermaid
graph TD
    subgraph "Client/Frontend"
        ClientApp[Client Application]
    end

    subgraph "AWS API Gateway (ai-multi-comms-dev-api)"
        %% Note: Authentication via API Key validated against Usage Plan
        APIGW["'/initiate-conversation' (POST)"]
        APIKeyValidation["API Key Validation (dev-usage-plan)"]
    end

    subgraph "AWS Lambda (channel-router-dev)"
        LambdaFunc[channel-router-dev]
    end

    subgraph "AWS DynamoDB (company-data-dev)"
        DynamoTable[company-data-dev Table]
    end

    subgraph "AWS SQS (Queues - Dev)"
        SQS_W[WhatsApp Queue]
        SQS_S[SMS Queue]
        SQS_E[Email Queue]
    end

    ClientApp -- HTTPS Request --> APIGW
    APIGW -- Requires --> APIKeyValidation
    APIGW -- Triggers (AWS_PROXY) --> LambdaFunc
    LambdaFunc -- Reads Config --> DynamoTable
    DynamoTable -- Config Data --> LambdaFunc
    LambdaFunc -- Build Context & Route --> SQS_W
    LambdaFunc -- Build Context & Route --> SQS_S
    LambdaFunc -- Build Context & Route --> SQS_E
```

## 2. Authentication Flow

This diagram focuses on the authentication step performed by API Gateway using the mandatory `x-api-key` header.

```mermaid
sequenceDiagram
    participant Client
    participant API Gateway
    participant UsagePlan [dev-usage-plan]
    participant APIKey [API Key (test-company-dev)]
    participant Lambda [channel-router-dev]

    Client->>API Gateway: POST /initiate-conversation (with x-api-key Header)
    API Gateway->>API Gateway: Extract x-api-key header
    API Gateway->>UsagePlan: Check if request associated with plan?
    UsagePlan-->>API Gateway: Yes/No
    alt Request is associated with Usage Plan
        API Gateway->>APIKey: Validate provided API Key against keys in plan
        APIKey-->>API Gateway: Key Valid / Invalid
        alt Key is Valid
            API Gateway->>Lambda: Trigger Lambda Function
            Lambda-->>API Gateway: Lambda Response
        else Key is Invalid
            API Gateway-->>Client: Return 403 Forbidden Response
        end
    else Request not associated with Usage Plan
        API Gateway-->>Client: Return 403 Forbidden Response
    end
    API Gateway-->>Client: Forward Lambda Response / Error

```

## 3. Lambda Validation Flow

This diagram details the sequence of validation steps performed *inside* the Channel Router Lambda function after it receives a request.

```mermaid
graph TD
    Start[Lambda Triggered] --> ParseBody{Parse Request Body}
    ParseBody -- Valid JSON --> ValidateStructure{Check Required Sections}
    ParseBody -- Invalid JSON --> ErrorResponse["Return 400 (INVALID_REQUEST)"]

    ValidateStructure -- Sections OK --> ValidateRequestData{Validate request_data Fields}
    ValidateStructure -- Sections Missing/Invalid --> ErrorResponseStruct["Return 400 (MISSING/INVALID_*_SECTION)"]

    ValidateRequestData -- request_data OK --> ValidateRecipientData{Validate recipient_data Fields}
    ValidateRequestData -- request_data Invalid --> ErrorResponseReqData["Return 400 (INVALID_*)"]

    ValidateRecipientData -- recipient_data OK --> ExtractIDs{Extract company/project IDs}
    ValidateRecipientData -- recipient_data Invalid --> ErrorResponseRecipData["Return 400 (INVALID_*)"]

    ExtractIDs -- IDs Found --> GetConfig[Get Config from DynamoDB]
    ExtractIDs -- IDs Missing --> ErrorResponseIDs["Return 400 (MISSING_IDENTIFIERS)"]

    GetConfig -- Config Found --> CheckStatus{Check project_status}
    GetConfig -- Not Found --> ErrorResponseNotFound["Return 404 (COMPANY_NOT_FOUND)"]
    GetConfig -- DB Error --> ErrorResponseDB["Return 500 (DATABASE_ERROR)"]

    CheckStatus -- Status Active --> CheckChannel{Check allowed_channels}
    CheckStatus -- Status Inactive --> ErrorResponseInactive["Return 403 (PROJECT_INACTIVE)"]

    CheckChannel -- Channel Allowed --> GetQueueURL{Get SQS Queue URL for Channel}
    CheckChannel -- Channel Not Allowed --> ErrorResponseChannel["Return 403 (CHANNEL_NOT_ALLOWED)"]

    GetQueueURL -- URL Found --> ProceedToSQS[Proceed to Build Context & Send SQS]
    GetQueueURL -- URL Not Found --> ErrorResponseConfig["Return 500 (CONFIGURATION_ERROR)"]
```

This document provides supplementary diagrams visualizing the data flows, structure, and interactions related to the Channel Router Lambda (`channel-router-dev`).

## 4. High-Level Sequence Diagram

This diagram shows the end-to-end flow initiated by a client request.

```mermaid
sequenceDiagram
    participant Client
    participant API Gateway
    participant ChannelRouterLambda [channel-router-dev]
    participant DynamoDB [company-data-dev]
    participant SQS [SQS Queues]

    Client->>API Gateway: POST /initiate-conversation (Payload, x-api-key)
    API Gateway->>API Gateway: Validate API Key
    API Gateway->>ChannelRouterLambda: Trigger (AWS_PROXY Event)
    ChannelRouterLambda->>ChannelRouterLambda: Parse Request Body
    ChannelRouterLambda->>ChannelRouterLambda: Validate Payload
    ChannelRouterLambda->>DynamoDB: GetItem(company_id, project_id)
    DynamoDB-->>ChannelRouterLambda: Return Company Config / Not Found
    ChannelRouterLambda->>ChannelRouterLambda: Validate Config (status, channels)
    ChannelRouterLambda->>ChannelRouterLambda: Build Context Object
    ChannelRouterLambda->>SQS: SendMessage(Context Object)
    SQS-->>ChannelRouterLambda: Message Accepted Confirmation
    ChannelRouterLambda-->>API Gateway: Return Success/Error Response (JSON)
    API Gateway-->>Client: Forward Response (e.g., 200 OK)
```

## 5. Context Object Structure

This diagram outlines the main components of the JSON `Context Object` generated by `context_builder.py` and sent to SQS.

```mermaid
graph TD
    ContextObject --> Metadata
    ContextObject --> FrontendPayload[frontend_payload]
    ContextObject --> CompanyDataPayload[company_data_payload]
    ContextObject --> ConversationData[conversation_data]

    Metadata --> router_version
    Metadata --> timestamp

    FrontendPayload --> company_data
    FrontendPayload --> recipient_data
    FrontendPayload --> request_data
    FrontendPayload --> project_data(Optional)

    CompanyDataPayload --> company_id
    CompanyDataPayload --> project_id
    CompanyDataPayload --> allowed_channels
    CompanyDataPayload --> project_status
    CompanyDataPayload --> channel_config
    CompanyDataPayload --> ai_config(Optional)
    CompanyDataPayload --> company_rep(Optional)
    CompanyDataPayload --> rate_limits

    ConversationData --> conversation_id
    ConversationData --> thread_id(Placeholder: null)
    ConversationData --> content_variables(Placeholder: null)
    ConversationData --> message(Placeholder: null)
    ConversationData --> conversation_status(Placeholder: &quot;initiated&quot;)
    ConversationData --> latest_message_timestamp(Placeholder: null)
    ConversationData --> message_count(Placeholder: 0)
    ConversationData --> channel_metadata
    ConversationData --> function_call(Placeholder: false)
    ConversationData --> function_type(Placeholder: null)

    subgraph channel_metadata
        channel_method
        delivery_status(Placeholder: null)
        message_sid(Placeholder: null)
    end

```

## 6. Lambda Module Interactions

This diagram shows the primary call flow between the Python modules within the `channel-router-dev` Lambda function.

```mermaid
graph LR
    Handler[index.lambda_handler] --> RequestParser[utils.request_parser]
    Handler --> Validator[utils.validators]
    Handler --> DynamoService[services.dynamodb_service]
    Handler --> ContextBuilder[core.context_builder]
    Handler --> SqsService[services.sqs_service]
    Handler --> ResponseBuilder[utils.response_builder]

    RequestParser -- parses event body --> Handler
    Validator -- validates payload & config --> Handler
    DynamoService -- fetches company config --> Handler
    ContextBuilder -- uses payload & config --> Handler
    ContextBuilder -- generates context object --> Handler
    SqsService -- gets queue URL & sends message --> Handler
    ResponseBuilder -- formats success/error JSON --> Handler
```

## 7. Error Handling Flow

This diagram illustrates how different error conditions are handled and mapped to HTTP responses.

```mermaid
graph TD
    Start[Request Received] --> ParseRequest{Parse Request Body?}
    ParseRequest -- Success --> ValidatePayload{Validate Payload?}
    ParseRequest -- Failure --> Error400["Build 400 Response (INVALID_REQUEST)"]

    ValidatePayload -- Success --> GetConfig{Get Company Config?}
    ValidatePayload -- Failure --> Error400Payload["Build 400 Response (INVALID_PAYLOAD)"]

    GetConfig -- Success --> ValidateConfig{Validate Config?}
    GetConfig -- Not Found --> Error404["Build 404 Response (COMPANY_NOT_FOUND)"]
    GetConfig -- DB Error --> Error500DB["Build 500 Response (DATABASE_ERROR)"]
    GetConfig -- Inactive --> Error403["Build 403 Response (PROJECT_INACTIVE)"]

    ValidateConfig -- Success --> GetQueue{Get Queue URL?}
    ValidateConfig -- Failure --> Error400Config["Build 400 Response (CONFIG_VALIDATION_FAILED)"]

    GetQueue -- Success --> BuildContext{Build Context Object?}
    GetQueue -- Invalid Channel --> Error400Channel["Build 400 Response (INVALID_CHANNEL)"]

    BuildContext -- Success --> SendSQS{Send to SQS?}
    BuildContext -- Failure --> Error500Internal["Build 500 Response (INTERNAL_ERROR)"]

    SendSQS -- Success --> Success200["Build 200 Response (Success)"]
    SendSQS -- Failure --> Error500SQS["Build 500 Response (SQS_SEND_ERROR)"]

    Error400 --> End[Return Response]
    Error400Payload --> End
    Error404 --> End
    Error500DB --> End
    Error403 --> End
    Error400Config --> End
    Error400Channel --> End
    Error500Internal --> End
    Error500SQS --> End
    Success200 --> End
```