"""
Pagination utilities for DynamoDB queries in the AI Multi-Communications Engine.

This module provides helpers for paginated access to DynamoDB tables.
"""
import logging
from typing import Dict, Any, List, Optional, Union, Callable, Generic, TypeVar, Iterator

from src.shared.database.dynamo_client import DynamoDBClient

# Configure logger
logger = logging.getLogger(__name__)

T = TypeVar('T')


class PaginationHelper(Generic[T]):
    """
    Helper for paginated access to DynamoDB tables.
    
    This class provides utilities for handling pagination in DynamoDB queries,
    with support for both automatic and manual pagination.
    """
    
    def __init__(
        self,
        dynamodb_client: Optional[DynamoDBClient] = None,
        item_transformer: Optional[Callable[[Dict[str, Any]], T]] = None
    ):
        """
        Initialize the pagination helper.
        
        Args:
            dynamodb_client: Optional DynamoDB client to use
            item_transformer: Optional function to transform items
        """
        self.dynamodb_client = dynamodb_client or DynamoDBClient()
        self.item_transformer = item_transformer or (lambda x: x)  # Default: identity function
    
    def paginate_query(
        self,
        table_name: str,
        key_condition_expression: str,
        expression_attribute_values: Dict[str, Any],
        expression_attribute_names: Optional[Dict[str, str]] = None,
        index_name: Optional[str] = None,
        scan_index_forward: bool = True,
        limit: Optional[int] = None,
        projection_expression: Optional[str] = None,
        max_items: Optional[int] = None,
        page_size: int = 100
    ) -> List[T]:
        """
        Execute a paginated query and return all results.
        
        This method automatically handles pagination and returns all results.
        
        Args:
            table_name: The name of the table to query
            key_condition_expression: The key condition expression
            expression_attribute_values: Values for the key condition expression
            expression_attribute_names: Names for the key condition expression
            index_name: Optional secondary index to query
            scan_index_forward: Whether to scan the index forward (True) or backward (False)
            limit: Optional maximum number of items to return in the query
            projection_expression: Optional projection expression
            max_items: Optional maximum number of items to return in total
            page_size: Number of items per page
            
        Returns:
            A list of items
        """
        try:
            result = []
            exclusive_start_key = None
            
            # Use the specified page size or limit
            effective_page_size = min(page_size, limit) if limit else page_size
            
            while True:
                # Execute the query
                response = self.dynamodb_client.query(
                    table_name=table_name,
                    key_condition_expression=key_condition_expression,
                    expression_attribute_values=expression_attribute_values,
                    expression_attribute_names=expression_attribute_names,
                    index_name=index_name,
                    scan_index_forward=scan_index_forward,
                    limit=effective_page_size,
                    projection_expression=projection_expression,
                    exclusive_start_key=exclusive_start_key
                )
                
                # Process items
                items = response.get("Items", [])
                for item in items:
                    result.append(self.item_transformer(item))
                    
                    # Check if we've reached the maximum number of items
                    if max_items and len(result) >= max_items:
                        return result[:max_items]
                
                # Check if there are more items
                exclusive_start_key = response.get("LastEvaluatedKey")
                if not exclusive_start_key:
                    break
            
            return result
        except Exception as e:
            logger.error(f"Error in paginate_query: {str(e)}")
            raise
    
    def paginate_scan(
        self,
        table_name: str,
        filter_expression: Optional[str] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        expression_attribute_names: Optional[Dict[str, str]] = None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        projection_expression: Optional[str] = None,
        max_items: Optional[int] = None,
        page_size: int = 100
    ) -> List[T]:
        """
        Execute a paginated scan and return all results.
        
        This method automatically handles pagination and returns all results.
        
        Args:
            table_name: The name of the table to scan
            filter_expression: Optional filter expression
            expression_attribute_values: Values for the filter expression
            expression_attribute_names: Names for the filter expression
            index_name: Optional secondary index to scan
            limit: Optional maximum number of items to return in the scan
            projection_expression: Optional projection expression
            max_items: Optional maximum number of items to return in total
            page_size: Number of items per page
            
        Returns:
            A list of items
        """
        try:
            result = []
            exclusive_start_key = None
            
            # Use the specified page size or limit
            effective_page_size = min(page_size, limit) if limit else page_size
            
            while True:
                # Execute the scan
                response = self.dynamodb_client.scan(
                    table_name=table_name,
                    filter_expression=filter_expression,
                    expression_attribute_values=expression_attribute_values,
                    expression_attribute_names=expression_attribute_names,
                    index_name=index_name,
                    limit=effective_page_size,
                    projection_expression=projection_expression,
                    exclusive_start_key=exclusive_start_key
                )
                
                # Process items
                items = response.get("Items", [])
                for item in items:
                    result.append(self.item_transformer(item))
                    
                    # Check if we've reached the maximum number of items
                    if max_items and len(result) >= max_items:
                        return result[:max_items]
                
                # Check if there are more items
                exclusive_start_key = response.get("LastEvaluatedKey")
                if not exclusive_start_key:
                    break
            
            return result
        except Exception as e:
            logger.error(f"Error in paginate_scan: {str(e)}")
            raise
    
    def get_page(
        self,
        table_name: str,
        is_scan: bool = False,
        key_condition_expression: Optional[str] = None,
        filter_expression: Optional[str] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        expression_attribute_names: Optional[Dict[str, str]] = None,
        index_name: Optional[str] = None,
        scan_index_forward: bool = True,
        limit: int = 25,
        projection_expression: Optional[str] = None,
        exclusive_start_key: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get a single page of results.
        
        This method is useful for manual pagination where you want to display
        results page by page and provide "next page" functionality.
        
        Args:
            table_name: The name of the table
            is_scan: Whether to use scan (True) or query (False)
            key_condition_expression: The key condition expression (for query)
            filter_expression: The filter expression (for scan)
            expression_attribute_values: Values for expressions
            expression_attribute_names: Names for expressions
            index_name: Optional secondary index
            scan_index_forward: Whether to scan forward (for query)
            limit: Maximum number of items per page
            projection_expression: Optional projection expression
            exclusive_start_key: Optional key to start from
            
        Returns:
            A dict containing items and pagination information
        """
        try:
            if is_scan:
                # Execute a scan
                response = self.dynamodb_client.scan(
                    table_name=table_name,
                    filter_expression=filter_expression,
                    expression_attribute_values=expression_attribute_values,
                    expression_attribute_names=expression_attribute_names,
                    index_name=index_name,
                    limit=limit,
                    projection_expression=projection_expression,
                    exclusive_start_key=exclusive_start_key
                )
            else:
                # Execute a query
                response = self.dynamodb_client.query(
                    table_name=table_name,
                    key_condition_expression=key_condition_expression,
                    expression_attribute_values=expression_attribute_values,
                    expression_attribute_names=expression_attribute_names,
                    index_name=index_name,
                    scan_index_forward=scan_index_forward,
                    limit=limit,
                    projection_expression=projection_expression,
                    exclusive_start_key=exclusive_start_key
                )
            
            # Transform items
            items = [self.item_transformer(item) for item in response.get("Items", [])]
            
            # Return items and pagination info
            return {
                "items": items,
                "count": len(items),
                "next_page_key": response.get("LastEvaluatedKey"),
                "has_more": "LastEvaluatedKey" in response
            }
        except Exception as e:
            logger.error(f"Error in get_page: {str(e)}")
            raise
    
    def query_iterator(
        self,
        table_name: str,
        key_condition_expression: str,
        expression_attribute_values: Dict[str, Any],
        expression_attribute_names: Optional[Dict[str, str]] = None,
        index_name: Optional[str] = None,
        scan_index_forward: bool = True,
        limit: Optional[int] = None,
        projection_expression: Optional[str] = None,
        page_size: int = 100
    ) -> Iterator[T]:
        """
        Create an iterator for query results.
        
        This method is useful for processing large result sets without
        loading everything into memory at once.
        
        Args:
            table_name: The name of the table to query
            key_condition_expression: The key condition expression
            expression_attribute_values: Values for the key condition expression
            expression_attribute_names: Names for the key condition expression
            index_name: Optional secondary index to query
            scan_index_forward: Whether to scan the index forward (True) or backward (False)
            limit: Optional maximum number of items to return in the query
            projection_expression: Optional projection expression
            page_size: Number of items per page
            
        Returns:
            An iterator for query results
        """
        try:
            # Use the specified page size or limit
            effective_page_size = min(page_size, limit) if limit else page_size
            
            # Total items yielded
            total_yielded = 0
            
            # Start key for pagination
            exclusive_start_key = None
            
            while True:
                # Execute the query
                response = self.dynamodb_client.query(
                    table_name=table_name,
                    key_condition_expression=key_condition_expression,
                    expression_attribute_values=expression_attribute_values,
                    expression_attribute_names=expression_attribute_names,
                    index_name=index_name,
                    scan_index_forward=scan_index_forward,
                    limit=effective_page_size,
                    projection_expression=projection_expression,
                    exclusive_start_key=exclusive_start_key
                )
                
                # Process items
                items = response.get("Items", [])
                for item in items:
                    # Check if we've reached the limit
                    if limit and total_yielded >= limit:
                        return
                        
                    # Yield the transformed item
                    yield self.item_transformer(item)
                    total_yielded += 1
                
                # Check if there are more items
                exclusive_start_key = response.get("LastEvaluatedKey")
                if not exclusive_start_key:
                    break
        except Exception as e:
            logger.error(f"Error in query_iterator: {str(e)}")
            raise
    
    def scan_iterator(
        self,
        table_name: str,
        filter_expression: Optional[str] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        expression_attribute_names: Optional[Dict[str, str]] = None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        projection_expression: Optional[str] = None,
        page_size: int = 100
    ) -> Iterator[T]:
        """
        Create an iterator for scan results.
        
        This method is useful for processing large result sets without
        loading everything into memory at once.
        
        Args:
            table_name: The name of the table to scan
            filter_expression: Optional filter expression
            expression_attribute_values: Values for the filter expression
            expression_attribute_names: Names for the filter expression
            index_name: Optional secondary index to scan
            limit: Optional maximum number of items to return in the scan
            projection_expression: Optional projection expression
            page_size: Number of items per page
            
        Returns:
            An iterator for scan results
        """
        try:
            # Use the specified page size or limit
            effective_page_size = min(page_size, limit) if limit else page_size
            
            # Total items yielded
            total_yielded = 0
            
            # Start key for pagination
            exclusive_start_key = None
            
            while True:
                # Execute the scan
                response = self.dynamodb_client.scan(
                    table_name=table_name,
                    filter_expression=filter_expression,
                    expression_attribute_values=expression_attribute_values,
                    expression_attribute_names=expression_attribute_names,
                    index_name=index_name,
                    limit=effective_page_size,
                    projection_expression=projection_expression,
                    exclusive_start_key=exclusive_start_key
                )
                
                # Process items
                items = response.get("Items", [])
                for item in items:
                    # Check if we've reached the limit
                    if limit and total_yielded >= limit:
                        return
                        
                    # Yield the transformed item
                    yield self.item_transformer(item)
                    total_yielded += 1
                
                # Check if there are more items
                exclusive_start_key = response.get("LastEvaluatedKey")
                if not exclusive_start_key:
                    break
        except Exception as e:
            logger.error(f"Error in scan_iterator: {str(e)}")
            raise 