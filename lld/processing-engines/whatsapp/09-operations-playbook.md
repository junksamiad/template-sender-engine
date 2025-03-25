# WhatsApp Processing Engine - Operations Playbook

> **Part 9 of 9 in the WhatsApp Processing Engine documentation series**

## 1. Introduction

This Operations Playbook provides guidelines, procedures, and best practices for operating and maintaining the WhatsApp Processing Engine in production. The playbook covers common operational tasks, troubleshooting scenarios, and incident response procedures.

## 2. Operational Responsibilities

The core operational responsibilities for the WhatsApp Processing Engine include:

1. **Monitoring**: Continuously monitoring the system's health and performance
2. **Maintenance**: Performing routine maintenance tasks
3. **Troubleshooting**: Diagnosing and resolving issues
4. **Scaling**: Adjusting capacity based on demand
5. **Security**: Ensuring secure operation and credential management
6. **Backup & Recovery**: Maintaining data integrity and recovery procedures
7. **Updates**: Applying system updates and patches

## 3. Routine Operational Tasks

### 3.1 Daily Operations

| Task | Description | Responsible Team | Frequency |
|------|-------------|------------------|-----------|
| Health Check | Review operational dashboards and alerts | DevOps | Daily |
| DLQ Monitoring | Check for messages in Dead Letter Queue | DevOps | Daily |
| Error Review | Review error logs and metrics | DevOps | Daily |
| Performance Review | Check processing times and bottlenecks | DevOps | Daily |
| Token Usage | Monitor OpenAI token consumption | DevOps/Finance | Daily |

### 3.2 Weekly Operations

| Task | Description | Responsible Team | Frequency |
|------|-------------|------------------|-----------|
| Capacity Planning | Review usage trends and adjust capacity | DevOps | Weekly |
| Template Review | Check template approval statuses | Business Operations | Weekly |
| Cost Analysis | Analyze costs for AI services and messaging | Finance | Weekly |
| DynamoDB Scaling | Review table provisioning and throughput | DevOps | Weekly |
| Security Review | Review access logs and security alerts | Security | Weekly |

### 3.3 Monthly Operations

| Task | Description | Responsible Team | Frequency |
|------|-------------|------------------|-----------|
| Service Limits | Check and adjust AWS service limits | DevOps | Monthly |
| Dependency Updates | Update dependencies and libraries | Development | Monthly |
| Performance Analysis | Detailed analysis of system performance | DevOps/Development | Monthly |
| Disaster Recovery Test | Test recovery procedures | DevOps | Monthly |
| Documentation Review | Review and update operational documentation | Development/DevOps | Monthly |

## 4. Monitoring Procedure

### 4.1 Key Monitoring Points

1. **CloudWatch Dashboards**: Primary monitoring interface
2. **Alarms**: Configured for critical thresholds
3. **Logs**: Structured logs for detailed analysis
4. **X-Ray Traces**: For performance and error analysis
5. **SQS Queue Metrics**: Message volume and processing rates
6. **DynamoDB Metrics**: Throughput and error rates
7. **Lambda Metrics**: Invocations, errors, and duration

### 4.2 Alert Response Procedure

For each triggered alert, follow these steps:

1. **Acknowledge**: Acknowledge the alert in the monitoring system
2. **Assess Impact**: Determine the business impact and severity
3. **Investigate**: Use logs, traces, and metrics to identify the cause
4. **Mitigate**: Apply mitigation steps from the playbook
5. **Resolve**: Implement a resolution
6. **Document**: Record the incident, cause, and resolution
7. **Follow-up**: Create tickets for any required follow-up work

## 5. Troubleshooting Guides

### 5.1 High Error Rates

**Symptoms**: Increased error rate in CloudWatch metrics, alerts for failed messages

**Troubleshooting Steps**:

1. Check CloudWatch Logs Insights for error patterns:
   ```
   fields @timestamp, message.error_category, message.error_message
   | filter level = 'ERROR'
   | stats count(*) as error_count by message.error_category
   | sort error_count desc
   ```

2. Analyze X-Ray traces for failing requests to identify common patterns

3. Check for external service issues:
   - OpenAI service status
   - Twilio service status
   - AWS service health dashboard

4. Check for recent deployments or changes

5. Look for resource constraints:
   - Lambda throttling
   - DynamoDB throttling
   - SQS visibility timeout issues

**Resolution Actions**:

