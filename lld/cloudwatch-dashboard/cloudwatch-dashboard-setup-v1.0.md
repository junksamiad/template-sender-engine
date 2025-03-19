# CloudWatch Dashboard Setup for Channel Router

This document outlines the CloudWatch dashboard configuration for monitoring the Channel Router system and its components.

## Main Overview Dashboard

The main dashboard provides a comprehensive view of the entire Channel Router system, including all key components and their metrics.

```typescript
// Main Channel Router Dashboard
const mainDashboard = new cloudwatch.Dashboard(this, 'ChannelRouterDashboard', {
  dashboardName: 'ChannelRouter-Overview',
  periodOverride: cloudwatch.PeriodOverride.AUTO
});

mainDashboard.addWidgets(
  // Header with system status
  new cloudwatch.TextWidget({
    markdown: '# Channel Router System Overview\nKey metrics for all components',
    width: 24,
    height: 2
  }),
  
  // API Gateway Section
  new cloudwatch.TextWidget({
    markdown: '## API Gateway',
    width: 24,
    height: 1
  }),
  new cloudwatch.GraphWidget({
    title: 'Request Volume',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/ApiGateway',
        metricName: 'Count',
        dimensionsMap: {
          ApiName: 'ChannelRouterApi'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 8,
    height: 6
  }),
  new cloudwatch.GraphWidget({
    title: 'Throttled Requests',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/ApiGateway',
        metricName: 'ThrottleCount',
        dimensionsMap: {
          ApiName: 'ChannelRouterApi'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 8,
    height: 6
  }),
  new cloudwatch.GraphWidget({
    title: 'API Errors',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/ApiGateway',
        metricName: '4XXError',
        dimensionsMap: {
          ApiName: 'ChannelRouterApi'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/ApiGateway',
        metricName: '5XXError',
        dimensionsMap: {
          ApiName: 'ChannelRouterApi'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 8,
    height: 6
  }),
  
  // Lambda Section
  new cloudwatch.TextWidget({
    markdown: '## Lambda Functions',
    width: 24,
    height: 1
  }),
  new cloudwatch.GraphWidget({
    title: 'Invocations & Errors',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/Lambda',
        metricName: 'Invocations',
        dimensionsMap: {
          FunctionName: 'ChannelRouterFunction'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      })
    ],
    right: [
      new cloudwatch.Metric({
        namespace: 'AWS/Lambda',
        metricName: 'Errors',
        dimensionsMap: {
          FunctionName: 'ChannelRouterFunction'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 8,
    height: 6
  }),
  new cloudwatch.GraphWidget({
    title: 'Duration',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/Lambda',
        metricName: 'Duration',
        dimensionsMap: {
          FunctionName: 'ChannelRouterFunction'
        },
        statistic: 'Average',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/Lambda',
        metricName: 'Duration',
        dimensionsMap: {
          FunctionName: 'ChannelRouterFunction'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 8,
    height: 6
  }),
  new cloudwatch.GraphWidget({
    title: 'Concurrent Executions',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/Lambda',
        metricName: 'ConcurrentExecutions',
        dimensionsMap: {
          FunctionName: 'ChannelRouterFunction'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 8,
    height: 6
  }),
  
  // SQS Section
  new cloudwatch.TextWidget({
    markdown: '## SQS Queues',
    width: 24,
    height: 1
  }),
  new cloudwatch.GraphWidget({
    title: 'WhatsApp Queue - Messages',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'NumberOfMessagesReceived',
        dimensionsMap: {
          QueueName: 'WhatsAppQueue'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'NumberOfMessagesDeleted',
        dimensionsMap: {
          QueueName: 'WhatsAppQueue'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 8,
    height: 6
  }),
  new cloudwatch.GraphWidget({
    title: 'WhatsApp Queue - Age & Depth',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'ApproximateAgeOfOldestMessage',
        dimensionsMap: {
          QueueName: 'WhatsAppQueue'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      })
    ],
    right: [
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'ApproximateNumberOfMessagesVisible',
        dimensionsMap: {
          QueueName: 'WhatsAppQueue'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 8,
    height: 6
  }),
  new cloudwatch.GraphWidget({
    title: 'Dead Letter Queue - Messages',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'ApproximateNumberOfMessagesVisible',
        dimensionsMap: {
          QueueName: 'WhatsAppDLQ'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 8,
    height: 6
  }),
  
  // DynamoDB Section
  new cloudwatch.TextWidget({
    markdown: '## DynamoDB',
    width: 24,
    height: 1
  }),
  new cloudwatch.GraphWidget({
    title: 'Read Capacity Units',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/DynamoDB',
        metricName: 'ConsumedReadCapacityUnits',
        dimensionsMap: {
          TableName: 'wa_company_data'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 8,
    height: 6
  }),
  new cloudwatch.GraphWidget({
    title: 'Write Capacity Units',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/DynamoDB',
        metricName: 'ConsumedWriteCapacityUnits',
        dimensionsMap: {
          TableName: 'wa_company_data'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 8,
    height: 6
  }),
  new cloudwatch.GraphWidget({
    title: 'DynamoDB Errors',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/DynamoDB',
        metricName: 'SystemErrors',
        dimensionsMap: {
          TableName: 'wa_company_data'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/DynamoDB',
        metricName: 'UserErrors',
        dimensionsMap: {
          TableName: 'wa_company_data'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 8,
    height: 6
  }),
  
  // Custom Metrics Section
  new cloudwatch.TextWidget({
    markdown: '## Custom Metrics',
    width: 24,
    height: 1
  }),
  new cloudwatch.GraphWidget({
    title: 'OpenAI API Response Times',
    left: [
      new cloudwatch.Metric({
        namespace: 'ChannelRouter',
        metricName: 'OpenAIResponseTime',
        statistic: 'Average',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'ChannelRouter',
        metricName: 'OpenAIResponseTime',
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  }),
  new cloudwatch.GraphWidget({
    title: 'Message Processing Time',
    left: [
      new cloudwatch.Metric({
        namespace: 'ChannelRouter',
        metricName: 'MessageProcessingTime',
        statistic: 'Average',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'ChannelRouter',
        metricName: 'MessageProcessingTime',
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  })
);
```

