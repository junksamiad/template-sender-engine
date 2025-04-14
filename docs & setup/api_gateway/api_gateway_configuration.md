# AI Multi-Comms Engine - API Gateway Configuration

This document outlines the API Gateway configuration for the AI Multi-Communications Engine development environment. This serves as the entry point for all frontend applications to interact with our system.

## 1. API Gateway Overview

### 1.1 Purpose

The API Gateway serves as the front door for all application traffic, providing:
- A single, unified entry point for multiple frontends
- Authentication via API keys
- Rate limiting to prevent abuse
- CORS support for web-based frontends
- Logging and monitoring capabilities

### 1.2 Configuration Approach

For our development environment, we configure the API Gateway directly using AWS CLI commands rather than through infrastructure as code (CDK/CloudFormation). This provides more granular control during the development phase.

## 2. API Gateway Configuration Details

### 2.1 Basic Settings

- **API Name**: `ai-multi-comms-dev-api`
- **Deployment Stage**: `dev`
- **Endpoint Type**: `REGIONAL`
- **API Gateway ID**: To be generated during creation

### 2.2 Resource Structure

```
/
└── /initiate-conversation (POST)
```

### 2.3 Rate Limiting Settings

As specified in our architecture documentation:

- **Rate Limit**: 10 requests per second
- **Burst Limit**: 20 concurrent requests

These limits help protect our backend services from excessive traffic while providing sufficient capacity for normal operation.

### 2.4 CORS Configuration

Cross-Origin Resource Sharing (CORS) is enabled with the following settings:

- **Allowed Origins**: `*` (For development. Will be restricted in production)
- **Allowed Methods**: `POST, OPTIONS`
- **Allowed Headers**: `Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token`
- **Exposed Headers**: `None`
- **Max Age**: `300` seconds
- **Allow Credentials**: `false`

### 2.5 API Key Configuration

#### 2.5.1 API Key Management

API keys are managed at the API Gateway level rather than in the Lambda function. This approach:
- Simplifies authentication logic
- Leverages AWS's built-in security features
- Provides usage metrics per API key

#### 2.5.2 API Key Setup

For each company/client, we create a separate API key:

- **Key Name**: `{company-name}-dev` (e.g., `cucumber-recruitment-dev`)
- **Description**: `Development API key for {Company Name}`
- **Enabled**: `true`

#### 2.5.3 Usage Plans

We create a single usage plan for the development environment:

- **Plan Name**: `dev-usage-plan`
- **Throttle Settings**:
  - Rate: 10 requests per second
  - Burst: 20 requests
- **Quota Settings**: None for development (unlimited)

Each API key is associated with this usage plan.

### 2.6 Logging and Monitoring

- **CloudWatch Logs**: Enabled with INFO level
- **Access Logging**: Enabled
- **Data Tracing**: Enabled for development (helps with debugging)
- **Detailed Metrics**: Enabled per resource/method

## 3. Mock Integration

For initial testing, we configure a mock integration that:
- Returns a 200 OK response
- Includes a simple JSON body indicating success
- Simulates the expected response format

This allows testing the API Gateway configuration before connecting it to a Lambda function.

## 4. Testing the Configuration

### 4.1 Sample cURL Request

```bash
curl -X POST https://{api-id}.execute-api.eu-north-1.amazonaws.com/dev/initiate-conversation \
  -H "Content-Type: application/json" \
  -H "x-api-key: {your-api-key}" \
  -d '{
    "company_data": {
      "company_id": "test-company",
      "project_id": "test-project"
    },
    "recipient_data": {
      "recipient_first_name": "Test",
      "recipient_last_name": "User",
      "recipient_tel": "+1234567890",
      "recipient_email": "test@example.com",
      "comms_consent": true
    },
    "request_data": {
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "channel_method": "whatsapp",
      "initial_request_timestamp": "2023-06-15T14:30:45.123Z"
    }
  }'
```

### 4.2 Expected Response (Mock)

```json
{
  "status": "success",
  "message": "API Gateway configuration is working",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## 5. Deployment Commands

The following AWS CLI commands are used to create and configure the API Gateway:

```bash
# These commands will be executed to set up the API Gateway
# Step 1: Create the API
# Step 2: Create resources and methods
# Step 3: Configure CORS
# Step 4: Set up mock integration
# Step 5: Create and configure usage plan
# Step 6: Create API keys
# Step 7: Deploy the API
```

Detailed commands will be provided in the deployment script.

## 6. Next Steps

Once the API Gateway is successfully deployed and tested with the mock integration:

1. Create the Lambda function for the Channel Router
2. Update the API Gateway to integrate with the Lambda
3. Implement full request validation and processing

## 7. Security Considerations

- API keys should be treated as sensitive credentials
- In production, CORS settings should be restricted to specific domains
- Consider implementing AWS WAF for additional protection
- Rotate API keys periodically
- Monitor for unusual traffic patterns 