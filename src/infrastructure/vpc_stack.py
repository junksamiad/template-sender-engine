from aws_cdk import Stack, aws_ec2 as ec2
from constructs import Construct
from typing import Any


class VpcStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a VPC with public and private subnets in 2 Availability Zones
        self.vpc = ec2.Vpc(
            self,
            "AiMultiCommsVpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )

        # Create security group for Lambda functions
        self.lambda_sg = ec2.SecurityGroup(
            self,
            "LambdaSecurityGroup",
            vpc=self.vpc,
            description="Security group for Lambda functions",
            allow_all_outbound=True,
        )

        # Output the VPC ID
        self.vpc_id = self.vpc.vpc_id 