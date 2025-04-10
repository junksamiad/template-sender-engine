# SQS Queues (All Channels - Dev) - Low-Level Design

## 1. Introduction

This document provides a detailed Low-Level Design (LLD) for the AWS Simple Queue Service (SQS) resources configured for the **WhatsApp, SMS, and Email channels** within the **development environment** (`src_dev`) of the AI Multi-Communications Engine.

This setup includes a main processing queue and a corresponding Dead-Letter Queue (DLQ) for each channel to handle message buffering, decoupling, and basic error management during development and testing.

These queues were implemented manually using the AWS CLI as part of the initial infrastructure setup.

## 2. Architecture Overview

### 2.1 Component Purpose

For each channel (WhatsApp, SMS, Email):

1.  **Main Queue (`ai-multi-comms-<channel>-queue-dev`):**
    *   Receives `Context Object` messages routed for the specific channel from the Channel Router Lambda (`channel-router-dev`).
    *   Acts as a buffer, decoupling the Channel Router from the downstream Channel Processing Engine Lambda (to be developed).
    *   Enables asynchronous processing of message requests.
    *   Holds messages temporarily if the processing engine is unavailable or handling a backlog.

2.  **Dead-Letter Queue (`ai-multi-comms-<channel>-dlq-dev`):**
    *   Receives messages that fail processing repeatedly in the corresponding main queue (after `maxReceiveCount` is exceeded).
    *   Isolates problematic messages for later inspection and debugging.
    *   Prevents perpetually failing messages from blocking the main queue.

### 2.2 Position in System Architecture (Development)

```mermaid
graph TD
    subgraph "Channel Router Component (Dev)"
        RouterLambda[channel-router-dev Lambda]
    end

    subgraph "SQS Queues (WhatsApp - Dev)"
        MainQueueW["Main Queue<br/>ai-multi-comms-whatsapp-queue-dev<br/>VisTimeout: 905s"]
        DLQW["DLQ<br/>ai-multi-comms-whatsapp-dlq-dev<br/>Retention: 14d"]
        RedriveW["Redrive Policy (Max: 3)"]
    end

     subgraph "SQS Queues (SMS - Dev)"
        MainQueueS["Main Queue<br/>ai-multi-comms-sms-queue-dev<br/>VisTimeout: 600s"]
        DLQS["DLQ<br/>ai-multi-comms-sms-dlq-dev<br/>Retention: 14d"]
        RedriveS["Redrive Policy (Max: 3)"]
    end

     subgraph "SQS Queues (Email - Dev)"
        MainQueueE["Main Queue<br/>ai-multi-comms-email-queue-dev<br/>VisTimeout: 600s"]
        DLQE["DLQ<br/>ai-multi-comms-email-dlq-dev<br/>Retention: 14d"]
        RedriveE["Redrive Policy (Max: 3)"]
    end

    subgraph "Processing Engines (Dev - Future)"
        ProcessingLambdaW[ (whatsapp-processor-dev Lambda) ]
        ProcessingLambdaS[ (sms-processor-dev Lambda) ]
        ProcessingLambdaE[ (email-processor-dev Lambda) ]
    end

    subgraph "Monitoring (Dev)"
        CloudWatchAlarms["CloudWatch Alarms (Future)"]
        DLQInspection["Manual DLQ Inspection via Console/CLI"]
    end

    RouterLambda -- "Sends Context Object (WhatsApp)" --> MainQueueW
    MainQueueW -- "Failed Processing (x3)" --> RedriveW
    RedriveW --> DLQW
    MainQueueW -- "Triggers / Polls" --> ProcessingLambdaW
    ProcessingLambdaW -- "Processes & Deletes" --> MainQueueW

    RouterLambda -- "Sends Context Object (SMS)" --> MainQueueS
    MainQueueS -- "Failed Processing (x3)" --> RedriveS
    RedriveS --> DLQS
    MainQueueS -- "Triggers / Polls" --> ProcessingLambdaS
    ProcessingLambdaS -- "Processes & Deletes" --> MainQueueS

    RouterLambda -- "Sends Context Object (Email)" --> MainQueueE
    MainQueueE -- "Failed Processing (x3)" --> RedriveE
    RedriveE --> DLQE
    MainQueueE -- "Triggers / Polls" --> ProcessingLambdaE
    ProcessingLambdaE -- "Processes & Deletes" --> MainQueueE


    DLQW --> DLQInspection
    DLQW -.-> CloudWatchAlarms
    DLQS --> DLQInspection
    DLQS -.-> CloudWatchAlarms
    DLQE --> DLQInspection
    DLQE -.-> CloudWatchAlarms

```
*Diagram illustrates the flow for all channel queues.*

