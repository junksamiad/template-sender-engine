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

## DLQ Monitoring and Processing Dashboard

```typescript
const dlqDashboard = new cloudwatch.Dashboard(this, 'DLQDashboard', {
  dashboardName: 'ChannelRouter-DLQ-Monitoring'
});

dlqDashboard.addWidgets(
  // Header
  new cloudwatch.TextWidget({
    markdown: '# Dead Letter Queue Monitoring\nMonitoring for DLQs and the DLQ Processor Lambda',
    width: 24,
    height: 2
  }),
  
  // DLQ Message Counts
  new cloudwatch.GraphWidget({
    title: 'DLQ Message Counts',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'ApproximateNumberOfMessagesVisible',
        dimensionsMap: {
          QueueName: 'WhatsAppDLQ'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'ApproximateNumberOfMessagesVisible',
        dimensionsMap: {
          QueueName: 'EmailDLQ'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'ApproximateNumberOfMessagesVisible',
        dimensionsMap: {
          QueueName: 'SMSDLQ'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  }),
  
  // DLQ Message Age
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
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'ApproximateAgeOfOldestMessage',
        dimensionsMap: {
          QueueName: 'EmailDLQ'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/SQS',
        metricName: 'ApproximateAgeOfOldestMessage',
        dimensionsMap: {
          QueueName: 'SMSDLQ'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  }),
  
  // DLQ Processor Lambda Section
  new cloudwatch.TextWidget({
    markdown: '## DLQ Processor Lambda',
    width: 24,
    height: 1
  }),
  
  // DLQ Processor Lambda Invocations & Errors
  new cloudwatch.GraphWidget({
    title: 'DLQ Processor Lambda Invocations & Errors',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/Lambda',
        metricName: 'Invocations',
        dimensionsMap: {
          FunctionName: 'DLQProcessorFunction'
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
          FunctionName: 'DLQProcessorFunction'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  }),
  
  // DLQ Processor Lambda Duration
  new cloudwatch.GraphWidget({
    title: 'DLQ Processor Lambda Duration',
    left: [
      new cloudwatch.Metric({
        namespace: 'AWS/Lambda',
        metricName: 'Duration',
        dimensionsMap: {
          FunctionName: 'DLQProcessorFunction'
        },
        statistic: 'Average',
        period: cdk.Duration.minutes(1)
      }),
      new cloudwatch.Metric({
        namespace: 'AWS/Lambda',
        metricName: 'Duration',
        dimensionsMap: {
          FunctionName: 'DLQProcessorFunction'
        },
        statistic: 'Maximum',
        period: cdk.Duration.minutes(1)
      })
    ],
    width: 12,
    height: 6
  }),
  
  // Custom Metrics for DLQ Processing
  new cloudwatch.GraphWidget({
    title: 'DLQ Processing Results',
    left: [
      new cloudwatch.Metric({
        namespace: 'ChannelRouter',
        metricName: 'DLQMessagesProcessed',
        statistic: 'Sum',
        period: cdk.Duration.minutes(5)
      }),
      new cloudwatch.Metric({
        namespace: 'ChannelRouter',
        metricName: 'DLQProcessingErrors',
        statistic: 'Sum',
        period: cdk.Duration.minutes(5)
      })
    ],
    width: 12,
    height: 6
  }),
  
  // Status Updates by DLQ Processor
  new cloudwatch.GraphWidget({
    title: 'Status Updates by DLQ Processor',
    left: [
      new cloudwatch.Metric({
        namespace: 'ChannelRouter',
        metricName: 'StatusUpdatedToFailed',
        dimensionsMap: {
          Channel: 'WhatsApp'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(5)
      }),
      new cloudwatch.Metric({
        namespace: 'ChannelRouter',
        metricName: 'StatusUpdatedToFailed',
        dimensionsMap: {
          Channel: 'Email'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(5)
      }),
      new cloudwatch.Metric({
        namespace: 'ChannelRouter',
        metricName: 'StatusUpdatedToFailed',
        dimensionsMap: {
          Channel: 'SMS'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(5)
      })
    ],
    width: 12,
    height: 6
  })
);
```

## DLQ Processor Lambda Implementation

The DLQ Processor Lambda is a dedicated function that processes messages from Dead Letter Queues and updates their status in DynamoDB. To implement custom metrics for this Lambda, add the following code:

