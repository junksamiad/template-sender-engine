# WhatsApp Processing Engine - Overview and Architecture

> **Part 1 of 9 in the WhatsApp Processing Engine documentation series**

## 1. Introduction

The WhatsApp Processing Engine is a core component of our multi-channel communications system responsible for processing WhatsApp messages through the SQS queue, OpenAI, and Twilio. This document provides a high-level overview of the architecture and processing flow.

## 2. Component Purpose

The WhatsApp Processing Engine is responsible for:

- Consuming messages from the WhatsApp SQS queue
- Implementing the heartbeat pattern for long-running operations
- Creating and managing conversations in DynamoDB
- Retrieving credentials from AWS Secrets Manager using references provided in the context object
- Processing messages using the OpenAI Assistants API
- Delivering messages to end users via Twilio
- Handling failures and retries appropriately
- Providing detailed logging and monitoring

## 3. Position in System Architecture

The WhatsApp Processing Engine sits between:
- **Upstream**: Channel Router (via WhatsApp SQS queue)
- **Downstream**: OpenAI API and Twilio WhatsApp API
- **Persistence**: DynamoDB for conversation record management
- **Security**: AWS Secrets Manager for API credentials (accessed as needed)

```
                                   (1)                 (3)                  (5)
                                     ┌─► DynamoDB ◄────┐                    │
                                     │  (Conversations) │                    │
                                     │                  │                    ▼
Channel Router → WhatsApp SQS Queue → WhatsApp Processing Engine ────► OpenAI API ────► Twilio API → End User
                                     │          │        ▲                   ▲
                                     │          │        │                   │
                                     │          └───────(2)───────┐          │
                                     │                            ▼          │
                                     └─────────────────► AWS Secrets Manager(4)
```

Process flow:
1. Create conversation record in DynamoDB with status "received"
2. Update conversation status to "processing"
3. Update conversation with OpenAI processing results
4. Retrieve API credentials from Secrets Manager when needed:
   - For OpenAI API access before AI processing
   - For Twilio API access before message delivery
5. Update conversation with final status after delivery

## 4. Technical Implementation

The WhatsApp Processing Engine is implemented as:

- **Lambda Function**: Triggered by messages in the WhatsApp SQS queue
- **SQS Event Source**: Configured with batch size 1 for reliable processing
- **DynamoDB Access**: For conversation record creation and management
- **OpenAI Integration**: For AI-powered message processing
- **Twilio Integration**: For WhatsApp message delivery
- **Heartbeat Pattern**: For extending visibility timeout during long-running operations
- **CloudWatch**: For monitoring and logging operations
- **AWS Secrets Manager**: For securely accessing API keys

## 5. Processing Flow

The WhatsApp Processing Engine follows a linear, efficient processing flow:

1. **Message Receipt**: A message is received from the Channel Router's SQS queue containing a context object.

2. **Conversation Creation**: The engine creates a conversation record in DynamoDB with status "processing".

3. **OpenAI Processing**: 
   - The engine creates an OpenAI thread and adds the context as a message.
   - A run is created with the specified assistant.
   - The run is polled until completion.
   - The assistant responds with a structured JSON containing content variables.
   - The content variables are added to the context object.

4. **Template Message Sending**:
   - The updated context object with content variables is passed to the Twilio integration function.
   - The function retrieves WhatsApp credentials from AWS Secrets Manager using the `channel_config.whatsapp.whatsapp_credentials_id` reference from the context object.
   - These credentials include the `twilio_account_sid`, `twilio_auth_token`, and `twilio_template_sid` needed for API authentication and template identification.
   - The function uses the `channel_config.whatsapp.company_whatsapp_number` from the context object as the sender's phone number.
   - The content variables are passed to the Twilio API along with the template SID, account SID, and auth token.
   - The message is sent to the recipient's WhatsApp number (extracted from `frontend_payload.recipient_data.recipient_tel`).

5. **Conversation Finalization**:
   - The conversation record is updated with thread ID and delivery status.
   - Status is changed to "initial_message_sent".
   - The processing is complete.

## 6. Error Handling

