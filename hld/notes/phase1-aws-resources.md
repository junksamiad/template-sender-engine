# Phase 1 AWS Resources Documentation

This document tracks all AWS resources created for Phase 1 of the AI Multi-Communications Engine project.

## DynamoDB Tables

| Table Name | Purpose | Configuration | Region | Cost Estimate |
|------------|---------|--------------|--------|---------------|
| wa_company_data-dev | Stores company and project configuration data | Partition Key: company_id<br>Sort Key: project_id<br>Billing Mode: PAY_PER_REQUEST<br>Point-in-time Recovery: Enabled | us-east-1 | ~$1-2/month for small workloads |
| conversations-dev | Stores conversation data across multiple channels | Partition Key: recipient_tel<br>Sort Key: conversation_id<br>Billing Mode: PAY_PER_REQUEST<br>Point-in-time Recovery: Enabled<br>TTL: Enabled (ttl attribute) | us-east-1 | ~$2-5/month for small workloads |

### Global Secondary Indexes (GSIs)

#### wa_company_data-dev
No GSIs added for the wa_company_data table yet, as the primary key structure satisfies the current query patterns.

#### conversations-dev

| Index Name | Purpose | Partition Key | Sort Key | Projection | 
|------------|---------|--------------|----------|------------|
| EmailIndex | Support lookups by recipient email for email channel | recipient_email | conversation_id | ALL |
| CompanyProjectIndex | Find conversations by company and project | company_id | project_id | ALL |
| RequestIdIndex | Find conversations by request_id | request_id | - | ALL |
| StatusIndex | Find conversations by status | conversation_status | updated_at | ALL |
| ChannelMethodConversationIndex | Find all conversations for a channel type | channel_method | created_at | ALL |
| MessageIdIndex | Match email replies using message_id | message_id | - | ALL |
| TimestampIndex | Find recent conversations by timestamp | created_at | channel_method | ALL |

## AWS Secrets Manager

| Secret Name | Purpose | Rotation Policy | Region | Cost Estimate |
|-------------|---------|----------------|--------|---------------|
| | | | | |

## CloudWatch Resources

| Resource Type | Name | Purpose | Region | Cost Estimate |
|---------------|------|---------|--------|---------------|
| | | | | |

## IAM Resources

| Resource Type | Name | Purpose | Permissions |
|---------------|------|---------|------------|
| | | | |

## Cost Summary

### Phase 1

| Component | Monthly Cost Estimate |
|-----------|------------------------|
| DynamoDB Tables (2) | ~$3-7/month for small workloads |
| **Total Base Cost** | ~$3-7/month |

### Cost Optimization Notes

1. The tables are configured with PAY_PER_REQUEST billing mode to avoid over-provisioning in early stages.
2. For production workloads with predictable usage patterns, consider switching to PROVISIONED billing mode.
3. TTL is enabled on the conversations table to automatically delete old records, reducing storage costs.
4. Point-in-time recovery is enabled for data protection, which adds a small cost but provides critical data recovery capabilities.

## Access Information

| Resource | Access Method | Notes |
|----------|---------------|-------|
| DynamoDB Tables | AWS Console or AWS SDK | Access using IAM credentials with appropriate permissions |

## Cleanup Instructions

To delete all resources created in Phase 1 and avoid ongoing charges, run:

```bash
source .env && PYTHONPATH=$(pwd) cdk destroy AiMultiCommsDatabaseStack AiMultiCommsSecretsStack
```

## Next Phase Resource Dependencies

For Phase 2 (Channel Router Implementation), the following resources from Phase 1 will be required:

- DynamoDB Tables:
  - wa_company_data table for company/project lookup
  - conversations table for conversation tracking
- Secrets Manager references for credential management
- Shared utilities for context handling, error management, etc. 