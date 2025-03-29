"""
Query utilities for DynamoDB tables in the AI Multi-Communications Engine.

This module provides specialized query functions beyond the basic CRUD operations.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union, Callable, TypeVar, Generic

from src.shared.database.dynamo_client import DynamoDBClient
from src.shared.database.operations import DatabaseOperations
from src.shared.database.models import WaCompanyData, Conversation, Message, ChannelMethod, ConversationStatus

# Configure logger
logger = logging.getLogger(__name__)

T = TypeVar('T')


class QueryUtilities:
    """
    Advanced query utilities for the AI Multi-Communications Engine.
    
    This class provides specialized query methods for common patterns
    and complex use cases beyond basic CRUD operations.
    """
    
    def __init__(
        self,
        db_ops: Optional[DatabaseOperations] = None,
        env_name: str = "dev"
    ):
        """
        Initialize query utilities.
        
        Args:
            db_ops: Optional DatabaseOperations instance to use
            env_name: Environment name for table naming
        """
        self.env_name = env_name
        self.db_ops = db_ops or DatabaseOperations(env_name=env_name)
        logger.info("Query utilities initialized")
    
    # --------------------------------------------------------------------------
    # Advanced Company Data Queries
    # --------------------------------------------------------------------------
    
    def find_company_projects_by_status(
        self,
        company_id: str,
        status: str = "active"
    ) -> List[WaCompanyData]:
        """
        Find all projects for a company with the specified status.
        
        Args:
            company_id: The company ID
            status: The project status to filter by
            
        Returns:
            A list of company data items matching the criteria
        """
        try:
            # Get all projects for the company
            projects = self.db_ops.list_company_projects(company_id)
            
            # Filter by status
            return [project for project in projects if project.project_status == status]
        except Exception as e:
            logger.error(f"Error finding company projects by status: {str(e)}")
            raise
    
    def find_company_projects_by_channel(
        self,
        company_id: str,
        channel: Union[str, ChannelMethod]
    ) -> List[WaCompanyData]:
        """
        Find all projects for a company that support the specified channel.
        
        Args:
            company_id: The company ID
            channel: The channel to filter by
            
        Returns:
            A list of company data items matching the criteria
        """
        try:
            # Convert channel enum to string if needed
            if isinstance(channel, ChannelMethod):
                channel_value = channel.value
            else:
                channel_value = channel
                
            # Get all projects for the company
            projects = self.db_ops.list_company_projects(company_id)
            
            # Filter by channel
            return [
                project for project in projects 
                if channel_value in project.allowed_channels
            ]
        except Exception as e:
            logger.error(f"Error finding company projects by channel: {str(e)}")
            raise
    
    def find_company_project_by_credentials_reference(
        self,
        credentials_reference: str
    ) -> Optional[WaCompanyData]:
        """
        Find a company project by a credentials reference in its channel config.
        
        This is useful for matching incoming webhooks to the correct project.
        
        Args:
            credentials_reference: The credentials reference to search for
            
        Returns:
            The company data item matching the reference, or None if not found
        """
        # This requires a scan operation, which is not ideal for production
        # In a real system, you might want to create a GSI for this purpose
        try:
            table_name = f"wa_company_data-{self.env_name}"
            client = self.db_ops.dynamodb_client
            
            # Scan the table to find matching credential references
            response = client.scan(
                table_name=table_name,
                filter_expression="contains(channel_config.whatsapp.whatsapp_credentials_id, :ref) OR "
                                  "contains(channel_config.sms.sms_credentials_id, :ref) OR "
                                  "contains(channel_config.email.email_credentials_id, :ref)",
                expression_attribute_values={
                    ":ref": credentials_reference
                }
            )
            
            items = response.get("Items", [])
            if not items:
                logger.info(f"No company project found for credentials_reference={credentials_reference}")
                return None
                
            # Return the first matching item
            return WaCompanyData.from_item(items[0])
        except Exception as e:
            logger.error(f"Error finding company project by credentials reference: {str(e)}")
            raise
    
    # --------------------------------------------------------------------------
    # Advanced Conversation Queries
    # --------------------------------------------------------------------------
    
    def find_recipient_conversations(
        self,
        recipient_id: str,
        is_email: bool = False,
        limit: Optional[int] = 10
    ) -> List[Conversation]:
        """
        Find all conversations for a recipient.
        
        Args:
            recipient_id: The recipient ID (tel or email)
            is_email: Whether the recipient ID is an email
            limit: Maximum number of conversations to return
            
        Returns:
            A list of conversations for the recipient
        """
        try:
            table_name = f"conversations-{self.env_name}"
            client = self.db_ops.dynamodb_client
            
            if is_email:
                # Query using the EmailIndex
                response = client.query(
                    table_name=table_name,
                    key_condition_expression="recipient_email = :recipient_id",
                    expression_attribute_values={
                        ":recipient_id": recipient_id
                    },
                    index_name="EmailIndex",
                    limit=limit
                )
            else:
                # Query using the primary table
                response = client.query(
                    table_name=table_name,
                    key_condition_expression="recipient_tel = :recipient_id",
                    expression_attribute_values={
                        ":recipient_id": recipient_id
                    },
                    limit=limit
                )
            
            items = response.get("Items", [])
            return [Conversation.from_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error finding recipient conversations: {str(e)}")
            raise
    
    def find_conversations_by_time_period(
        self,
        start_time: Union[str, datetime],
        end_time: Union[str, datetime],
        channel: Optional[Union[str, ChannelMethod]] = None,
        limit: Optional[int] = 100
    ) -> List[Conversation]:
        """
        Find conversations created within a time period.
        
        Args:
            start_time: The start of the time period
            end_time: The end of the time period
            channel: Optional channel to filter by
            limit: Maximum number of conversations to return
            
        Returns:
            A list of conversations within the time period
        """
        try:
            table_name = f"conversations-{self.env_name}"
            client = self.db_ops.dynamodb_client
            
            # Convert times to strings if needed
            if isinstance(start_time, datetime):
                start_time_str = start_time.isoformat()
            else:
                start_time_str = start_time
                
            if isinstance(end_time, datetime):
                end_time_str = end_time.isoformat()
            else:
                end_time_str = end_time
            
            # For time-based queries with a range, we need to use a filter expression
            # rather than a key condition (because created_at is a range key in TimestampIndex)
            if channel:
                # Convert channel enum to string if needed
                if isinstance(channel, ChannelMethod):
                    channel_value = channel.value
                else:
                    channel_value = channel
                    
                # Filter by both time range and channel
                filter_expression = "created_at BETWEEN :start_time AND :end_time"
                response = client.scan(
                    table_name=table_name,
                    filter_expression=filter_expression + " AND channel_method = :channel",
                    expression_attribute_values={
                        ":start_time": start_time_str,
                        ":end_time": end_time_str,
                        ":channel": channel_value
                    },
                    limit=limit
                )
            else:
                # Filter by time range only
                filter_expression = "created_at BETWEEN :start_time AND :end_time"
                response = client.scan(
                    table_name=table_name,
                    filter_expression=filter_expression,
                    expression_attribute_values={
                        ":start_time": start_time_str,
                        ":end_time": end_time_str
                    },
                    limit=limit
                )
            
            items = response.get("Items", [])
            return [Conversation.from_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error finding conversations by time period: {str(e)}")
            raise
    
    def find_recent_conversations(
        self,
        hours: int = 24,
        channel: Optional[Union[str, ChannelMethod]] = None,
        limit: Optional[int] = 50
    ) -> List[Conversation]:
        """
        Find conversations created within the last N hours.
        
        Args:
            hours: Number of hours to look back
            channel: Optional channel to filter by
            limit: Maximum number of conversations to return
            
        Returns:
            A list of recent conversations
        """
        try:
            # Calculate start time N hours ago
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours)
            
            return self.find_conversations_by_time_period(
                start_time=start_time,
                end_time=end_time,
                channel=channel,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Error finding recent conversations: {str(e)}")
            raise
    
    def find_failed_conversations(
        self,
        hours: int = 24,
        limit: Optional[int] = 50
    ) -> List[Conversation]:
        """
        Find conversations that failed within the last N hours.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of conversations to return
            
        Returns:
            A list of failed conversations
        """
        try:
            # Get conversations by status
            failed_conversations = self.db_ops.query_conversations_by_status(
                status=ConversationStatus.FAILED,
                limit=limit
            )
            
            # Calculate start time N hours ago
            start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            start_time_str = start_time.isoformat()
            
            # Filter by time
            return [
                conv for conv in failed_conversations 
                if conv.updated_at >= start_time_str
            ]
        except Exception as e:
            logger.error(f"Error finding failed conversations: {str(e)}")
            raise
    
    def find_unprocessed_conversations(
        self,
        minutes: int = 10,
        limit: Optional[int] = 20
    ) -> List[Conversation]:
        """
        Find conversations that have been in processing state for too long.
        
        This can be used to identify conversations that might be stuck.
        
        Args:
            minutes: Number of minutes to consider as "too long"
            limit: Maximum number of conversations to return
            
        Returns:
            A list of potentially stuck conversations
        """
        try:
            # Get conversations in processing state
            processing_conversations = self.db_ops.query_conversations_by_status(
                status=ConversationStatus.PROCESSING,
                limit=limit * 2  # Get more than we need for filtering
            )
            
            # Calculate cutoff time
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            cutoff_time_str = cutoff_time.isoformat()
            
            # Filter conversations that have been in processing state for too long
            result = [
                conv for conv in processing_conversations 
                if conv.updated_at < cutoff_time_str
            ]
            
            return result[:limit]
        except Exception as e:
            logger.error(f"Error finding unprocessed conversations: {str(e)}")
            raise
    
    def find_conversations_with_most_messages(
        self,
        limit: int = 10
    ) -> List[Conversation]:
        """
        Find conversations with the most messages.
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            A list of conversations with the most messages
        """
        # This is a more expensive operation as it requires a full scan
        try:
            table_name = f"conversations-{self.env_name}"
            client = self.db_ops.dynamodb_client
            
            # Scan the entire table (consider using pagination for large tables)
            response = client.scan(
                table_name=table_name,
                projection_expression="recipient_tel, conversation_id, channel_method, messages, recipient_email"
            )
            
            # Convert to conversation objects and count messages
            items = response.get("Items", [])
            conversations = [Conversation.from_item(item) for item in items]
            
            # Sort by message count descending
            conversations.sort(key=lambda conv: len(conv.messages) if conv.messages else 0, reverse=True)
            
            # Return top N
            return conversations[:limit]
        except Exception as e:
            logger.error(f"Error finding conversations with most messages: {str(e)}")
            raise
    
    def search_conversations_by_message_content(
        self,
        search_term: str,
        limit: int = 10
    ) -> List[Conversation]:
        """
        Search conversations for a specific term in message content.
        
        Note: This is an expensive operation that requires scanning the table.
        In a production environment, consider using a dedicated search service.
        
        Args:
            search_term: The term to search for
            limit: Maximum number of conversations to return
            
        Returns:
            A list of conversations containing the search term
        """
        try:
            table_name = f"conversations-{self.env_name}"
            client = self.db_ops.dynamodb_client
            
            # Scan the table for conversations with messages containing the search term
            response = client.scan(
                table_name=table_name
            )
            
            # Convert to conversation objects
            items = response.get("Items", [])
            conversations = [Conversation.from_item(item) for item in items]
            
            # Filter conversations with messages containing the search term
            matching_conversations = []
            search_term_lower = search_term.lower()
            
            for conv in conversations:
                if not conv.messages:
                    continue
                    
                for msg in conv.messages:
                    if search_term_lower in msg.content.lower():
                        matching_conversations.append(conv)
                        break
                        
                if len(matching_conversations) >= limit:
                    break
            
            return matching_conversations
        except Exception as e:
            logger.error(f"Error searching conversations by message content: {str(e)}")
            raise 