The WhatsApp Processing Engine implements robust error handling through:

1. **Retry Logic**: Automatic retries with exponential backoff for transient failures.

2. **Dead Letter Queue**: Messages that fail after retries are sent to a DLQ for investigation.

3. **Error Categorization**: Errors are categorized by type (API errors, validation errors, etc.) for monitoring.

4. **Comprehensive Logging**: Detailed logging at each processing step for debugging.

5. **Structured Error Responses**: All errors include error codes, descriptive messages, and relevant metadata.

6. **JSON Validation**: Validation of the assistant's JSON response to ensure it contains the required variables.

## 7. Full Documentation

The WhatsApp Processing Engine is documented in detail across several files:

1. [SQS Integration](02-sqs-integration.md): Details on message queue integration, payload validation, and retry mechanisms.
2. [Conversation Management](03-conversation-management.md): Description of the DynamoDB conversation schema and operations.
3. [Credential Management](04-credential-management.md): Details on secure access to credentials for external APIs.
4. [OpenAI Integration](05-openai-integration.md): Comprehensive documentation on the OpenAI Assistants API integration.
5. [Template Management](06-template-management.md): Template creation, management, and message sending details.
6. [Error Handling Strategy](07-error-handling-strategy.md): Complete error handling approach and implementation.
7. [Monitoring & Observability](08-monitoring-observability.md): Monitoring, alerting, and observability details.
8. [Operations Playbook](09-operations-playbook.md): Operational procedures, troubleshooting, and maintenance tasks.

## 8. Component Documentation Structure

The WhatsApp Processing Engine documentation is organized into the following sections:

1. **Overview and Architecture** (this document)
2. **SQS Integration** - Queue consumption and the heartbeat pattern
3. **Conversation Management** - DynamoDB record creation and updates
4. **Credential Management** - AWS Secrets Manager integration
5. **OpenAI Integration** - Thread creation and message processing
6. **Template Management** - Template handling and message delivery
7. **Error Handling Strategy** - Approach to failures and retries
8. **Monitoring and Observability** - CloudWatch integration
9. **Operations Playbook** - Day-to-day operations and troubleshooting

Each document focuses on a specific aspect of the processing engine, providing a modular approach to understanding the system.

## 9. Related Documentation

- [Context Object Structure](../../context-object/context-object-v1.0.md)
- [Conversations DB Schema](../../db/conversations-db-schema-v1.0.md)
- [AWS Reference Management](../../secrets-manager/aws-referencing-v1.0.md)
- [Error Tracking Strategies](../error-tracking-strategies-v1.0.md)
- [CloudWatch Dashboard Setup](../../cloudwatch-dashboard/cloudwatch-dashboard-setup-v1.0.md) 

## 10. Lambda Function Configuration

The WhatsApp Processing Engine Lambda function is configured with specific settings to ensure optimal performance, reliability, and scalability:

### 10.1 Environment Variables

| Environment Variable | Description | Value | Purpose |
|----------------------|-------------|-------|---------|
| `CONVERSATIONS_TABLE` | DynamoDB table for conversations | `template-sender-conversations` | Store conversation data |
| `WHATSAPP_QUEUE_URL` | SQS queue URL | `https://sqs.{region}.amazonaws.com/{account}/whatsapp-queue` | Process incoming messages |
| `SECRETS_MANAGER_REGION` | AWS region for Secrets Manager | `us-east-1` | Access Twilio and OpenAI credentials |
| `LOG_LEVEL` | Logging verbosity | `INFO` | Control logging detail (INFO, DEBUG, ERROR) |
| `OPENAI_MAX_TOKENS` | Maximum tokens for OpenAI | `2048` | Limit token usage for cost control |
| `DYNAMO_MAX_RETRY` | DynamoDB retry count | `3` | Configure retry behavior for DynamoDB |
| `SQS_HEARTBEAT_INTERVAL_MS` | SQS visibility extension interval | `300000` | Configure heartbeat (5 minutes) |
| `OPENAI_DEFAULT_TIMEOUT_MS` | OpenAI API timeout | `60000` | Configure API timeout (60 seconds) |
| `NODE_OPTIONS` | Node.js runtime options | `--enable-source-maps` | Improve error stack traces |
| `USE_ADAPTIVE_RATE_LIMITING` | Rate limiting flag | `true` | Enable adaptive rate limiting |

