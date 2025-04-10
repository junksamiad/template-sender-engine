#!/bin/bash
# API Gateway Lambda Integration Update Script
# This script updates the API Gateway to integrate with a Lambda function
# instead of using the mock integration

# Configuration - Update these values
API_ID="302fd6rbg3"                # Your API Gateway ID from deploy_api_gateway.sh
AWS_REGION="eu-north-1"  # Your AWS region
LAMBDA_FUNCTION_NAME="channel-router-dev"  # Your Lambda function name
LAMBDA_FUNCTION_ARN=""   # Your Lambda function ARN (leave blank to auto-construct)
ACCOUNT_ID="337909745089"            # Your AWS account ID

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if required variables are set
if [ -z "$API_ID" ] || [ -z "$LAMBDA_FUNCTION_NAME" ] || [ -z "$ACCOUNT_ID" ]; then
    echo -e "${RED}Error: Please update the API_ID, LAMBDA_FUNCTION_NAME, and ACCOUNT_ID variables at the top of this script.${NC}"
    exit 1
fi

# If Lambda ARN is not provided, construct it
if [ -z "$LAMBDA_FUNCTION_ARN" ]; then
    LAMBDA_FUNCTION_ARN="arn:aws:lambda:$AWS_REGION:$ACCOUNT_ID:function:$LAMBDA_FUNCTION_NAME"
    echo -e "${YELLOW}Constructed Lambda ARN: $LAMBDA_FUNCTION_ARN${NC}"
fi

echo -e "${BLUE}Updating API Gateway with Lambda Integration${NC}"
echo -e "${BLUE}API Gateway ID: $API_ID${NC}"
echo -e "${BLUE}Lambda Function: $LAMBDA_FUNCTION_NAME${NC}"

# Step 1: Get the resource ID for /initiate-conversation
echo -e "\n${BLUE}Step 1: Getting resource ID for /initiate-conversation${NC}"
RESOURCES=$(aws apigateway get-resources --rest-api-id $API_ID)
RESOURCE_ID=$(echo $RESOURCES | jq -r '.items[] | select(.path=="/initiate-conversation") | .id')

if [ -z "$RESOURCE_ID" ]; then
    echo -e "${RED}Error: Could not find resource ID for /initiate-conversation${NC}"
    exit 1
fi

echo "Resource ID: $RESOURCE_ID"

# Step 2: Delete the existing mock integration for the POST method
echo -e "\n${BLUE}Step 2: Removing existing mock integration for POST method${NC}"
aws apigateway delete-integration \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST

echo -e "${GREEN}Deleted existing integration${NC}"

# Step 3: Set up Lambda integration for the POST method
echo -e "\n${BLUE}Step 3: Setting up Lambda integration for POST method${NC}"
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:$AWS_REGION:lambda:path/2015-03-31/functions/$LAMBDA_FUNCTION_ARN/invocations \
  --content-handling CONVERT_TO_TEXT

echo -e "${GREEN}Lambda integration set up successfully${NC}"

# Step 4: Add permission for API Gateway to invoke Lambda
echo -e "\n${BLUE}Step 4: Adding permission for API Gateway to invoke Lambda${NC}"
aws lambda add-permission \
  --function-name $LAMBDA_FUNCTION_NAME \
  --statement-id apigateway-$API_ID \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:$AWS_REGION:$ACCOUNT_ID:$API_ID/*/POST/initiate-conversation"

echo -e "${GREEN}Lambda permission added${NC}"

# Step 5: Setup integration response
echo -e "\n${BLUE}Step 5: Setting up integration response${NC}"
aws apigateway put-integration-response \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --status-code 200 \
  --selection-pattern ""

echo -e "${GREEN}Integration response set up${NC}"

# Step 6: Deploy the API to the dev stage
echo -e "\n${BLUE}Step 6: Deploying API to dev stage${NC}"
DEPLOYMENT_ID=$(aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name dev \
  --description "Updated with Lambda integration" \
  --query 'id' \
  --output text)

echo -e "${GREEN}API deployed successfully. Deployment ID: $DEPLOYMENT_ID${NC}"

# Step 7: Update API Gateway stage settings to enable detailed CloudWatch metrics
echo -e "\n${BLUE}Step 7: Updating stage settings for CloudWatch metrics${NC}"
aws apigateway update-stage \
  --rest-api-id $API_ID \
  --stage-name dev \
  --patch-operations \
    op=replace,path=/*/*/logging/loglevel,value=INFO \
    op=replace,path=/*/*/metrics/enabled,value=true

echo -e "${GREEN}Stage settings updated${NC}"

# Final step: Print out the updated endpoint
echo -e "\n${BLUE}==========================================${NC}"
echo -e "${GREEN}API Gateway updated successfully!${NC}"
echo -e "${BLUE}==========================================${NC}"
echo -e "API Gateway endpoint: https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/dev"
echo -e "Test URL: https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/dev/initiate-conversation"
echo -e "\nTest command:"
echo -e "curl -X POST https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/dev/initiate-conversation \\"
echo -e "  -H \"Content-Type: application/json\" \\"
echo -e "  -H \"x-api-key: YOUR_API_KEY\" \\"
echo -e "  -d '{\"company_data\":{\"company_id\":\"test-company\",\"project_id\":\"test-project\"},\"recipient_data\":{\"recipient_first_name\":\"Test\",\"recipient_last_name\":\"User\",\"recipient_tel\":\"+1234567890\",\"recipient_email\":\"test@example.com\",\"comms_consent\":true},\"request_data\":{\"request_id\":\"550e8400-e29b-41d4-a716-446655440000\",\"channel_method\":\"whatsapp\",\"initial_request_timestamp\":\"2023-06-15T14:30:45.123Z\"}}'" 