1. For OpenAI issues:
   - Implement circuit breaker if not already active
   - Check API usage and limits
   - Verify API key validity

2. For Twilio issues:
   - Check account balance
   - Verify WhatsApp Business Account status
   - Check for message template rejections

3. For AWS service issues:
   - Adjust capacities/limits if needed
   - Implement backoff strategies
   - Consider fallback mechanisms

### 5.2 SQS Messages Stuck

**Symptoms**: Messages not being processed, stuck in SQS queue

**Troubleshooting Steps**:

1. Check Lambda CloudWatch Logs for processing errors

2. Verify Lambda concurrency and throttling metrics

3. Check if the SQS visibility timeout is appropriate:
   - Too short: Messages become visible before processing completes
   - Too long: Failed processing delays retry

4. Check for heartbeat pattern failures:
   ```
   fields @timestamp, message
   | filter message like /heartbeat/
   | sort @timestamp desc
   ```

5. Verify DynamoDB availability and throughput

**Resolution Actions**:

1. Adjust SQS visibility timeout if needed

2. Update Lambda concurrency limits

3. Manually purge problematic messages if identified

4. Restart processing with corrected configuration

### 5.3 High Processing Latency

**Symptoms**: Increased message processing time, delayed responses

**Troubleshooting Steps**:

1. Check processing time metrics by component:
   - OpenAI API latency
   - Twilio API latency
   - DynamoDB operation latency
   - Lambda duration

2. Examine X-Ray traces to identify slow components

3. Check for cold start patterns in Lambda executions

4. Analyze concurrent execution patterns

**Resolution Actions**:

1. Adjust Lambda memory configuration for better performance

2. Implement or tune caching strategies

3. Optimize DynamoDB access patterns

4. Consider Provisioned Concurrency for Lambda functions

5. Optimize OpenAI requests (prompt engineering, model selection)

### 5.4 DynamoDB Throughput Issues

**Symptoms**: ProvisionedThroughputExceededException, high latency on DynamoDB operations

**Troubleshooting Steps**:

1. Check CloudWatch metrics for consumed read/write capacity units

2. Look for hot partitions in DynamoDB

3. Analyze access patterns in X-Ray traces

4. Check for inefficient queries or scans

**Resolution Actions**:

1. Increase provisioned capacity or switch to on-demand

2. Implement or adjust caching strategies

3. Review and optimize key design for better distribution

4. Implement backoff strategy for retries

### 5.5 Template Approval Issues

**Symptoms**: WhatsApp templates stuck in PENDING or frequently REJECTED

**Troubleshooting Steps**:

1. Check template content against WhatsApp guidelines

2. Verify template error messages in Twilio console

3. Analyze template rejection patterns

**Resolution Actions**:

1. Revise templates according to feedback

2. Adjust template category if necessary

3. Simplify template content

4. Contact Twilio support for persistent issues

## 6. Scaling Procedures

### 6.1 Lambda Scaling

Lambda functions scale automatically, but configure the following:

```javascript
// CDK configuration for Lambda scaling
const processingLambda = new lambda.Function(this, 'WhatsAppProcessingLambda', {
  // ... other configuration ...
  reservedConcurrentExecutions: 100  // Adjust based on expected load
});

// For predictable workloads, consider Provisioned Concurrency
const provisioned = new lambda.ProvisionedConcurrency(this, 'ProvisionedConcurrency', {
  alias: alias,
  provisionedConcurrentExecutions: 10
});
```

### 6.2 DynamoDB Scaling

Configure DynamoDB auto-scaling:

```javascript
// CDK configuration for DynamoDB scaling
const table = new dynamodb.Table(this, 'ConversationTable', {
  partitionKey: { name: 'recipient_tel', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'conversation_id', type: dynamodb.AttributeType.STRING },
  billingMode: dynamodb.BillingMode.PROVISIONED,
  readCapacity: 5,
  writeCapacity: 5
});

// Add auto-scaling
const readScaling = table.autoScaleReadCapacity({
  minCapacity: 5,
  maxCapacity: 100
});

readScaling.scaleOnUtilization({
  targetUtilizationPercent: 70
});

const writeScaling = table.autoScaleWriteCapacity({
  minCapacity: 5,
  maxCapacity: 100
});

writeScaling.scaleOnUtilization({
  targetUtilizationPercent: 70
});
```

### 6.3 SQS Scaling Considerations

