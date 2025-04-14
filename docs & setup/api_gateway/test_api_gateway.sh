#!/bin/bash
# API Gateway Test Script for AI Multi-Comms Engine (Development)
# This script tests the API Gateway configuration

# Configuration - Replace these values with your actual API Gateway details
API_ID="302fd6rbg3"                          # Update with your API Gateway ID
API_KEY="JPeCbzB4mM5MOfdZHvjBS3i1GfMwaN0p97eTRwo2"                         # Update with your API key
AWS_REGION="eu-north-1"            # Update with your AWS region
API_URL="https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/dev"
ENDPOINT="$API_URL/initiate-conversation"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Sample payload
PAYLOAD='{
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

# Check if API_ID and API_KEY are provided
if [ -z "$API_ID" ] || [ -z "$API_KEY" ]; then
    echo -e "${RED}Error: Please update the API_ID and API_KEY variables in this script.${NC}"
    echo "These values are printed when you run the deploy_api_gateway.sh script."
    exit 1
fi

# Function to print section header
print_header() {
    echo -e "\n${BLUE}==========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}==========================================${NC}"
}

# Test 1: Basic connectivity check (OPTIONS request for CORS)
test_cors() {
    print_header "Test 1: CORS Configuration (OPTIONS request)"

    echo "Sending OPTIONS request to $ENDPOINT..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X OPTIONS $ENDPOINT \
      -H "Origin: http://example.com" \
      -H "Access-Control-Request-Method: POST" \
      -H "Access-Control-Request-Headers: Content-Type, X-Api-Key")

    if [ "$RESPONSE" -eq 200 ]; then
        echo -e "${GREEN}✓ CORS is correctly configured (HTTP 200 response)${NC}"
        
        # Check headers in detail
        echo -e "\nExamining CORS headers in detail:"
        HEADERS=$(curl -s -I -X OPTIONS $ENDPOINT \
          -H "Origin: http://example.com" \
          -H "Access-Control-Request-Method: POST" \
          -H "Access-Control-Request-Headers: Content-Type, X-Api-Key")
        
        echo "$HEADERS" | grep -i "Access-Control-Allow-Origin"
        echo "$HEADERS" | grep -i "Access-Control-Allow-Methods"
        echo "$HEADERS" | grep -i "Access-Control-Allow-Headers"
    else
        echo -e "${RED}✗ CORS test failed with HTTP $RESPONSE${NC}"
    fi
}

# Test 2: API Key validation
test_api_key() {
    print_header "Test 2: API Key Validation"

    echo "2.1: Testing with valid API key..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $ENDPOINT \
      -H "Content-Type: application/json" \
      -H "x-api-key: $API_KEY" \
      -d "$PAYLOAD")

    if [ "$RESPONSE" -eq 200 ]; then
        echo -e "${GREEN}✓ Valid API key accepted (HTTP 200 response)${NC}"
    else
        echo -e "${RED}✗ Valid API key test failed with HTTP $RESPONSE${NC}"
    fi

    echo -e "\n2.2: Testing with invalid API key..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $ENDPOINT \
      -H "Content-Type: application/json" \
      -H "x-api-key: invalidkey123" \
      -d "$PAYLOAD")

    if [ "$RESPONSE" -eq 403 ]; then
        echo -e "${GREEN}✓ Invalid API key correctly rejected (HTTP 403 response)${NC}"
    else
        echo -e "${RED}✗ Invalid API key test failed with HTTP $RESPONSE (expected 403)${NC}"
    fi

    echo -e "\n2.3: Testing with missing API key..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $ENDPOINT \
      -H "Content-Type: application/json" \
      -d "$PAYLOAD")

    if [ "$RESPONSE" -eq 403 ]; then
        echo -e "${GREEN}✓ Missing API key correctly rejected (HTTP 403 response)${NC}"
    else
        echo -e "${RED}✗ Missing API key test failed with HTTP $RESPONSE (expected 403)${NC}"
    fi
}

# Test 3: Mock integration response
test_mock_response() {
    print_header "Test 3: Mock Integration Response"

    echo "Testing response format..."
    RESPONSE=$(curl -s -X POST $ENDPOINT \
      -H "Content-Type: application/json" \
      -H "x-api-key: $API_KEY" \
      -d "$PAYLOAD")

    echo -e "\nResponse received:"
    echo $RESPONSE | jq '.'

    # Check if response contains expected fields
    if echo $RESPONSE | jq -e '.status' > /dev/null && \
       echo $RESPONSE | jq -e '.message' > /dev/null && \
       echo $RESPONSE | jq -e '.request_id' > /dev/null; then
        echo -e "\n${GREEN}✓ Response contains expected fields (status, message, request_id)${NC}"
    else
        echo -e "\n${RED}✗ Response is missing expected fields${NC}"
    fi

    # Check if request_id matches the mock one
    REQ_ID=$(echo $RESPONSE | jq -r '.request_id')
    if [ "$REQ_ID" == "mock-request-id" ]; then
        echo -e "${GREEN}✓ Request ID in response matches the mock one sent in response template${NC}"
    else
        echo -e "${RED}✗ Request ID mismatch or missing${NC}"
        echo -e "  Expected: mock-request-id"
        echo -e "  Received: $REQ_ID"
    fi
}

# Test 4: Content-Type validation
test_content_type() {
    print_header "Test 4: Content-Type Testing"

    echo "Testing with application/json Content-Type..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $ENDPOINT \
      -H "Content-Type: application/json" \
      -H "x-api-key: $API_KEY" \
      -d "$PAYLOAD")

    if [ "$RESPONSE" -eq 200 ]; then
        echo -e "${GREEN}✓ application/json Content-Type accepted (HTTP 200 response)${NC}"
    else
        echo -e "${RED}✗ application/json Content-Type test failed with HTTP $RESPONSE${NC}"
    fi

    # This may or may not fail depending on API Gateway configuration
    echo -e "\nTesting with text/plain Content-Type..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $ENDPOINT \
      -H "Content-Type: text/plain" \
      -H "x-api-key: $API_KEY" \
      -d "$PAYLOAD")

    if [ "$RESPONSE" -eq 415 ]; then
        echo -e "${GREEN}✓ text/plain correctly rejected (HTTP 415 response)${NC}"
    elif [ "$RESPONSE" -eq 200 ]; then
        echo -e "${YELLOW}⚠ text/plain was accepted (HTTP 200) - API Gateway is not validating Content-Type${NC}"
    else
        echo -e "${YELLOW}⚠ text/plain test returned HTTP $RESPONSE${NC}"
    fi
}

# Main test execution
check_dependencies() {
    command -v curl >/dev/null 2>&1 || { echo -e "${RED}Error: curl is required but not installed.${NC}" >&2; exit 1; }
    command -v jq >/dev/null 2>&1 || { echo -e "${RED}Warning: jq is not installed. Some tests may not work properly.${NC}" >&2; }
}

run_all_tests() {
    echo -e "${BLUE}API Gateway Test Suite${NC}"
    echo -e "${BLUE}Testing API Gateway at: $ENDPOINT${NC}"
    
    test_cors
    test_api_key
    test_mock_response
    test_content_type

    print_header "All tests completed"
}

# Check dependencies and run tests
check_dependencies
run_all_tests 