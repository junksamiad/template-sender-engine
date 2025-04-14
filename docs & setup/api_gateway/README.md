# API Gateway Setup and Testing

This directory contains documentation and scripts for deploying and testing the API Gateway component of the AI Multi-Comms Engine.

## Contents

- `api_gateway_configuration.md` - Detailed documentation of the API Gateway configuration
- `deploy_api_gateway.sh` - Script to deploy the API Gateway using AWS CLI
- `test_api_gateway.sh` - Script to test the deployed API Gateway 
- `update_api_gateway_lambda.sh` - Script to update the API Gateway with Lambda integration
- `stage_patch_template.json` - Template file for CloudWatch logging patch operations
- `api_gateway_config.txt` - Output file containing deployment details (API ID, Key, Endpoint)

## Prerequisites

- AWS CLI installed and configured with appropriate credentials
- `jq` command line tool installed (for parsing JSON responses in the test script)
- Bash shell environment

## Deployment Process

1. **Review the configuration documentation**

   Before deploying, review the `api_gateway_configuration.md` file to understand the API Gateway setup.

2. **Make the deployment script executable**

   ```bash
   chmod +x deploy_api_gateway.sh
   ```

3. **Run the deployment script**

   ```bash
   ./deploy_api_gateway.sh
   ```

   The script will create:
   - A new API Gateway
   - Resources and methods
   - Mock integrations for testing
   - API key and usage plan
   - CORS configuration
   - CloudWatch logging (using `stage_patch_template.json`)

4. **Check the output file**

   The script will output details to the console and save them to `api_gateway_config.txt`:
   - API Gateway ID
   - API Gateway endpoint
   - API key value

   Keep this file safe as it contains your API key.

## Testing the API Gateway

1. **Update the test script with your API details**

   The `deploy_api_gateway.sh` script should update the `API_ID` and `API_KEY` in `test_api_gateway.sh` automatically. If not, manually copy the values from `api_gateway_config.txt` into these variables at the top of `test_api_gateway.sh`:
   ```bash
   API_ID=""     # Your API Gateway ID
   API_KEY=""    # Your API key
   AWS_REGION="eu-north-1" # Your AWS region (should be pre-filled)
   ```

2. **Make the test script executable**

   ```bash
   chmod +x test_api_gateway.sh
   ```

3. **Run the test script**

   ```bash
   ./test_api_gateway.sh
   ```

   The script will test:
   - CORS configuration
   - API key validation
   - Mock integration response format
   - Content-Type validation

4. **Review test results**

   The script will display detailed results for each test, with colored output indicating success or failure.

5. **Check CloudWatch Logs (Optional)**
   - Go to CloudWatch -> Log groups in the AWS Console.
   - Find the log group `/aws/apigateway/<YOUR_API_ID>/dev`.
   - Check the latest log stream for detailed request logs.

## Integrating with Lambda

After testing the API Gateway with mock integrations, you can connect it to a Lambda function:

1. **Make the Lambda integration script executable**

   ```bash
   chmod +x update_api_gateway_lambda.sh
   ```

2. **Update the script with your API Gateway and Lambda details**

   The `API_ID` should be pre-filled by the deployment script. Manually update these variables at the top of `update_api_gateway_lambda.sh`:
   ```bash
   LAMBDA_FUNCTION_NAME=""  # Your Lambda function name
   ACCOUNT_ID=""            # Your AWS account ID (or leave blank to auto-detect)
   ```

3. **Run the update script**

   ```bash
   ./update_api_gateway_lambda.sh
   ```

   The script will:
   - Remove the mock integration
   - Configure the Lambda integration for API Gateway
   - Set up the necessary IAM permissions
   - Redeploy the API Gateway
   - Update the CloudWatch logging and metrics

4. **Test the Lambda integration**

   After updating, you can test the Lambda integration using the curl command provided at the end of the script output.

## Next Steps After Integration

Once the API Gateway is integrated with Lambda:

1. Develop and test the Lambda function logic
2. Configure additional resources and methods if needed
3. Set up appropriate authentication and authorization
4. Deploy to production with appropriate rate limits
5. Set up monitoring and alerting

## Cleanup

To delete the API Gateway and associated resources, you can use the AWS CLI:

```bash
# Get your API ID from api_gateway_config.txt
API_ID="your-api-id"

# Delete the API Gateway
aws apigateway delete-rest-api --rest-api-id $API_ID

# Note: You may also need to delete the CloudWatch log group manually
# /aws/apigateway/<API_ID>/dev
```

## Troubleshooting

- **CloudWatch Logging Failures:** The `deploy_api_gateway.sh` script configures CloudWatch logging using a template file (`stage_patch_template.json`) and passes it via `file://` to the `aws apigateway update-stage` command. This is necessary due to complexities with shell quoting/escaping when embedding the required JSON log format directly in the command or via shell variables. If logging fails, ensure the `stage_patch_template.json` file exists and check IAM permissions for API Gateway to write to CloudWatch Logs.
- **CORS issues**: If CORS tests fail, ensure the CORS configuration in the deployment script matches your frontend requirements.
- **API key validation failures**: Verify the API key is correctly associated with the usage plan and stage.
- **Mock integration response issues**: Check the mock integration configuration in the deployment script.
- **Lambda integration issues**: Ensure the Lambda function exists and has the correct permissions.
- **Permission errors**: Ensure your AWS CLI is configured with sufficient permissions to create and manage API Gateway resources. 