### 2.3 Technical Implementation

-   **Service**: AWS Simple Queue Service (SQS)
-   **Deployment Method**: AWS CLI (Manual setup for dev)
-   **Queue Type**: Standard (for all main and DLQ queues)
-   **Region**: `eu-north-1` (Stockholm)
-   **Account ID**: `337909745089`

## 3. Detailed Design

This section details the configuration for each channel's queue pair.

### 3.1 WhatsApp Channel

#### 3.1.1 Main Queue (`ai-multi-comms-whatsapp-queue-dev`)

-   **Queue URL**: `https://sqs.eu-north-1.amazonaws.com/337909745089/ai-multi-comms-whatsapp-queue-dev`
-   **ARN**: `arn:aws:sqs:eu-north-1:337909745089:ai-multi-comms-whatsapp-queue-dev`
-   **Visibility Timeout**: `905` seconds (15 minutes, 5 seconds)
    *   *Rationale:* Set slightly longer than the consuming Lambda (`whatsapp-channel-processor-dev`) timeout of 900 seconds, as required by AWS event source mapping constraints. Originally 600 seconds.
-   **Message Retention Period**: Default (4 days)
-   **Receive Message Wait Time**: Default (0 seconds - Short Polling)
-   **Redrive Policy**: Enabled
    *   `deadLetterTargetArn`: `arn:aws:sqs:eu-north-1:337909745089:ai-multi-comms-whatsapp-dlq-dev`
    *   `maxReceiveCount`: `3`

#### 3.1.2 Dead-Letter Queue (`ai-multi-comms-whatsapp-dlq-dev`)

-   **Queue URL**: `https://sqs.eu-north-1.amazonaws.com/337909745089/ai-multi-comms-whatsapp-dlq-dev`
-   **ARN**: `arn:aws:sqs:eu-north-1:337909745089:ai-multi-comms-whatsapp-dlq-dev`
-   **Visibility Timeout**: Default (30 seconds)
-   **Message Retention Period**: `1209600` seconds (14 days)
    *   *Rationale:* Ample time for developers to investigate failures.
-   **Redrive Policy**: Disabled.

### 3.2 SMS Channel

#### 3.2.1 Main Queue (`ai-multi-comms-sms-queue-dev`)

-   **Queue URL**: `https://sqs.eu-north-1.amazonaws.com/337909745089/ai-multi-comms-sms-queue-dev`
-   **ARN**: `arn:aws:sqs:eu-north-1:337909745089:ai-multi-comms-sms-queue-dev`
-   **Visibility Timeout**: `600` seconds (10 minutes)
    *   *Rationale:* Consistent with WhatsApp; allows time for processing including external SMS provider API calls.
-   **Message Retention Period**: Default (4 days)
-   **Receive Message Wait Time**: Default (0 seconds - Short Polling)
-   **Redrive Policy**: Enabled
    *   `deadLetterTargetArn`: `arn:aws:sqs:eu-north-1:337909745089:ai-multi-comms-sms-dlq-dev`
    *   `maxReceiveCount`: `3`

#### 3.2.2 Dead-Letter Queue (`ai-multi-comms-sms-dlq-dev`)

-   **Queue URL**: `https://sqs.eu-north-1.amazonaws.com/337909745089/ai-multi-comms-sms-dlq-dev`
-   **ARN**: `arn:aws:sqs:eu-north-1:337909745089:ai-multi-comms-sms-dlq-dev`
-   **Visibility Timeout**: Default (30 seconds)
-   **Message Retention Period**: `1209600` seconds (14 days)
    *   *Rationale:* Consistent with WhatsApp DLQ.
-   **Redrive Policy**: Disabled.

### 3.3 Email Channel

#### 3.3.1 Main Queue (`ai-multi-comms-email-queue-dev`)

-   **Queue URL**: `https://sqs.eu-north-1.amazonaws.com/337909745089/ai-multi-comms-email-queue-dev`
-   **ARN**: `arn:aws:sqs:eu-north-1:337909745089:ai-multi-comms-email-queue-dev`
-   **Visibility Timeout**: `600` seconds (10 minutes)
    *   *Rationale:* Consistent with other channels; allows time for processing including external Email provider/SMTP API calls.
-   **Message Retention Period**: Default (4 days)
-   **Receive Message Wait Time**: Default (0 seconds - Short Polling)
-   **Redrive Policy**: Enabled
    *   `deadLetterTargetArn`: `arn:aws:sqs:eu-north-1:337909745089:ai-multi-comms-email-dlq-dev`
    *   `maxReceiveCount`: `3`