SQS scales automatically, but consider these configurations:

1. **Message Retention Period**: Configure based on business requirements
2. **Visibility Timeout**: Adjust to match processing time plus buffer
3. **DLQ Settings**: Configure maxReceiveCount appropriately
4. **Lambda Concurrency**: Balance with downstream service limits

## 7. Backup and Recovery

### 7.1 DynamoDB Backup

Enable Point-in-Time Recovery (PITR) for critical tables:

```javascript
// CDK configuration for DynamoDB PITR
const table = new dynamodb.Table(this, 'ConversationTable', {
  // ... other configuration ...
  pointInTimeRecovery: true
});
```

Create scheduled backups:

```javascript
// AWS CLI command for creating on-demand backup
aws dynamodb create-backup --table-name wa_conversation --backup-name "daily-backup-$(date +%Y-%m-%d)"

// Schedule with EventBridge
const rule = new events.Rule(this, 'BackupRule', {
  schedule: events.Schedule.expression('cron(0 0 * * ? *)')  // Daily at midnight
});

rule.addTarget(new targets.LambdaFunction(backupLambda));
```

### 7.2 Recovery Procedures

#### 7.2.1 DynamoDB Recovery

To restore from PITR:

```bash
# Identify the point in time to restore to
TIME_TO_RESTORE="2023-06-01T13:15:00Z"

# Create restored table
aws dynamodb restore-table-to-point-in-time \
  --source-table-name wa_conversation \
  --target-table-name wa_conversation_restored \
  --use-latest-restorable-time \
  --sse-specification-override Enabled=true
```

To restore from backup:

```bash
# List available backups
aws dynamodb list-backups --table-name wa_conversation

# Restore from backup
aws dynamodb restore-table-from-backup \
  --target-table-name wa_conversation_restored \
  --backup-arn "arn:aws:dynamodb:us-east-1:123456789012:table/wa_conversation/backup/01234567890123-abcdef"
```

#### 7.2.2 Reprocessing Failed Messages

To reprocess messages from DLQ:

```bash
# Create Lambda function to move messages from DLQ to main queue
# Example implementation:

exports.handler = async (event) => {
  const sqs = new AWS.SQS();
  
  // Get messages from DLQ
  const receiveParams = {
    QueueUrl: process.env.DLQ_URL,
    MaxNumberOfMessages: 10,
    VisibilityTimeout: 30
  };
  
  const receiveResult = await sqs.receiveMessage(receiveParams).promise();
  
  if (!receiveResult.Messages || receiveResult.Messages.length === 0) {
    return { processed: 0 };
  }
  
  // Process each message
  for (const message of receiveResult.Messages) {
    // Send to main queue
    await sqs.sendMessage({
      QueueUrl: process.env.MAIN_QUEUE_URL,
      MessageBody: message.Body
    }).promise();
    
    // Delete from DLQ
    await sqs.deleteMessage({
      QueueUrl: process.env.DLQ_URL,
      ReceiptHandle: message.ReceiptHandle
    }).promise();
  }
  
  return { processed: receiveResult.Messages.length };
};
```

## 8. Security Operations

### 8.1 Credential Rotation

Rotate OpenAI API keys quarterly or after security incidents:

1. Create new API key in OpenAI dashboard
2. Update the key in AWS Secrets Manager:

```bash
# Update OpenAI API key
aws secretsmanager update-secret \
  --secret-id "OpenAI/ApiKey" \
  --secret-string '{"api_key":"sk-newkey..."}'
```

Rotate Twilio credentials quarterly:

1. Create new API keys in Twilio console
2. Update the keys in AWS Secrets Manager:

```bash
# Update Twilio credentials
aws secretsmanager update-secret \
  --secret-id "Twilio/ApiCredentials" \
  --secret-string '{"account_sid":"AC123...","auth_token":"abcd..."}'
```

### 8.2 Security Monitoring

Monitor for suspicious activities:

1. Set up CloudTrail for API activity monitoring
2. Create alerts for suspicious patterns:
   - Multiple failed authentication attempts
   - Unusual API call patterns
   - Access from unusual IP addresses
   - Credential access patterns

3. Regular security reviews:
   - IAM permissions audit
   - Secrets access audit
   - Security group configuration

## 9. Incident Response

### 9.1 Incident Severity Levels