```javascript
// In the DLQ Processor Lambda
const AWS = require('aws-sdk');
const cloudwatch = new AWS.CloudWatch();

// After processing a batch of DLQ messages
await cloudwatch.putMetricData({
  Namespace: 'ChannelRouter',
  MetricData: [
    {
      MetricName: 'DLQMessagesProcessed',
      Value: successfullyProcessedCount,
      Unit: 'Count'
    },
    {
      MetricName: 'DLQProcessingErrors',
      Value: errorCount,
      Unit: 'Count'
    },
    {
      MetricName: 'StatusUpdatedToFailed',
      Value: statusUpdateCount,
      Unit: 'Count',
      Dimensions: [
        {
          Name: 'Channel',
          Value: channelMethod // 'WhatsApp', 'Email', or 'SMS'
        }
      ]
    }
  ]
}).promise();
```

## DLQ Processor Lambda Alarms

```typescript
// Create an alarm for DLQ Processor Lambda errors
const dlqProcessorErrorAlarm = new cloudwatch.Alarm(this, 'DLQProcessorErrorAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'AWS/Lambda',
    metricName: 'Errors',
    dimensionsMap: {
      FunctionName: 'DLQProcessorFunction'
    },
    statistic: 'Sum',
    period: cdk.Duration.minutes(5)
  }),
  threshold: 1,
  evaluationPeriods: 1,
  alarmDescription: 'Errors in DLQ Processor Lambda'
});

// Create an alarm for DLQ Processor Lambda throttling
const dlqProcessorThrottlingAlarm = new cloudwatch.Alarm(this, 'DLQProcessorThrottlingAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'AWS/Lambda',
    metricName: 'Throttles',
    dimensionsMap: {
      FunctionName: 'DLQProcessorFunction'
    },
    statistic: 'Sum',
    period: cdk.Duration.minutes(5)
  }),
  threshold: 1,
  evaluationPeriods: 1,
  alarmDescription: 'Throttling in DLQ Processor Lambda'
});
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

## AI Assistant Configuration Monitoring

For applications that use OpenAI Assistants API or similar AI services, specific monitoring for configuration issues is critical as these require human intervention and cannot be resolved through automated retries.

### Custom Metrics for AI Configuration Issues

Set up custom metrics to track configuration-related issues:

```javascript
// Example of emitting assistant configuration issue metrics
async function emitConfigurationIssueMetric(issueType, dimensions) {
  const cloudwatch = new AWS.CloudWatch();
  
  // Convert dimensions object to CloudWatch format
  const metricDimensions = Object.entries(dimensions).map(([name, value]) => ({
    Name: name,
    Value: String(value)
  }));
  
  // Emit the metric
  await cloudwatch.putMetricData({
    Namespace: 'WhatsAppProcessingEngine',
    MetricData: [
      {
        MetricName: 'AssistantConfigurationIssue',
        Value: 1,
        Unit: 'Count',
        Dimensions: [
          ...metricDimensions,
          { Name: 'IssueType', Value: issueType }
        ]
      }
    ]
  }).promise();
}
```

### Key Metrics to Monitor

| Metric Name | Description | Dimensions | Unit | Statistic |
|-------------|-------------|------------|------|-----------|
| `AssistantConfigurationIssue` | Count of AI assistant configuration issues | `ConversationId`, `AssistantId`, `ProcessingStage`, `IssueType`, `Environment` | Count | Sum |

### AI Configuration Issues Dashboard

Create a dedicated dashboard for monitoring AI assistant configuration issues:

```typescript
// AI Configuration Issues Dashboard
const aiConfigDashboard = new cloudwatch.Dashboard(this, 'AIConfigIssuesDashboard', {
  dashboardName: 'WhatsAppEngine-AIConfigIssues'
});

