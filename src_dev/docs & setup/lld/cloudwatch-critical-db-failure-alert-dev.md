# CloudWatch Alarm Setup for Critical DB Update Failure (WhatsApp Processor - Dev)

This document details the implemented CloudWatch monitoring setup designed to specifically alert on critical failures during the final DynamoDB update step within the `whatsapp-channel-processor-dev` Lambda function. This setup ensures that instances where a message is sent but the corresponding database record update fails are promptly flagged.

## 1. Overview: Log -> Filter -> Metric -> Alarm -> SNS -> Email

The monitoring flow relies on a chain of AWS services:

1.  **CloudWatch Logs:** The `whatsapp-channel-processor-dev` Lambda logs a `CRITICAL` message if the `update_conversation_after_send` call to DynamoDB fails.
2.  **Metric Filter:** A CloudWatch Logs Metric Filter (`FinalDbUpdateFailureFilter-Dev`) scans the Lambda's log group (`/aws/lambda/whatsapp-channel-processor-dev`) for log entries matching the critical error pattern.
3.  **Custom Metric:** Each time a matching log entry is found, the filter increments a custom CloudWatch Metric (`FinalDbUpdateFailureCount` in the `AIComms/WhatsAppProcessor/Dev` namespace).
4.  **CloudWatch Alarm:** An alarm (`WhatsAppProcessorFinalDbUpdateFailureAlarm-Dev`) monitors the `FinalDbUpdateFailureCount` metric.
5.  **SNS Topic:** If the alarm threshold is breached (metric >= 1), it triggers an action to publish a notification to an SNS Topic (`ai-comms-critical-alerts-dev`).
6.  **Email Notification:** An email endpoint (subscribed and confirmed by the developer) receives the notification from the SNS topic.

## 2. Implemented Configuration (AWS CLI)

The following AWS resources were configured using the AWS CLI:

### 2.1. SNS Topic

-   **Purpose:** Central hub for receiving alarm notifications.
-   **Name:** `ai-comms-critical-alerts-dev`
-   **ARN:** `arn:aws:sns:eu-north-1:337909745089:ai-comms-critical-alerts-dev`
-   **Creation Command:**
    ```bash
    aws sns create-topic --name ai-comms-critical-alerts-dev
    ```
-   **Subscription:** An email endpoint was manually subscribed using `aws sns subscribe` and confirmed via email.
    ```bash
    # Example command (run by developer, replace email)
    # aws sns subscribe --topic-arn arn:aws:sns:eu-north-1:337909745089:ai-comms-critical-alerts-dev --protocol email --notification-endpoint <your-email-address> --region eu-north-1
    ```

### 2.2. CloudWatch Logs Metric Filter

-   **Purpose:** Scan logs and count occurrences of the specific critical error.
-   **Log Group:** `/aws/lambda/whatsapp-channel-processor-dev`
-   **Filter Name:** `FinalDbUpdateFailureFilter-Dev`
-   **Filter Pattern:** `{$.logLevel = CRITICAL && $.message = "*final DynamoDB update failed*"}`
    *   *Note: This pattern relies on the logger outputting JSON with these fields. If logs are plain text, a pattern like `?"CRITICAL" ?"final DynamoDB update failed"` might be needed, though the JSON pattern worked during setup.*
-   **Metric Transformation:**
    *   Namespace: `AIComms/WhatsAppProcessor/Dev`
    *   Metric Name: `FinalDbUpdateFailureCount`
    *   Metric Value: `1`
    *   Default Value: `0`
-   **Creation Command:**
    ```bash
    aws logs put-metric-filter \
      --log-group-name /aws/lambda/whatsapp-channel-processor-dev \
      --filter-name FinalDbUpdateFailureFilter-Dev \
      --filter-pattern '{$.logLevel = CRITICAL && $.message = "*final DynamoDB update failed*" }' \
      --metric-transformations metricName=FinalDbUpdateFailureCount,metricNamespace=AIComms/WhatsAppProcessor/Dev,metricValue=1,defaultValue=0
    ```

### 2.3. CloudWatch Alarm

-   **Purpose:** Monitor the custom metric and trigger the SNS notification.
-   **Alarm Name:** `WhatsAppProcessorFinalDbUpdateFailureAlarm-Dev`
-   **Metric Monitored:** `FinalDbUpdateFailureCount` (Namespace: `AIComms/WhatsAppProcessor/Dev`)
-   **Configuration:**
    *   Statistic: `Sum`
    *   Period: `300` seconds (5 minutes)
    *   Evaluation Periods: `1`
    *   Threshold: `1`
    *   Comparison Operator: `GreaterThanOrEqualToThreshold`
    *   Treat Missing Data: `notBreaching`
-   **Alarm Action:** `arn:aws:sns:eu-north-1:337909745089:ai-comms-critical-alerts-dev`
-   **Creation Command:**
    ```bash
    aws cloudwatch put-metric-alarm \
      --alarm-name WhatsAppProcessorFinalDbUpdateFailureAlarm-Dev \
      --metric-name FinalDbUpdateFailureCount \
      --namespace AIComms/WhatsAppProcessor/Dev \
      --statistic Sum \
      --period 300 \
      --evaluation-periods 1 \
      --threshold 1 \
      --comparison-operator GreaterThanOrEqualToThreshold \
      --alarm-actions arn:aws:sns:eu-north-1:337909745089:ai-comms-critical-alerts-dev \
      --treat-missing-data notBreaching
    ```

## 3. Summary

This setup provides automated alerting specifically for the critical scenario where the WhatsApp processor sends a message but fails the final database update. Monitoring relies on the specific `CRITICAL` log message format generated in `services/dynamodb_service.py` when `update_conversation_after_send` returns `False`.
