"""
Database operations utility for AI Multi-Communications Engine.

This module provides a high-level interface for CRUD operations on DynamoDB tables.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, TypeVar, Type

from src.shared.database.dynamo_client import DynamoDBClient
from src.shared.database.models import WaCompanyData, Conversation, Message, ChannelMethod, ConversationStatus

# Configure logger
logger = logging.getLogger(__name__)


class DatabaseOperations:
    """
    High-level database operations for the AI Multi-Communications Engine.
    
    This class provides a clean, type-safe interface for performing CRUD operations
    on the DynamoDB tables used by the application.
    """
    
    def __init__(
        self,
        dynamodb_client: Optional[DynamoDBClient] = None,
        wa_company_data_table_name: Optional[str] = None,
        conversations_table_name: Optional[str] = None,
        env_name: str = "dev"
    ):
        """
        Initialize database operations.
        
        Args:
            dynamodb_client: Optional DynamoDB client to use
            wa_company_data_table_name: Name of the wa_company_data table
            conversations_table_name: Name of the conversations table
            env_name: Environment name for table naming
        """
        self.env_name = env_name
        self.dynamodb_client = dynamodb_client or DynamoDBClient()
        self.wa_company_data_table = wa_company_data_table_name or f"wa_company_data-{env_name}"
        self.conversations_table = conversations_table_name or f"conversations-{env_name}"
        
        logger.info(f"Database operations initialized for tables: {self.wa_company_data_table}, {self.conversations_table}")
    
    # --------------------------------------------------------------------------
    # Company Data Operations
    # --------------------------------------------------------------------------
    
    def get_company_data(self, company_id: str, project_id: str) -> Optional[WaCompanyData]:
        """
        Get company data from the wa_company_data table.
        
        Args:
            company_id: The company ID
            project_id: The project ID
            
        Returns:
            The company data, or None if not found
        """
        try:
            key = {"company_id": company_id, "project_id": project_id}
            item = self.dynamodb_client.get_item(self.wa_company_data_table, key)
            
            if not item:
                logger.info(f"No company data found for company_id={company_id}, project_id={project_id}")
                return None
                
            return WaCompanyData.from_item(item)
        except Exception as e:
            logger.error(f"Error getting company data: {str(e)}")
            raise
    
    def create_company_data(self, company_data: WaCompanyData) -> WaCompanyData:
        """
        Create company data in the wa_company_data table.
        
        Args:
            company_data: The company data to create
            
        Returns:
            The created company data
        """
        try:
            # Validate the company data
            errors = company_data.validate()
            if errors:
                error_msg = f"Company data validation failed: {', '.join(errors)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Set timestamps
            now = datetime.now(timezone.utc).isoformat()
            company_data.created_at = now
            company_data.updated_at = now
            
            # Save to DynamoDB
            item = company_data.to_item()
            self.dynamodb_client.put_item(self.wa_company_data_table, item)
            
            logger.info(f"Created company data for company_id={company_data.company_id}, project_id={company_data.project_id}")
            return company_data
        except Exception as e:
            logger.error(f"Error creating company data: {str(e)}")
            raise
    
    def update_company_data(self, company_data: WaCompanyData) -> WaCompanyData:
        """
        Update company data in the wa_company_data table.
        
        Args:
            company_data: The company data to update
            
        Returns:
            The updated company data
        """
        try:
            # Validate the company data
            errors = company_data.validate()
            if errors:
                error_msg = f"Company data validation failed: {', '.join(errors)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Check if company data exists
            key = {"company_id": company_data.company_id, "project_id": company_data.project_id}
            existing_item = self.dynamodb_client.get_item(self.wa_company_data_table, key)
            
            if not existing_item:
                error_msg = f"Company data not found for company_id={company_data.company_id}, project_id={company_data.project_id}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Update timestamp
            company_data.updated_at = datetime.now(timezone.utc).isoformat()
            
            # Save to DynamoDB
            item = company_data.to_item()
            self.dynamodb_client.put_item(self.wa_company_data_table, item)
            
            logger.info(f"Updated company data for company_id={company_data.company_id}, project_id={company_data.project_id}")
            return company_data
        except Exception as e:
            logger.error(f"Error updating company data: {str(e)}")
            raise
    
    def delete_company_data(self, company_id: str, project_id: str) -> bool:
        """
        Delete company data from the wa_company_data table.
        
        Args:
            company_id: The company ID
            project_id: The project ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            key = {"company_id": company_id, "project_id": project_id}
            existing_item = self.dynamodb_client.get_item(self.wa_company_data_table, key)
            
            if not existing_item:
                logger.info(f"No company data found for deletion: company_id={company_id}, project_id={project_id}")
                return False
            
            self.dynamodb_client.delete_item(self.wa_company_data_table, key)
            
            logger.info(f"Deleted company data for company_id={company_id}, project_id={project_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting company data: {str(e)}")
            raise
    
    def list_company_projects(self, company_id: str) -> List[WaCompanyData]:
        """
        List all projects for a company.
        
        Args:
            company_id: The company ID
            
        Returns:
            A list of company data items for the company
        """
        try:
            response = self.dynamodb_client.query(
                table_name=self.wa_company_data_table,
                key_condition_expression="company_id = :company_id",
                expression_attribute_values={":company_id": company_id}
            )
            
            items = response.get("Items", [])
            return [WaCompanyData.from_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error listing company projects: {str(e)}")
            raise
    
    # --------------------------------------------------------------------------
    # Conversation Operations
    # --------------------------------------------------------------------------
    
    def get_conversation(self, primary_key: Dict[str, Any]) -> Optional[Conversation]:
        """
        Get a conversation from the conversations table.
        
        Args:
            primary_key: The primary key of the conversation.
                For WhatsApp/SMS: {"recipient_tel": tel, "conversation_id": id}
                For Email: Use query_conversation_by_email instead
            
        Returns:
            The conversation, or None if not found
        """
        try:
            item = self.dynamodb_client.get_item(self.conversations_table, primary_key)
            
            if not item:
                logger.info(f"No conversation found for key={primary_key}")
                return None
                
            return Conversation.from_item(item)
        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}")
            raise
    
    def query_conversation_by_email(self, recipient_email: str, conversation_id: str) -> Optional[Conversation]:
        """
        Query a conversation by email from the conversations table.
        
        Args:
            recipient_email: The recipient's email address
            conversation_id: The conversation ID
            
        Returns:
            The conversation, or None if not found
        """
        try:
            response = self.dynamodb_client.query(
                table_name=self.conversations_table,
                key_condition_expression="recipient_email = :email AND conversation_id = :id",
                expression_attribute_values={
                    ":email": recipient_email,
                    ":id": conversation_id
                },
                index_name="EmailIndex"
            )
            
            items = response.get("Items", [])
            if not items:
                logger.info(f"No conversation found for recipient_email={recipient_email}, conversation_id={conversation_id}")
                return None
                
            return Conversation.from_item(items[0])
        except Exception as e:
            logger.error(f"Error querying conversation by email: {str(e)}")
            raise
    
    def create_conversation(self, conversation: Conversation) -> Conversation:
        """
        Create a conversation in the conversations table.
        
        Args:
            conversation: The conversation to create
            
        Returns:
            The created conversation
        """
        try:
            # Validate the conversation
            errors = conversation.validate()
            if errors:
                error_msg = f"Conversation validation failed: {', '.join(errors)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Set timestamps
            now = datetime.now(timezone.utc).isoformat()
            conversation.created_at = now
            conversation.updated_at = now
            
            # Save to DynamoDB
            item = conversation.to_item()
            self.dynamodb_client.put_item(self.conversations_table, item)
            
            logger.info(f"Created conversation with ID {conversation.conversation_id}")
            return conversation
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            raise
    
    def update_conversation(self, conversation: Conversation) -> Conversation:
        """
        Update a conversation in the conversations table.
        
        Args:
            conversation: The conversation to update
            
        Returns:
            The updated conversation
        """
        try:
            # Validate the conversation
            errors = conversation.validate()
            if errors:
                error_msg = f"Conversation validation failed: {', '.join(errors)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Determine the primary key based on channel
            if conversation.channel_method == ChannelMethod.EMAIL.value:
                # For email, use the EmailIndex to check existence
                existing = self.query_conversation_by_email(
                    conversation.recipient_email, 
                    conversation.conversation_id
                )
                
                if not existing:
                    error_msg = f"Conversation not found for recipient_email={conversation.recipient_email}, conversation_id={conversation.conversation_id}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                    
                key = {"recipient_email": conversation.recipient_email, "conversation_id": conversation.conversation_id}
            else:
                # For WhatsApp/SMS, use the main table
                key = {"recipient_tel": conversation.recipient_tel, "conversation_id": conversation.conversation_id}
                existing_item = self.dynamodb_client.get_item(self.conversations_table, key)
                
                if not existing_item:
                    error_msg = f"Conversation not found for recipient_tel={conversation.recipient_tel}, conversation_id={conversation.conversation_id}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            
            # Update timestamp
            conversation.updated_at = datetime.now(timezone.utc).isoformat()
            
            # Save to DynamoDB
            item = conversation.to_item()
            self.dynamodb_client.put_item(self.conversations_table, item)
            
            logger.info(f"Updated conversation with ID {conversation.conversation_id}")
            return conversation
        except Exception as e:
            logger.error(f"Error updating conversation: {str(e)}")
            raise
    
    def update_conversation_status(
        self,
        primary_key: Dict[str, Any],
        status: Union[str, ConversationStatus]
    ) -> bool:
        """
        Update a conversation's status.
        
        Args:
            primary_key: The primary key of the conversation
            status: The new status
            
        Returns:
            True if updated, False if not found
        """
        try:
            # Get current conversation
            item = self.dynamodb_client.get_item(self.conversations_table, primary_key)
            
            if not item:
                logger.info(f"No conversation found for update: {primary_key}")
                return False
            
            # Convert status enum to string if needed
            if isinstance(status, ConversationStatus):
                status_value = status.value
            else:
                status_value = status
            
            # Update the status and timestamp
            now = datetime.now(timezone.utc).isoformat()
            self.dynamodb_client.update_item(
                table_name=self.conversations_table,
                key=primary_key,
                update_expression="SET conversation_status = :status, updated_at = :updated_at",
                expression_attribute_values={
                    ":status": status_value,
                    ":updated_at": now
                }
            )
            
            logger.info(f"Updated conversation status to {status_value} for {primary_key}")
            return True
        except Exception as e:
            logger.error(f"Error updating conversation status: {str(e)}")
            raise
    
    def add_message_to_conversation(
        self,
        primary_key: Dict[str, Any],
        message: Union[Dict[str, Any], Message]
    ) -> bool:
        """
        Add a message to a conversation.
        
        Args:
            primary_key: The primary key of the conversation
            message: The message to add
            
        Returns:
            True if added, False if conversation not found
        """
        try:
            # Get current conversation
            item = self.dynamodb_client.get_item(self.conversations_table, primary_key)
            
            if not item:
                logger.info(f"No conversation found for adding message: {primary_key}")
                return False
            
            # Convert message to dict if needed
            if isinstance(message, Message):
                message_dict = message.to_dict()
            else:
                # Ensure message has an entry_id
                if 'entry_id' not in message:
                    message['entry_id'] = str(uuid.uuid4())
                    
                # Ensure message has a timestamp
                if 'message_timestamp' not in message:
                    message['message_timestamp'] = datetime.now(timezone.utc).isoformat()
                    
                message_dict = message
            
            # Update the conversation with the new message
            now = datetime.now(timezone.utc).isoformat()
            self.dynamodb_client.update_item(
                table_name=self.conversations_table,
                key=primary_key,
                update_expression="SET messages = list_append(if_not_exists(messages, :empty_list), :new_message), updated_at = :updated_at",
                expression_attribute_values={
                    ":new_message": [message_dict],
                    ":empty_list": [],
                    ":updated_at": now
                }
            )
            
            logger.info(f"Added message to conversation for {primary_key}")
            return True
        except Exception as e:
            logger.error(f"Error adding message to conversation: {str(e)}")
            raise
    
    def delete_conversation(self, primary_key: Dict[str, Any]) -> bool:
        """
        Delete a conversation from the conversations table.
        
        Args:
            primary_key: The primary key of the conversation
            
        Returns:
            True if deleted, False if not found
        """
        try:
            existing_item = self.dynamodb_client.get_item(self.conversations_table, primary_key)
            
            if not existing_item:
                logger.info(f"No conversation found for deletion: {primary_key}")
                return False
            
            self.dynamodb_client.delete_item(self.conversations_table, primary_key)
            
            logger.info(f"Deleted conversation for {primary_key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting conversation: {str(e)}")
            raise
    
    def query_conversations_by_company_project(
        self,
        company_id: str,
        project_id: str,
        limit: Optional[int] = None
    ) -> List[Conversation]:
        """
        Query conversations by company ID and project ID.
        
        Args:
            company_id: The company ID
            project_id: The project ID
            limit: Maximum number of items to return
            
        Returns:
            A list of conversations
        """
        try:
            response = self.dynamodb_client.query(
                table_name=self.conversations_table,
                key_condition_expression="company_id = :company_id AND project_id = :project_id",
                expression_attribute_values={
                    ":company_id": company_id,
                    ":project_id": project_id
                },
                index_name="CompanyProjectIndex",
                limit=limit
            )
            
            items = response.get("Items", [])
            return [Conversation.from_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error querying conversations by company/project: {str(e)}")
            raise
    
    def query_conversations_by_request_id(
        self,
        request_id: str,
        limit: Optional[int] = None
    ) -> List[Conversation]:
        """
        Query conversations by request ID.
        
        Args:
            request_id: The request ID
            limit: Maximum number of items to return
            
        Returns:
            A list of conversations
        """
        try:
            response = self.dynamodb_client.query(
                table_name=self.conversations_table,
                key_condition_expression="request_id = :request_id",
                expression_attribute_values={
                    ":request_id": request_id
                },
                index_name="RequestIdIndex",
                limit=limit
            )
            
            items = response.get("Items", [])
            return [Conversation.from_item(item) for item in items]
        except Exception as e:
            logger.error(f"Error querying conversations by request ID: {str(e)}")
            raise
    
    def query_conversations_by_status(
        self,
        status: Union[str, ConversationStatus],
        limit: Optional[int] = None
    ) -> List[Conversation]:
        """
        Query conversations by status.
        
        Args:
            status: The conversation status to filter by
            limit: Maximum number of conversations to return
            
        Returns:
            A list of conversations with the given status
        """
        try:
            # Convert to string if needed
            status_str = status.value if isinstance(status, ConversationStatus) else status
            
            # Use scan with a filter since there's no status index
            response = self.dynamodb_client.scan(
                table_name=self.conversations_table,
                filter_expression="conversation_status = :status",
                expression_attribute_values={
                    ":status": status_str,
                },
                limit=limit,
            )
            
            conversations = []
            for item in response.get("Items", []):
                conversations.append(Conversation.from_item(item))
                
            return conversations
        except Exception as e:
            logger.error(f"Error querying conversations by status: {str(e)}")
            raise
    
    def query_conversations_by_channel(
        self,
        channel: Union[str, ChannelMethod],
        limit: Optional[int] = None
    ) -> List[Conversation]:
        """
        Query conversations by channel method.
        
        Args:
            channel: The channel method (whatsapp, sms, email)
            limit: Maximum number of conversations to return
            
        Returns:
            A list of conversations for the given channel
        """
        try:
            # Convert to string if needed
            channel_str = channel.value if isinstance(channel, ChannelMethod) else channel
            
            response = self.dynamodb_client.query(
                table_name=self.conversations_table,
                key_condition_expression="channel_method = :channel",
                expression_attribute_values={
                    ":channel": channel_str,
                },
                index_name="ChannelIndex",
                limit=limit,
            )
            
            conversations = []
            for item in response.get("Items", []):
                conversations.append(Conversation.from_item(item))
                
            return conversations
        except Exception as e:
            logger.error(f"Error querying conversations by channel: {str(e)}")
            raise
    
    def query_conversation_by_message_id(
        self,
        message_id: str
    ) -> Optional[Conversation]:
        """
        Query a conversation by message ID (for email replies).
        
        Args:
            message_id: The message ID
            
        Returns:
            The conversation, or None if not found
        """
        try:
            response = self.dynamodb_client.query(
                table_name=self.conversations_table,
                key_condition_expression="message_id = :message_id",
                expression_attribute_values={
                    ":message_id": message_id
                },
                index_name="MessageIdIndex",
                limit=1
            )
            
            items = response.get("Items", [])
            if not items:
                logger.info(f"No conversation found for message_id={message_id}")
                return None
                
            return Conversation.from_item(items[0])
        except Exception as e:
            logger.error(f"Error querying conversation by message ID: {str(e)}")
            raise
    
    def query_recent_conversations(
        self,
        timestamp: Union[str, datetime],
        channel: Optional[Union[str, ChannelMethod]] = None,
        limit: Optional[int] = None
    ) -> List[Conversation]:
        """
        Query recent conversations before a given timestamp.
        
        Args:
            timestamp: The timestamp to filter by (conversations before this time)
            channel: Optional channel to filter by
            limit: Maximum number of conversations to return
            
        Returns:
            A list of conversations before the given timestamp
        """
        try:
            # Convert timestamp to string if needed
            if isinstance(timestamp, datetime):
                timestamp_str = timestamp.isoformat()
            else:
                timestamp_str = timestamp
            
            # Convert channel to string if needed
            if channel is not None:
                channel_str = channel.value if isinstance(channel, ChannelMethod) else channel
                
                # Query using RecentConversationsIndex which has channel_method as hash key and created_at as range key
                response = self.dynamodb_client.query(
                    table_name=self.conversations_table,
                    key_condition_expression="channel_method = :channel AND created_at <= :timestamp",
                    expression_attribute_values={
                        ":channel": channel_str,
                        ":timestamp": timestamp_str,
                    },
                    index_name="RecentConversationsIndex",
                    scan_index_forward=False,  # Descending order (newest first)
                    limit=limit,
                )
            else:
                # Without channel, we need to scan with a filter
                response = self.dynamodb_client.scan(
                    table_name=self.conversations_table,
                    filter_expression="created_at <= :timestamp",
                    expression_attribute_values={
                        ":timestamp": timestamp_str,
                    },
                    limit=limit,
                )
            
            conversations = []
            for item in response.get("Items", []):
                conversations.append(Conversation.from_item(item))
                
            return conversations
        except Exception as e:
            logger.error(f"Error querying recent conversations: {str(e)}")
            raise 