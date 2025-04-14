#!/bin/bash

# --- Replace placeholders below! ---
API_GATEWAY_URL="https://xlijn1k4xh.execute-api.eu-north-1.amazonaws.com/dev/initiate-conversation"
API_KEY="YbgTABlGlg6s2YZ9gcyuB4AUhi5jJcC05yeKcCWR"
# ---------------------------------

# Use a Here Document for the request body to handle quotes safely
read -r -d '' REQUEST_BODY <<'EOF'
{
  "company_data": {
    "company_id": "ci-aaa-001",
    "project_id": "pi-aaa-001"
  },
  "recipient_data": {
    "recipient_first_name": "Lee",
    "recipient_last_name": "Hayton",
    "recipient_tel": "+447835065013",
    "recipient_email": "junksamiad@gmail.com",
    "comms_consent": true
  },
  "project_data": {
    "analysisEngineID": "analysis_1234567890_abc123def",
    "jobID": "9999",
    "jobRole": "Healthcare Assistant",
    "clarificationPoints": [
      {
        "point": "The CV does not mention a driving licence. This needs clarification.",
        "pointConfirmed": "false"
      },
      {
        "point": "The CV does not mention owning a vehicle. This is a preference, not a requirement.",
        "pointConfirmed": "false"
      },
      {
        "point": "There is a gap in the timeline of work experience between Sept 2021 and Feb 2022. This needs clarification.",
        "pointConfirmed": "false"
      },
      {
        "point": "The candidate lives in Manchester but the job is in Liverpool which could be more than 30 miles travel from residence to workplace. Will this be an issue? This needs clarification.",
        "pointConfirmed": "false"
      },
      {
        "point": "The job description explicitly states no sponsorship, indicating that the person needs to have a right to work in the UK. This needs clarification.",
        "pointConfirmed": "false"
      },
      {
        "point": "The candidate's CV shows just 18 months experience working in care. The job states minimum 2 years. This needs clarification.",
        "pointConfirmed": "false"
      }
    ]
  },
  "request_data": {
    "request_id": "550e8400-e29b-41d4-a716-446655440002",
    "channel_method": "whatsapp",
    "initial_request_timestamp": "2023-09-15T11:45:32.789Z"
  }
}
EOF

echo "Sending request to: $API_GATEWAY_URL"

curl -X POST "$API_GATEWAY_URL" \
-H "Content-Type: application/json" \
-H "x-api-key: $API_KEY" \
-d "$REQUEST_BODY"

echo "\nRequest complete." 