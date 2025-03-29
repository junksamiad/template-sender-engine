"""
Database stack for the AI Multi-Communications Engine.

This module defines the AWS CDK stack for creating DynamoDB tables
according to the schema definitions in the LLD documents.
"""
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    CfnOutput,
)
from constructs import Construct
from typing import Any, Dict, Optional


class DatabaseStack(Stack):
    """
    CDK Stack for DynamoDB tables used by the AI Multi-Communications Engine.
    
    This stack creates:
    - wa_company_data table for company and project configurations
    - conversations table for tracking messages across all channels
    
    The tables are configured with GSIs to support the query patterns
    described in the schema documentation, with appropriate TTL settings
    and other optimizations.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str = "dev",
        **kwargs: Any,
    ) -> None:
        """
        Initialize the database stack.
        
        Args:
            scope: The scope in which this stack is defined
            construct_id: The ID of this stack
            env_name: The environment name (dev, staging, prod)
            **kwargs: Additional keyword arguments passed to the base Stack class
        """
        super().__init__(scope, construct_id, **kwargs)

        # Define removal policy based on environment
        removal_policy = (
            RemovalPolicy.RETAIN
            if env_name in ["prod", "staging"]
            else RemovalPolicy.DESTROY
        )

        # Create wa_company_data table
        self.company_data_table = dynamodb.Table(
            self,
            "WaCompanyDataTable",
            table_name=f"wa_company_data-{env_name}",
            partition_key=dynamodb.Attribute(
                name="company_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="project_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=removal_policy,
        )

        # Create conversations table
        self.conversations_table = dynamodb.Table(
            self,
            "ConversationsTable",
            table_name=f"conversations-{env_name}",
            # Define composite keys specific to each channel
            # For WhatsApp and SMS, we use recipient_tel as partition key
            # For Email, we use recipient_email as partition key
            # All use conversation_id as sort key which includes the channel identifier
            partition_key=dynamodb.Attribute(
                name="recipient_tel", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="conversation_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=removal_policy,
            # Enable TTL for conversation records
            time_to_live_attribute="ttl",
        )

        # Add GSI for email conversations
        self.conversations_table.add_global_secondary_index(
            index_name="EmailIndex",
            partition_key=dynamodb.Attribute(
                name="recipient_email", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="conversation_id", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Add GSI for company/project lookups
        self.conversations_table.add_global_secondary_index(
            index_name="CompanyProjectIndex",
            partition_key=dynamodb.Attribute(
                name="company_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="project_id", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Add GSI for finding conversations by request_id
        self.conversations_table.add_global_secondary_index(
            index_name="RequestIdIndex",
            partition_key=dynamodb.Attribute(
                name="request_id", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Add GSI for finding conversations by status
        self.conversations_table.add_global_secondary_index(
            index_name="StatusIndex",
            partition_key=dynamodb.Attribute(
                name="conversation_status", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="updated_at", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Add GSI for finding conversations by channel type
        self.conversations_table.add_global_secondary_index(
            index_name="ChannelMethodConversationIndex",
            partition_key=dynamodb.Attribute(
                name="channel_method", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Add GSI for matching email replies using message_id
        self.conversations_table.add_global_secondary_index(
            index_name="MessageIdIndex",
            partition_key=dynamodb.Attribute(
                name="message_id", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Add GSI for finding recent conversations by timestamp
        self.conversations_table.add_global_secondary_index(
            index_name="TimestampIndex",
            partition_key=dynamodb.Attribute(
                name="created_at", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="channel_method", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Outputs
        CfnOutput(
            self,
            "CompanyDataTableName",
            value=self.company_data_table.table_name,
            description="Name of the wa_company_data DynamoDB table",
        )
        CfnOutput(
            self,
            "ConversationsTableName",
            value=self.conversations_table.table_name,
            description="Name of the conversations DynamoDB table",
        )
        CfnOutput(
            self,
            "CompanyDataTableArn",
            value=self.company_data_table.table_arn,
            description="ARN of the wa_company_data DynamoDB table",
        )
        CfnOutput(
            self,
            "ConversationsTableArn",
            value=self.conversations_table.table_arn,
            description="ARN of the conversations DynamoDB table",
        ) 