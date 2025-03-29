#!/usr/bin/env python3
"""
Main CDK application entry point for the AI Multi-Communications Engine.
"""
import os
from aws_cdk import App, Environment
from dotenv import load_dotenv

# Import infrastructure stacks
from src.infrastructure import VpcStack, BaseServicesStack

# Load environment variables
load_dotenv()

# Create CDK app
app = App()

# Define AWS environment
env = Environment(
    account=os.environ.get("AWS_ACCOUNT_ID"),
    region=os.environ.get("AWS_REGION", "eu-north-1"),
)

# Deploy stacks
vpc_stack = VpcStack(app, "AiMultiCommsVpcStack", env=env)
base_services_stack = BaseServicesStack(
    app, "AiMultiCommsBaseServicesStack", vpc=vpc_stack.vpc, env=env
)

# Synthesize CloudFormation template
app.synth() 