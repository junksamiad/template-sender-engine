#!/usr/bin/env python3
import os
from aws_cdk import App, Environment
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

app = App()

# Import stacks after app is created to avoid circular dependencies
from src.infrastructure.vpc_stack import VpcStack
from src.infrastructure.base_services_stack import BaseServicesStack

# Define environment
env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT", os.environ.get("AWS_ACCOUNT_ID")),
    region=os.environ.get("CDK_DEFAULT_REGION", os.environ.get("AWS_REGION", "us-east-1")),
)

# Deploy stacks
vpc_stack = VpcStack(app, "AiMultiCommsVpcStack", env=env)
base_services_stack = BaseServicesStack(
    app, "AiMultiCommsBaseServicesStack", vpc=vpc_stack.vpc, env=env
)

app.synth() 