aiConfigDashboard.addWidgets(
  // Header
  new cloudwatch.TextWidget({
    markdown: '# AI Assistant Configuration Issues\nMonitoring for OpenAI Assistants API configuration problems',
    width: 24,
    height: 2
  }),
  
  // Configuration Issues by Type
  new cloudwatch.GraphWidget({
    title: 'Configuration Issues by Type',
    left: [
      new cloudwatch.Metric({
        namespace: 'WhatsAppProcessingEngine',
        metricName: 'AssistantConfigurationIssue',
        dimensionsMap: {
          'IssueType': 'MissingStructuredJSONResponse'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(5)
      }),
      new cloudwatch.Metric({
        namespace: 'WhatsAppProcessingEngine',
        metricName: 'AssistantConfigurationIssue',
        dimensionsMap: {
          'IssueType': 'MalformedJSONResponse'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(5)
      })
    ],
    width: 12,
    height: 6
  }),
  
  // Configuration Issues by Assistant ID
  new cloudwatch.GraphWidget({
    title: 'Configuration Issues by Assistant',
    left: [
      // This uses a metric math expression to separate by AssistantId dimension
      new cloudwatch.MathExpression({
        expression: "SELECT SUM(AssistantConfigurationIssue) FROM SCHEMA(WhatsAppProcessingEngine, AssistantId) GROUP BY AssistantId",
        period: cdk.Duration.minutes(60),
        label: "Issues per Assistant"
      })
    ],
    width: 12,
    height: 6
  }),
  
  // Configuration Issues by Processing Stage
  new cloudwatch.GraphWidget({
    title: 'Configuration Issues by Processing Stage',
    left: [
      new cloudwatch.Metric({
        namespace: 'WhatsAppProcessingEngine',
        metricName: 'AssistantConfigurationIssue',
        dimensionsMap: {
          'ProcessingStage': 'initial'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(5)
      }),
      new cloudwatch.Metric({
        namespace: 'WhatsAppProcessingEngine',
        metricName: 'AssistantConfigurationIssue',
        dimensionsMap: {
          'ProcessingStage': 'final'
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(5)
      })
    ],
    width: 12,
    height: 6
  }),
  
  // Time Since Last Configuration Issue
  new cloudwatch.SingleValueWidget({
    title: 'Time Since Last Configuration Issue',
    metrics: [
      new cloudwatch.MathExpression({
        expression: "TIME_SECONDS(AssistantConfigurationIssue)",
        usingMetrics: {
          AssistantConfigurationIssue: new cloudwatch.Metric({
            namespace: 'WhatsAppProcessingEngine',
            metricName: 'AssistantConfigurationIssue',
            statistic: 'Sample',
            period: cdk.Duration.hours(24)
          })
        }
      })
    ],
    width: 12,
    height: 6
  })
);
```

### AI Configuration Issues Alarms

Set up specific alarms for assistant configuration issues:

```typescript
// Missing Structured JSON Response Alarm
const missingStructuredJSONResponseAlarm = new cloudwatch.Alarm(this, 'MissingStructuredJSONResponseAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'WhatsAppProcessingEngine',
    metricName: 'AssistantConfigurationIssue',
    dimensionsMap: {
      'IssueType': 'MissingStructuredJSONResponse'
    },
    statistic: 'Sum',
    period: cdk.Duration.minutes(5)
  }),
  threshold: 0,
  evaluationPeriods: 1,
  datapointsToAlarm: 1,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
  alarmDescription: 'AI assistant did not provide the expected structured JSON response'
});

// Malformed JSON Response Alarm
const malformedJSONResponseAlarm = new cloudwatch.Alarm(this, 'MalformedJSONResponseAlarm', {
  metric: new cloudwatch.Metric({
    namespace: 'WhatsAppProcessingEngine',
    metricName: 'AssistantConfigurationIssue',
    dimensionsMap: {
      'IssueType': 'MalformedJSONResponse'
    },
    statistic: 'Sum',
    period: cdk.Duration.minutes(5)
  }),
  threshold: 0,
  evaluationPeriods: 1,
  datapointsToAlarm: 1,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
  alarmDescription: 'AI assistant provided a response that could not be parsed as valid JSON'
});

// Add high-priority notifications
missingStructuredJSONResponseAlarm.addAlarmAction(new cloudwatchActions.SnsAction(highPriorityAlarmTopic));
malformedJSONResponseAlarm.addAlarmAction(new cloudwatchActions.SnsAction(highPriorityAlarmTopic));
```

### Integration with Main Dashboard

Add a widget showing configuration issues to the main WhatsApp Processing Engine dashboard:

```typescript
// Add to existing WhatsApp Processing Dashboard
whatsappDashboard.addWidgets(
  // Other widgets...
  
  // AI Configuration Issues Section
  new cloudwatch.TextWidget({
    markdown: '## AI Assistant Configuration Issues',
    width: 24,
    height: 1
  }),
  
  // Configuration Issues Overview
  new cloudwatch.GraphWidget({
    title: 'AI Configuration Issues',
    left: [
      new cloudwatch.Metric({
        namespace: 'WhatsAppProcessingEngine',
        metricName: 'AssistantConfigurationIssue',
        statistic: 'Sum',
        period: cdk.Duration.minutes(5)
      })
    ],
    width: 12,
    height: 6
  }),
  
  // Alarm Status Widget
  new cloudwatch.AlarmWidget({
    title: 'Configuration Issue Alarms',
    alarms: [
      missingStructuredJSONResponseAlarm.alarmArn,
      malformedJSONResponseAlarm.alarmArn
    ],
    width: 12,
    height: 6
  })
);
```

## Alarm Integration

CloudWatch dashboards can display alarm states:

```typitten
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