"""
DynamoDB client utility for AI Multi-Communications Engine.

This module provides a client for interacting with DynamoDB tables,
with support for both local development and production environments.
"""
import os
import boto3
import logging
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional, List, Union

# Configure logger
logger = logging.getLogger(__name__)


class DynamoDBClient:
    """
    A client for interacting with DynamoDB tables.
    
    This class provides a consistent interface for DynamoDB operations,
    with built-in error handling and support for both local and AWS environments.
    """
    
    def __init__(
        self,
        region_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        use_local: bool = False
    ):
        """
        Initialize the DynamoDB client.
        
        Args:
            region_name: The AWS region to use. Defaults to the value in AWS_REGION env var.
            endpoint_url: The endpoint URL for DynamoDB (useful for local testing).
            use_local: If True, uses a local DynamoDB instance.
        """
        self.region_name = region_name or os.environ.get('AWS_REGION', 'us-east-1')
        
        # Configure for local development if requested
        if use_local:
            self.endpoint_url = endpoint_url or 'http://localhost:8000'
            logger.info(f"Using local DynamoDB at {self.endpoint_url}")
        else:
            self.endpoint_url = endpoint_url
        
        # Initialize the client
        self.client = boto3.client(
            'dynamodb',
            region_name=self.region_name,
            endpoint_url=self.endpoint_url
        )
        
        # Initialize the resource
        self.resource = boto3.resource(
            'dynamodb',
            region_name=self.region_name,
            endpoint_url=self.endpoint_url
        )
        
        logger.info(f"DynamoDB client initialized for region {self.region_name}")
    
    def get_table(self, table_name: str):
        """
        Get a reference to a DynamoDB table.
        
        Args:
            table_name: The name of the table to get
            
        Returns:
            A DynamoDB Table resource
        """
        try:
            table = self.resource.Table(table_name)
            # Verify the table exists
            table.table_status
            return table
        except ClientError as e:
            logger.error(f"Error getting table {table_name}: {str(e)}")
            raise
    
    def put_item(self, table_name: str, item: Dict[str, Any], condition_expression: Optional[str] = None) -> Dict[str, Any]:
        """
        Put an item into a DynamoDB table.
        
        Args:
            table_name: The name of the table
            item: The item to put into the table
            condition_expression: Optional condition expression for the put operation
            
        Returns:
            The response from DynamoDB
        """
        table = self.get_table(table_name)
        try:
            params = {'Item': item}
            if condition_expression:
                params['ConditionExpression'] = condition_expression
            
            response = table.put_item(**params)
            logger.debug(f"Put item into {table_name} successfully")
            return response
        except ClientError as e:
            logger.error(f"Error putting item into {table_name}: {str(e)}")
            raise
    
    def get_item(self, table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get an item from a DynamoDB table.
        
        Args:
            table_name: The name of the table
            key: The primary key of the item to get
            
        Returns:
            The item from the table, or an empty dict if not found
        """
        table = self.get_table(table_name)
        try:
            response = table.get_item(Key=key)
            return response.get('Item', {})
        except ClientError as e:
            logger.error(f"Error getting item from {table_name}: {str(e)}")
            raise
    
    def update_item(
        self,
        table_name: str,
        key: Dict[str, Any],
        update_expression: str,
        expression_attribute_values: Dict[str, Any],
        expression_attribute_names: Optional[Dict[str, str]] = None,
        condition_expression: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an item in a DynamoDB table.
        
        Args:
            table_name: The name of the table
            key: The primary key of the item to update
            update_expression: The update expression
            expression_attribute_values: Values for the update expression
            expression_attribute_names: Names for the update expression
            condition_expression: Optional condition expression
            
        Returns:
            The response from DynamoDB
        """
        table = self.get_table(table_name)
        try:
            params = {
                'Key': key,
                'UpdateExpression': update_expression,
                'ExpressionAttributeValues': expression_attribute_values,
                'ReturnValues': 'ALL_NEW'
            }
            
            if expression_attribute_names:
                params['ExpressionAttributeNames'] = expression_attribute_names
                
            if condition_expression:
                params['ConditionExpression'] = condition_expression
            
            response = table.update_item(**params)
            logger.debug(f"Updated item in {table_name} successfully")
            return response
        except ClientError as e:
            logger.error(f"Error updating item in {table_name}: {str(e)}")
            raise
    
    def delete_item(
        self,
        table_name: str,
        key: Dict[str, Any],
        condition_expression: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete an item from a DynamoDB table.
        
        Args:
            table_name: The name of the table
            key: The primary key of the item to delete
            condition_expression: Optional condition expression
            
        Returns:
            The response from DynamoDB
        """
        table = self.get_table(table_name)
        try:
            params = {'Key': key}
            
            if condition_expression:
                params['ConditionExpression'] = condition_expression
            
            response = table.delete_item(**params)
            logger.debug(f"Deleted item from {table_name} successfully")
            return response
        except ClientError as e:
            logger.error(f"Error deleting item from {table_name}: {str(e)}")
            raise
    
    def query(
        self,
        table_name: str,
        key_condition_expression: str,
        expression_attribute_values: Dict[str, Any],
        expression_attribute_names: Optional[Dict[str, str]] = None,
        index_name: Optional[str] = None,
        scan_index_forward: bool = True,
        limit: Optional[int] = None,
        projection_expression: Optional[str] = None,
        exclusive_start_key: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query items from a DynamoDB table.
        
        Args:
            table_name: The name of the table
            key_condition_expression: The key condition expression
            expression_attribute_values: Values for the key condition expression
            expression_attribute_names: Names for the key condition expression
            index_name: Optional secondary index to query
            scan_index_forward: Whether to scan the index forward (True) or backward (False)
            limit: Optional maximum number of items to return
            projection_expression: Optional projection expression to limit returned attributes
            exclusive_start_key: Optional start key for pagination
            
        Returns:
            The response from DynamoDB
        """
        table = self.get_table(table_name)
        try:
            params = {
                'KeyConditionExpression': key_condition_expression,
                'ExpressionAttributeValues': expression_attribute_values,
                'ScanIndexForward': scan_index_forward
            }
            
            if expression_attribute_names:
                params['ExpressionAttributeNames'] = expression_attribute_names
                
            if index_name:
                params['IndexName'] = index_name
                
            if limit:
                params['Limit'] = limit
                
            if projection_expression:
                params['ProjectionExpression'] = projection_expression
                
            if exclusive_start_key:
                params['ExclusiveStartKey'] = exclusive_start_key
            
            response = table.query(**params)
            logger.debug(f"Query on {table_name} {'index ' + index_name if index_name else 'table'} returned {len(response.get('Items', []))} items")
            return response
        except ClientError as e:
            logger.error(f"Error querying {table_name}: {str(e)}")
            raise
    
    def scan(
        self,
        table_name: str,
        filter_expression: Optional[str] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        expression_attribute_names: Optional[Dict[str, str]] = None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        projection_expression: Optional[str] = None,
        exclusive_start_key: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Scan items from a DynamoDB table.
        
        Args:
            table_name: The name of the table
            filter_expression: Optional filter expression
            expression_attribute_values: Values for the filter expression
            expression_attribute_names: Names for the filter expression
            index_name: Optional secondary index to scan
            limit: Optional maximum number of items to return
            projection_expression: Optional projection expression to limit returned attributes
            exclusive_start_key: Optional start key for pagination
            
        Returns:
            The response from DynamoDB
        """
        table = self.get_table(table_name)
        try:
            params = {}
            
            if filter_expression:
                params['FilterExpression'] = filter_expression
                
            if expression_attribute_values:
                params['ExpressionAttributeValues'] = expression_attribute_values
                
            if expression_attribute_names:
                params['ExpressionAttributeNames'] = expression_attribute_names
                
            if index_name:
                params['IndexName'] = index_name
                
            if limit:
                params['Limit'] = limit
                
            if projection_expression:
                params['ProjectionExpression'] = projection_expression
                
            if exclusive_start_key:
                params['ExclusiveStartKey'] = exclusive_start_key
            
            response = table.scan(**params)
            logger.debug(f"Scan on {table_name} {'index ' + index_name if index_name else 'table'} returned {len(response.get('Items', []))} items")
            return response
        except ClientError as e:
            logger.error(f"Error scanning {table_name}: {str(e)}")
            raise
    
    def batch_get_items(
        self,
        table_items_keys: Dict[str, List[Dict[str, Any]]],
        projection_expression: Optional[Dict[str, str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Batch get items from multiple DynamoDB tables.
        
        Args:
            table_items_keys: A dict mapping table names to lists of item keys
            projection_expression: Optional dict mapping table names to projection expressions
            
        Returns:
            A dict mapping table names to lists of items
        """
        try:
            request_items = {}
            for table_name, keys in table_items_keys.items():
                if not keys:
                    continue
                    
                table_request = {'Keys': keys}
                
                if projection_expression and table_name in projection_expression:
                    table_request['ProjectionExpression'] = projection_expression[table_name]
                    
                request_items[table_name] = table_request
            
            if not request_items:
                return {}
            
            response = self.resource.batch_get_item(RequestItems=request_items)
            
            # Process the response
            result = {}
            if 'Responses' in response:
                result = response['Responses']
                
            # Handle unprocessed items
            if 'UnprocessedKeys' in response and response['UnprocessedKeys']:
                logger.warning(f"Some items were not processed in batch_get_items: {response['UnprocessedKeys']}")
                
            return result
        except ClientError as e:
            logger.error(f"Error in batch_get_items: {str(e)}")
            raise
    
    def batch_write_items(
        self,
        table_items: Dict[str, List[Dict[str, Any]]],
        delete_items: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Batch write (put or delete) items to multiple DynamoDB tables.
        
        Args:
            table_items: A dict mapping table names to lists of items to put
            delete_items: A dict mapping table names to lists of item keys to delete
            
        Returns:
            A dict of unprocessed items
        """
        try:
            request_items = {}
            
            # Process put requests
            for table_name, items in table_items.items():
                if not items:
                    continue
                    
                write_requests = [{'PutRequest': {'Item': item}} for item in items]
                request_items[table_name] = write_requests
            
            # Process delete requests
            if delete_items:
                for table_name, keys in delete_items.items():
                    if not keys:
                        continue
                        
                    write_requests = [{'DeleteRequest': {'Key': key}} for key in keys]
                    
                    if table_name in request_items:
                        request_items[table_name].extend(write_requests)
                    else:
                        request_items[table_name] = write_requests
            
            if not request_items:
                return {}
            
            response = self.resource.batch_write_item(RequestItems=request_items)
            
            # Handle unprocessed items
            if 'UnprocessedItems' in response and response['UnprocessedItems']:
                logger.warning(f"Some items were not processed in batch_write_items: {response['UnprocessedItems']}")
                
            return response.get('UnprocessedItems', {})
        except ClientError as e:
            logger.error(f"Error in batch_write_items: {str(e)}")
            raise
    
    def create_table(
        self,
        table_name: str,
        key_schema: List[Dict[str, str]],
        attribute_definitions: List[Dict[str, str]],
        provisioned_throughput: Dict[str, int],
        global_secondary_indexes: Optional[List[Dict[str, Any]]] = None,
        local_secondary_indexes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Create a DynamoDB table.
        
        Args:
            table_name: The name of the table to create
            key_schema: The key schema for the table
            attribute_definitions: The attribute definitions for the table
            provisioned_throughput: The provisioned throughput for the table
            global_secondary_indexes: Optional global secondary indexes to create
            local_secondary_indexes: Optional local secondary indexes to create
            
        Returns:
            The response from DynamoDB
        """
        try:
            params = {
                'TableName': table_name,
                'KeySchema': key_schema,
                'AttributeDefinitions': attribute_definitions,
                'ProvisionedThroughput': provisioned_throughput
            }
            
            if global_secondary_indexes:
                params['GlobalSecondaryIndexes'] = global_secondary_indexes
                
            if local_secondary_indexes:
                params['LocalSecondaryIndexes'] = local_secondary_indexes
            
            response = self.client.create_table(**params)
            logger.info(f"Created table {table_name}")
            return response
        except ClientError as e:
            logger.error(f"Error creating table {table_name}: {str(e)}")
            raise
    
    def delete_table(self, table_name: str) -> Dict[str, Any]:
        """
        Delete a DynamoDB table.
        
        Args:
            table_name: The name of the table to delete
            
        Returns:
            The response from DynamoDB
        """
        try:
            response = self.client.delete_table(TableName=table_name)
            logger.info(f"Deleted table {table_name}")
            return response
        except ClientError as e:
            logger.error(f"Error deleting table {table_name}: {str(e)}")
            raise
    
    def describe_table(self, table_name: str) -> Dict[str, Any]:
        """
        Describe a DynamoDB table.
        
        Args:
            table_name: The name of the table to describe
            
        Returns:
            The table description
        """
        try:
            response = self.client.describe_table(TableName=table_name)
            return response.get('Table', {})
        except ClientError as e:
            logger.error(f"Error describing table {table_name}: {str(e)}")
            raise
    
    def list_tables(self) -> List[str]:
        """
        List all DynamoDB tables.
        
        Returns:
            A list of table names
        """
        try:
            response = self.client.list_tables()
            return response.get('TableNames', [])
        except ClientError as e:
            logger.error(f"Error listing tables: {str(e)}")
            raise 