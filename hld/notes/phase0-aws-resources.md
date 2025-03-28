# AWS Resources Documentation

This document tracks all AWS resources created for the AI Multi-Communications Engine project, organized by phase and stack.

## Phase 0: Environment Setup and Infrastructure Preparation

### AiMultiCommsVpcStack

| Resource Type | Resource Name | Purpose | Region | Cost Estimate |
|---------------|---------------|---------|--------|---------------|
| AWS::EC2::VPC | AiMultiCommsVpc | Main VPC for application | eu-north-1 | Free |
| AWS::EC2::Subnet | AiMultiCommsVpcPublicSubnet1/2 | Public subnets in 2 AZs | eu-north-1 | Free |
| AWS::EC2::Subnet | AiMultiCommsVpcPrivateSubnet1/2 | Private subnets in 2 AZs | eu-north-1 | Free |
| AWS::EC2::RouteTable | Public/PrivateRouteTable | Routing tables for subnets | eu-north-1 | Free |
| AWS::EC2::NatGateway | AiMultiCommsVpcNatGateway | NAT Gateway for private subnet internet access | eu-north-1 | ~$32/month + data transfer |
| AWS::EC2::SecurityGroup | LambdaSecurityGroup | Security group for Lambda functions | eu-north-1 | Free |

### AiMultiCommsBaseServicesStack

| Resource Type | Resource Name | Purpose | Region | Cost Estimate |
|---------------|---------------|---------|--------|---------------|
| AWS::Logs::LogGroup | AiMultiCommsLogGroup | Central log group for all application logs | eu-north-1 | ~$0.50/GB ingested |
| AWS::SecretsManager::Secret | AiMultiCommsSecrets | Base secret for storing credentials | eu-north-1 | $0.40/month per secret |
| AWS::EC2::VPCEndpoint | SecretsManagerEndpoint | VPC endpoint for Secrets Manager | eu-north-1 | ~$0.01/hour (~$7.50/month) |
| AWS::EC2::VPCEndpoint | LogsEndpoint | VPC endpoint for CloudWatch Logs | eu-north-1 | ~$0.01/hour (~$7.50/month) |

## Cost Summary

### Phase 0

| Component | Monthly Cost Estimate |
|-----------|------------------------|
| NAT Gateway | $32/month + data transfer |
| VPC Endpoints (2) | $15/month |
| Secrets Manager | $0.40/month |
| CloudWatch Logs | Variable based on usage |
| **Total Base Cost** | ~$47.40/month |

## Access Information

| Resource | Access Method | Notes |
|----------|---------------|-------|
| VPC | AWS Console | VPC ID: vpc-07697e3635246954b |
| Private Subnets | AWS Console | subnet-0318d2fb5773dfb8d, subnet-069e02bc74952fd92 |
| Secrets Manager | AWS Console/API | Path: /ai-multi-comms-engine/base-credentials |

## Cleanup Instructions

To delete all resources and avoid ongoing charges, run:

```bash
source .env && PYTHONPATH=$(pwd) cdk destroy --all
```

## Next Phase Resource Planning

For Phase 1 (Database Layer and Foundational Components), we will need:

- DynamoDB tables:
  - wa_company_data
  - conversations
- Additional IAM roles and policies
- Lambda functions for shared utilities 