## Component-Specific Dashboards

In addition to the main dashboard, more detailed dashboards for each component provide deeper insights.

### DynamoDB Dashboard

```typescript
const dynamoDbDashboard = new cloudwatch.Dashboard(this, 'DynamoDBDashboard', {
  dashboardName: 'ChannelRouter-DynamoDB'
});

dynamoDbDashboard.addWidgets(
  // Header
  new cloudwatch.TextWidget({
    markdown: '# DynamoDB Monitoring Dashboard\nDetailed metrics for wa_company_data table',
    width: 24,
    height: 2
  }),
  
  // Capacity metrics
  new cloudwatch.GraphWidget({
    title: 'Read Capacity Units (Detailed)',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/DynamoDB',
        metricName: 'ConsumedReadCapacityUnits',
        dimensionsMap: {
          TableName: 'wa_company_data'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/DynamoDB',
        metricName: 'ConsumedReadCapacityUnits',
        dimensionsMap: {
          TableName: 'wa_company_data'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  }),
  
  // Latency metrics
  new cloudwatch.GraphWidget({
    title: 'DynamoDB Operation Latency',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/DynamoDB',
        metricName: 'SuccessfulRequestLatency',
        dimensionsMap: {
          TableName: 'wa_company_data',
          Operation: 'GetItem'
        },
        statistic: 'Average',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/DynamoDB',
        metricName: 'SuccessfulRequestLatency',
        dimensionsMap: {
          TableName: 'wa_company_data',
          Operation: 'Query'
        },
        statistic: 'Average',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  }),
  
  // Throttling metrics
  new cloudwatch.GraphWidget({
    title: 'Throttled Requests',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/DynamoDB',
        metricName: 'ReadThrottleEvents',
        dimensionsMap: {
          TableName: 'wa_company_data'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/DynamoDB',
        metricName: 'WriteThrottleEvents',
        dimensionsMap: {
          TableName: 'wa_company_data'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  })
);
```

### SQS and DLQ Dashboard

```typescript
const sqsDashboard = new cloudwatch.Dashboard(this, 'SQSDashboard', {
  dashboardName: 'ChannelRouter-SQS'
});

sqsDashboard.addWidgets(
  // Header
  new cloudwatch.TextWidget({
    markdown: '# SQS Monitoring Dashboard\nDetailed metrics for queues and DLQs',
    width: 24,
    height: 2
  }),
  
  // WhatsApp Queue metrics
  new cloudwatch.TextWidget({
    markdown: '## WhatsApp Queue',
    width: 24,
    height: 1
  }),
  new cloudwatch.GraphWidget({
    title: 'Message Throughput',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'NumberOfMessagesSent',
        dimensionsMap: {
          QueueName: 'WhatsAppQueue'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'NumberOfMessagesReceived',
        dimensionsMap: {
          QueueName: 'WhatsAppQueue'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'NumberOfMessagesDeleted',
        dimensionsMap: {
          QueueName: 'WhatsAppQueue'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  }),
  new cloudwatch.GraphWidget({
    title: 'Queue Depth',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'ApproximateNumberOfMessagesVisible',
        dimensionsMap: {
          QueueName: 'WhatsAppQueue'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'ApproximateNumberOfMessagesNotVisible',
        dimensionsMap: {
          QueueName: 'WhatsAppQueue'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  }),
  
  // WhatsApp DLQ metrics
  new cloudwatch.TextWidget({
    markdown: '## WhatsApp Dead Letter Queue',
    width: 24,
    height: 1
  }),
  new cloudwatch.GraphWidget({
    title: 'DLQ Messages',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'ApproximateNumberOfMessagesVisible',
        dimensionsMap: {
          QueueName: 'WhatsAppDLQ'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  }),
  new cloudwatch.GraphWidget({
    title: 'DLQ Message Age',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'ApproximateAgeOfOldestMessage',
        dimensionsMap: {
          QueueName: 'WhatsAppDLQ'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  }),
  
  // Similar sections for Email and SMS queues
  // ...
);
```

