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
from src.infrastructure.database_stack import DatabaseStack
from src.infrastructure.secrets_stack import SecretsStack

# Define environment
env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT", os.environ.get("AWS_ACCOUNT_ID")),
    region=os.environ.get("CDK_DEFAULT_REGION", os.environ.get("AWS_REGION", "us-east-1")),
)

# Get environment name from environment variables or default to 'dev'
env_name = os.environ.get("ENV_NAME", "dev")

# Deploy stacks
vpc_stack = VpcStack(app, "AiMultiCommsVpcStack", env=env)
base_services_stack = BaseServicesStack(
    app, "AiMultiCommsBaseServicesStack", vpc=vpc_stack.vpc, env=env
)
database_stack = DatabaseStack(
    app, "AiMultiCommsDatabaseStack", env_name=env_name, env=env
)
secrets_stack = SecretsStack(
    app, "AiMultiCommsSecretsStack", env=env
)

app.synth() 