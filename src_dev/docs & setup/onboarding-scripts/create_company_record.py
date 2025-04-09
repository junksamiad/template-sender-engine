import boto3
import json
import argparse
import os
from datetime import datetime, timezone
from decimal import Decimal

# --- Configuration ---
# Use environment variable or default for table name
TABLE_NAME = os.environ.get("COMPANY_DATA_TABLE", "company-data-dev")
# Use environment variable or default for region
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-north-1")

# --- Helper Function to handle non-standard JSON types for DynamoDB ---
def replace_floats_with_decimal(obj):
    """Recursively replace float values with Decimal for DynamoDB compatibility."""
    if isinstance(obj, list):
        return [replace_floats_with_decimal(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: replace_floats_with_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        # Use context to handle potential precision issues if needed
        # return Decimal(str(obj)) # Safest way
        return Decimal(obj) # Often sufficient
    else:
        return obj

def validate_record(record):
    """Performs basic validation on the input record."""
    required_keys = [
        "company_id", "project_id", "company_name", "project_name",
        "api_key_reference", "allowed_channels", "rate_limits",
        "project_status", "channel_config"
    ]
    missing_keys = [key for key in required_keys if key not in record]
    if missing_keys:
        raise ValueError(f"Missing required keys in input file: {', '.join(missing_keys)}")

    if not isinstance(record.get("allowed_channels"), list) or not record["allowed_channels"]:
        raise ValueError("'allowed_channels' must be a non-empty list.")

    # Add more specific validations as needed (e.g., project_status values)
    print("Basic validation passed.")

def create_dynamodb_record(record_path):
    """Reads a JSON file, validates, prepares, and uploads to DynamoDB."""
    try:
        with open(record_path, 'r') as f:
            print(f"Reading record from: {record_path}")
            record_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {record_path}")
        return
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {record_path}: {e}")
        return

    try:
        validate_record(record_data)

        # Set timestamps
        now_iso = datetime.now(timezone.utc).isoformat()
        record_data["created_at"] = now_iso
        record_data["updated_at"] = now_iso
        print(f"Timestamps set: {now_iso}")

        # Prepare for DynamoDB (handle floats -> Decimal)
        dynamodb_item = replace_floats_with_decimal(record_data)

        # Initialize DynamoDB client
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(TABLE_NAME)

        print(f"Attempting to put item into DynamoDB table: {TABLE_NAME}...")
        # Use ConditionExpression to prevent overwriting existing items
        response = table.put_item(
            Item=dynamodb_item,
            ConditionExpression="attribute_not_exists(company_id) AND attribute_not_exists(project_id)"
        )
        print("Successfully created record in DynamoDB.")
        print(f"Response: {response}")

    except ValueError as e:
        print(f"Validation Error: {e}")
    except Exception as e:
        # Catch potential boto3 errors (e.g., ConditionalCheckFailedException)
        print(f"Error interacting with DynamoDB: {e}")
        print("Please check the company_id/project_id combination doesn't already exist and AWS credentials/permissions are correct.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new company/project record in the DynamoDB table.")
    parser.add_argument("input_file", help="Path to the JSON file containing the record data.")
    args = parser.parse_args()

    print(f"--- Starting Company Record Creation --- ")
    print(f"Using Table: {TABLE_NAME}")
    print(f"Using Region: {AWS_REGION}")
    create_dynamodb_record(args.input_file)
    print("--- Script Finished ---") 