### 10.2 Memory and Timeout Configuration

The Lambda function is configured with appropriate memory and timeout settings:

| Setting | Value | Rationale |
|---------|-------|-----------|
| Memory Size | 1024 MB | Provides sufficient memory for processing messages with large context objects |
| Timeout | 15 minutes | Maximum allowed Lambda timeout; provides ample time for long-running OpenAI operations |
| Ephemeral Storage | 512 MB | Default storage is sufficient for processing needs |

### 10.3 Concurrency Configuration

To control the rate of processing and prevent overloading downstream services:

| Setting | Value | Rationale |
|---------|-------|-----------|
| Reserved Concurrency | 25 | Limits simultaneous executions to prevent overwhelming OpenAI/Twilio APIs |
| Provisioned Concurrency | 0 | Not required; cold starts are acceptable for this workload |
| Asynchronous Invocation | Disabled | Uses SQS for message queue processing instead |

### 10.4 Networking Configuration

The Lambda function uses VPC configuration to access private resources:

| Setting | Value | Rationale |
|---------|-------|-----------|
| VPC | Application VPC | Provides access to VPC-isolated resources if needed |
| Subnets | Private subnets | Isolates Lambda functions from direct internet access |
| Security Group | Lambda-SG | Controls network access to/from Lambda functions |

## 11. Infrastructure as Code

The WhatsApp Processing Engine infrastructure is defined as code using AWS CDK, enabling consistent and repeatable deployments:

### 11.1 CDK Stack Implementation

The following is the core infrastructure defined in the CDK stack:

```typescript
export class WhatsAppProcessingStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // DynamoDB table for conversations
    const conversationsTable = new dynamodb.Table(this, 'ConversationsTable', {
      tableName: 'template-sender-conversations',
      partitionKey: { name: 'recipient_tel', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'conversation_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN
    });
    
    // Add GSI for company_id lookups
    conversationsTable.addGlobalSecondaryIndex({
      indexName: 'company-id-index',
      partitionKey: { name: 'company_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL
    });

    // Create Dead Letter Queue
    const whatsappDLQ = new sqs.Queue(this, 'WhatsAppDLQ', {
      queueName: 'whatsapp-processing-dlq',
      retentionPeriod: cdk.Duration.days(14),
      encryption: sqs.QueueEncryption.KMS_MANAGED
    });

    // Create main WhatsApp SQS queue
    const whatsappQueue = new sqs.Queue(this, 'WhatsAppQueue', {
      queueName: 'whatsapp-processing-queue',
      visibilityTimeout: cdk.Duration.seconds(600), // 10 minutes
      receiveMessageWaitTime: cdk.Duration.seconds(20), // Long polling
      deadLetterQueue: {
        queue: whatsappDLQ,
        maxReceiveCount: 3
      },
      encryption: sqs.QueueEncryption.KMS_MANAGED
    });

    // Create IAM role with required permissions
    const processingLambdaRole = new iam.Role(this, 'WhatsAppProcessingLambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole')
      ]
    });

    // Add custom IAM policies
    processingLambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'dynamodb:GetItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:Query',
        'dynamodb:BatchWriteItem'
      ],
      resources: [
        conversationsTable.tableArn,
        `${conversationsTable.tableArn}/index/*`
      ]
    }));

    processingLambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'sqs:ReceiveMessage',
        'sqs:DeleteMessage',
        'sqs:GetQueueAttributes',
        'sqs:ChangeMessageVisibility'
      ],
      resources: [whatsappQueue.queueArn]
    }));

    processingLambdaRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        'secretsmanager:GetSecretValue'
      ],
      resources: [
        `arn:aws:secretsmanager:${this.region}:${this.account}:secret:whatsapp/*`,
        `arn:aws:secretsmanager:${this.region}:${this.account}:secret:openai/*`
      ]
    }));

    // Create Lambda function
    const whatsappProcessingLambda = new lambda.Function(this, 'WhatsAppProcessingFunction', {
      runtime: lambda.Runtime.NODEJS_16_X,
      handler: 'index.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../lambda/whatsapp-processing')),
      memorySize: 1024,
      timeout: cdk.Duration.minutes(15),
      environment: {
        CONVERSATIONS_TABLE: conversationsTable.tableName,
        WHATSAPP_QUEUE_URL: whatsappQueue.queueUrl,
        LOG_LEVEL: 'INFO',
        OPENAI_MAX_TOKENS: '2048',
        DYNAMO_MAX_RETRY: '3',
        SQS_HEARTBEAT_INTERVAL_MS: '300000',
        OPENAI_DEFAULT_TIMEOUT_MS: '60000',
        USE_ADAPTIVE_RATE_LIMITING: 'true',
        NODE_OPTIONS: '--enable-source-maps'
      },
      role: processingLambdaRole,
      tracing: lambda.Tracing.ACTIVE,
      reservedConcurrentExecutions: 25,
      logRetention: logs.RetentionDays.ONE_MONTH
    });

    // Set up SQS as event source
    whatsappProcessingLambda.addEventSource(new SqsEventSource(whatsappQueue, {
      batchSize: 1,
      maxBatchingWindow: cdk.Duration.seconds(0)
    }));

    // Create CloudWatch alarm for DLQ messages
    const dlqAlarm = new cloudwatch.Alarm(this, 'WhatsAppDLQAlarm', {
      metric: whatsappDLQ.metricApproximateNumberOfMessagesVisible(),
      evaluationPeriods: 1,
      threshold: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      alarmDescription: 'Alert when messages are sent to WhatsApp Processing DLQ'
    });

    // Create SNS topic for alarms
    const alarmTopic = new sns.Topic(this, 'WhatsAppProcessingAlarms', {
      displayName: 'WhatsApp Processing Engine Alarms'
    });

    // Add alarm action
    dlqAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alarmTopic));

    // Create dashboard
    const dashboard = new cloudwatch.Dashboard(this, 'WhatsAppProcessingDashboard', {
      dashboardName: 'WhatsAppProcessingEngine'
    });

    // Add widgets to dashboard (additional widgets defined in dashboard configuration)
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Messages Processed',
        left: [whatsappProcessingLambda.metricInvocations()],
        width: 12
      }),
      new cloudwatch.GraphWidget({
        title: 'Processing Errors',
        left: [whatsappProcessingLambda.metricErrors()],
        width: 12
      })
    );

    // Outputs
    new cdk.CfnOutput(this, 'ConversationsTableName', {
      value: conversationsTable.tableName,
      description: 'DynamoDB table for WhatsApp conversations'
    });

    new cdk.CfnOutput(this, 'WhatsAppQueueUrl', {
      value: whatsappQueue.queueUrl,
      description: 'SQS Queue URL for WhatsApp processing'
    });

    new cdk.CfnOutput(this, 'WhatsAppProcessingLambdaArn', {
      value: whatsappProcessingLambda.functionArn,
      description: 'ARN of WhatsApp processing Lambda function'
    });
  }
}
```

### 11.2 Infrastructure Deployment

The infrastructure is deployed using the AWS CDK CLI:

```bash
# Install dependencies
npm install

# Synthesize CloudFormation template
cdk synth

# Deploy to development environment
cdk deploy -c environment=dev

# Deploy to production environment
cdk deploy -c environment=prod
```

### 11.3 CI/CD Integration

The infrastructure deployment is integrated with CI/CD pipelines using GitHub Actions:

```yaml
name: Deploy WhatsApp Processing Engine

on:
  push:
    branches:
      - main
    paths:
      - 'infra/**'
      - 'lambda/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm test
      
      - name: Deploy with CDK
        run: npx cdk deploy --require-approval never -c environment=prod
```

These infrastructure configurations ensure consistent, reproducible deployments across environments and enable infrastructure changes to be version-controlled and peer-reviewed alongside application code. 