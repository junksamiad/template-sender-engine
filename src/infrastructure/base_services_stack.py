from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_secretsmanager as secretsmanager,
    aws_logs as logs,
    RemovalPolicy,
)
from constructs import Construct
from typing import Any


class BaseServicesStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, vpc: ec2.Vpc, **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Store VPC reference
        self.vpc = vpc

        # Create CloudWatch Log Group for the application
        self.log_group = logs.LogGroup(
            self,
            "AiMultiCommsLogGroup",
            log_group_name="/ai-multi-comms-engine",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.TWO_WEEKS,
        )

        # Create VPC Endpoints for AWS services to improve security and performance
        # Secrets Manager VPC Endpoint
        self.secrets_manager_endpoint = ec2.InterfaceVpcEndpoint(
            self,
            "SecretsManagerEndpoint",
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )

        # CloudWatch Logs VPC Endpoint
        self.logs_endpoint = ec2.InterfaceVpcEndpoint(
            self,
            "LogsEndpoint",
            vpc=self.vpc,
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )

        # Create a base Secret for storing API credentials
        # This will be populated during the appropriate phase
        self.base_secrets = secretsmanager.Secret(
            self,
            "AiMultiCommsSecrets",
            secret_name="/ai-multi-comms-engine/base-credentials",
            description="Base credentials for AI Multi-Communications Engine",
            removal_policy=RemovalPolicy.RETAIN,  # Retain secrets on stack deletion for safety
        ) 