## Custom Metrics Implementation

To track custom metrics like OpenAI response times, add code to your Lambda functions:

```javascript
// In your Lambda function that processes messages
const AWS = require('aws-sdk');
const cloudwatch = new AWS.CloudWatch();

async function processWithOpenAI(message) {
  const startTime = Date.now();
  
  try {
    // Call OpenAI API
    const response = await callOpenAI(message);
    
    // Record the response time
    const responseTime = Date.now() - startTime;
    await cloudwatch.putMetricData({
      Namespace: 'ChannelRouter',
      MetricData: [
        {
          MetricName: 'OpenAIResponseTime',
          Value: responseTime,
          Unit: 'Milliseconds',
          Dimensions: [
            {
              Name: 'FunctionName',
              Value: process.env.AWS_LAMBDA_FUNCTION_NAME
            }
          ]
        }
      ]
    }).promise();
    
    return response;
  } catch (error) {
    // Handle error and still record the time
    const responseTime = Date.now() - startTime;
    // Record error metric and response time
    // ...
    throw error;
  }
}
```

## Alarm Integration

CloudWatch dashboards can display alarm states:

```typescript
// Create an alarm
const dlqAlarm = new cloudwatch.Alarm(this, 'DLQMessagesAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'AWS/SQS',
    metricName: 'ApproximateNumberOfMessagesVisible',
    dimensionsMap: {
      QueueName: 'WhatsAppDLQ'
    },
    statistic: 'Maximum',
    period: cdk.Duration.minutes(1)
  }),
  threshold: 1,
  evaluationPeriods: 1,
  alarmDescription: 'Messages detected in WhatsApp DLQ'
});

// Add alarm status widget to dashboard
mainDashboard.addWidgets(
  new cloudwatch.AlarmWidget({
    title: 'Critical Alarms',
    alarms: [dlqAlarm],
    width: 24,
    height: 6
  })
);
```

## Recommended Alarms

Set up the following alarms for proactive monitoring:

1. **DLQ Messages Present**:
   - Trigger when any messages appear in a Dead Letter Queue
   - Indicates processing failures that need investigation

2. **High API Error Rate**:
   - Trigger when 4XX or 5XX errors exceed a threshold (e.g., >5% of requests)
   - Indicates client or server-side issues

3. **Lambda Function Errors**:
   - Trigger when Lambda errors exceed a threshold
   - Indicates code or configuration issues

4. **Queue Age Threshold**:
   - Trigger when the oldest message exceeds a time threshold (e.g., >5 minutes)
   - Indicates processing bottlenecks

5. **DynamoDB Throttling**:
   - Trigger when read or write throttling events occur
   - Indicates capacity issues

6. **Lambda Duration Threshold**:
   - Trigger when Lambda execution time approaches timeout limit
   - Indicates potential timeout issues

## Dashboard Creation in AWS Console

To create dashboards manually in the AWS Console:

1. Go to CloudWatch in the AWS Console
2. Select "Dashboards" from the left navigation
3. Click "Create dashboard"
4. Name your dashboard (e.g., "ChannelRouter-Overview")
5. Add widgets by selecting the widget type (graph, number, text, etc.)
6. For each graph widget:
   - Search for the metrics you want to display
   - Select the appropriate statistic (Sum, Average, Maximum, etc.)
   - Configure the time period and layout
7. Arrange widgets by dragging and dropping
8. Save the dashboard

## Dashboard Sharing and Access

To ensure your team has access to these dashboards:

1. **IAM Permissions**:
   - Grant appropriate CloudWatch dashboard permissions to team members
   - Consider creating a specific IAM role for monitoring

2. **Dashboard Sharing**:
   - You can share dashboard links with team members
   - Consider setting up a central monitoring station with dashboards displayed

3. **Cross-Account Access**:
   - If you have multiple AWS accounts, you can share dashboards across accounts

## Implementation in Your Project

To add these dashboards to your Channel Router project:

1. **Add to CDK Stack**:
   - Include the dashboard definitions in your main CDK stack
   - Reference the actual resources you're creating (queues, functions, etc.)

2. **Deploy with Infrastructure**:
   - The dashboards will be created when you deploy your CDK stack
   - Any updates to the dashboards will be applied on subsequent deployments

3. **Customize Based on Needs**:
   - Start with the basic dashboard shown above
   - Add or remove widgets based on your specific monitoring needs
   - Refine over time as you gain operational experience

## Best Practices for Monitoring

1. **Focus on Key Metrics**:
   - Identify the most important metrics for your application
   - Don't overwhelm dashboards with too many metrics

2. **Set Appropriate Thresholds**:
   - Base alarm thresholds on historical data and business requirements
   - Avoid alarm fatigue from too many false positives

3. **Use Composite Alarms**:
   - Combine multiple conditions for more meaningful alerts
   - Reduce noise by triggering only on significant events

4. **Document Runbooks**:
   - Create clear procedures for responding to each alarm
   - Include troubleshooting steps and escalation paths

5. **Regular Reviews**:
   - Periodically review dashboard effectiveness
   - Adjust metrics and thresholds based on operational experience 