#### 3.3.2 Dead-Letter Queue (`ai-multi-comms-email-dlq-dev`)

-   **Queue URL**: `https://sqs.eu-north-1.amazonaws.com/337909745089/ai-multi-comms-email-dlq-dev`
-   **ARN**: `arn:aws:sqs:eu-north-1:337909745089:ai-multi-comms-email-dlq-dev`
-   **Visibility Timeout**: Default (30 seconds)
-   **Message Retention Period**: `1209600` seconds (14 days)
    *   *Rationale:* Consistent with other DLQs.
-   **Redrive Policy**: Disabled.

### 3.4 Message Structure

-   Messages placed in any of the main queues (`ai-multi-comms-*-queue-dev`) by the Channel Router will be JSON strings representing the **Context Object**.
-   The structure is generated by `src_dev/channel-router/lambda/core/context_builder.py`.

## 4. Deployment & Management

-   **Deployment Tool**: AWS CLI (Initial Setup)
-   **Creation Steps**: Queues were created using `aws sqs create-queue` and configured using `aws sqs set-queue-attributes` for Redrive Policies.
    ```bash
    # Example Commands (Conceptual - replace <channel>, ARNs, URLs)
    # aws sqs create-queue --queue-name ai-multi-comms-<channel>-dlq-dev --attributes MessageRetentionPeriod=1209600 --region eu-north-1
    # DLQ_ARN=$(aws sqs get-queue-attributes --queue-url <DLQ_URL> --attribute-names QueueArn --query Attributes.QueueArn --output text --region eu-north-1)
    # echo '{"deadLetterTargetArn":"'$DLQ_ARN'","maxReceiveCount":"3"}' > redrive_policy.json
    # aws sqs create-queue --queue-name ai-multi-comms-<channel>-queue-dev --attributes VisibilityTimeout=600 --region eu-north-1
    # MAIN_QUEUE_URL=$(aws sqs get-queue-url --queue-name ai-multi-comms-<channel>-queue-dev --query QueueUrl --output text --region eu-north-1)
    # aws sqs set-queue-attributes --queue-url $MAIN_QUEUE_URL --attributes file://redrive_policy.json --region eu-north-1
    ```
-   **Management**: Via AWS Console or AWS CLI for monitoring queue depths, purging, or inspecting DLQ messages.

## 5. Testing Strategy

-   **Sending Messages**: Verified implicitly by successful execution of the Channel Router Lambda sending messages for each configured channel. Check CloudWatch logs for the Router Lambda and `sqs:SendMessage` calls.
-   **Receiving Messages**: Will be tested when the respective Channel Processor Lambdas (e.g., `sms-processor-dev`, `email-processor-dev`) are developed and configured to poll these queues.
-   **DLQ Functionality**: Test for each channel by:
    *   Manually sending a malformed JSON message to the main queue.
    *   Deploying a test version of a processor Lambda designed to consistently fail.
    *   Observing the `ApproximateReceiveCount` attribute increase (using `aws sqs receive-message --attribute-names ApproximateReceiveCount`).
    *   Confirming the message appears in the respective DLQ after the count exceeds 3.
-   **Verification**: Use `aws sqs receive-message` or the AWS Console to view messages and queue attributes (`ApproximateNumberOfMessages`).

## 6. Security Considerations

-   **Access Control (IAM Policies)**:
    *   **Channel Router Lambda (`channel-router-dev-role`)**: Requires `sqs:SendMessage` permission on the ARNs of all three main queues (`ai-multi-comms-whatsapp-queue-dev`, `ai-multi-comms-sms-queue-dev`, `ai-multi-comms-email-queue-dev`). The role's policy (`ai-multi-comms-channel-router-dev-policy` v3) has been updated to grant these permissions.
    *   **Channel Processor Lambdas (Future)**: Each processor will require `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes` permissions on its *corresponding* main queue.
    *   **Admin/Developer Users**: May require permissions like `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:ListQueues`, `sqs:GetQueueAttributes`, `sqs:PurgeQueue` on all main queues and DLQs for debugging and management.
-   **Encryption**: Server-Side Encryption using SQS-managed keys (SSE-SQS) is enabled by default.

## 7. Future Enhancements (Development Context)

-   Implement CloudWatch Alarms monitoring the `ApproximateNumberOfMessagesVisible` metric for all DLQs to alert developers of processing failures.
-   Re-evaluate using Standard vs. FIFO queues if strict message ordering becomes critical for any channel.
-   Consider adding queue-specific tags for cost allocation or resource identification. 