| Level | Description | Response Time | Escalation |
|-------|-------------|---------------|------------|
| P1 | Critical service outage | Immediate | DevOps Manager, CTO |
| P2 | Partial service degradation | 30 minutes | DevOps Manager |
| P3 | Non-critical component failure | 2 hours | On-call Engineer |
| P4 | Minor issues, no service impact | 1 business day | Development Team |

### 9.2 Incident Response Workflow

1. **Detect**: Identify the incident through alerts or reports
2. **Classify**: Determine severity and impact
3. **Notify**: Alert appropriate team members
4. **Contain**: Limit the impact of the incident
5. **Investigate**: Identify root cause
6. **Resolve**: Implement solution
7. **Recover**: Restore normal operations
8. **Document**: Record the incident and response
9. **Review**: Conduct post-incident analysis

### 9.3 Communication Templates

#### P1/P2 Incident Initial Communication

```
INCIDENT NOTIFICATION: [Incident ID]
Status: Investigating
Impact: [Brief description of impact]
Actions: [Current actions being taken]
Updates: Will provide update in [timeframe]
```

#### Incident Update

```
INCIDENT UPDATE: [Incident ID]
Status: [Investigating/Identified/Resolving/Resolved]
Impact: [Updated impact assessment]
Root Cause: [If identified]
Actions: [Current actions being taken]
ETA: [Estimated time to resolution if known]
```

#### Incident Resolution

```
INCIDENT RESOLVED: [Incident ID]
Status: Resolved at [timestamp]
Duration: [Total incident duration]
Impact: [Final impact assessment]
Root Cause: [Brief description]
Resolution: [Actions taken to resolve]
Follow-up: Post-incident review scheduled for [date/time]
```

## 10. Capacity Planning

### 10.1 Resource Utilization Analysis

Monitor key resource metrics:

1. **Lambda Concurrency**: Track max concurrent executions
2. **DynamoDB Capacity**: Monitor consumed RCUs/WCUs
3. **SQS Queue Depth**: Track message backlog
4. **API Call Volume**: Monitor external API call rates

### 10.2 Growth Planning

Calculate capacity requirements based on:

1. **Message Volume**: Messages per second
2. **Processing Time**: Average processing time per message
3. **Storage Requirements**: DynamoDB storage growth rate
4. **Token Usage**: OpenAI token consumption rate

Formula for Lambda concurrency requirements:

```
Required Concurrency = (Messages per second) × (Average duration in seconds)
```

Formula for DynamoDB capacity:

```
RCU = (Read operations per second) × (Item size in KB / 4 KB)
WCU = (Write operations per second) × (Item size in KB / 1 KB)
```

## 11. Disaster Recovery Plan

### 11.1 Recovery Time Objective (RTO)

Target recovery times by component:

| Component | RTO | Recovery Method |
|-----------|-----|-----------------|
| Lambda Functions | 15 minutes | Deployment from source control |
| DynamoDB Tables | 1 hour | PITR or backup restoration |
| SQS Queues | 30 minutes | Recreation from CloudFormation |
| Message Processing | 2 hours | Reprocessing from backlog |

### 11.2 Recovery Point Objective (RPO)

Data loss tolerance by component:

| Component | RPO | Protection Method |
|-----------|-----|------------------|
| Conversation Data | 24 hours | Daily backups, PITR |
| Message Queue | 4 days | SQS message retention |
| Templates | 7 days | Weekly backups |

### 11.3 Disaster Scenarios and Responses

#### Scenario 1: AWS Region Outage

1. Determine if multi-region failover is needed based on outage duration
2. If needed, activate standby infrastructure in secondary region
3. Update DNS or API Gateway routes to point to standby
4. Monitor recovery and service restoration

#### Scenario 2: Data Corruption

1. Identify scope of corruption
2. Stop processing to prevent further corruption
3. Restore affected data from last known good backup or PITR
4. Verify data integrity before resuming operations
5. Resume processing with validated configuration

#### Scenario 3: Security Breach

1. Isolate affected components
2. Revoke and rotate all credentials
3. Scan for unauthorized changes or backdoors
4. Restore from trusted backups if needed
5. Implement additional security controls
6. Resume operations with enhanced monitoring

## 12. Related Documentation

- [Overview and Architecture](./01-overview-architecture.md)
- [Monitoring and Observability](./09-monitoring-observability.md)
- [Error Handling Strategy](./08-error-handling-strategy.md) 