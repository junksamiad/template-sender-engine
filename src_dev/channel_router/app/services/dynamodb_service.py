"""
Service functions for interacting with DynamoDB.
"""

import os
import boto3
import logging
from typing import Dict, Any, Optional, Tuple, Union, TYPE_CHECKING
from botocore.exceptions import ClientError
from decimal import Decimal

# Import boto3 types for type hinting if available
if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource, Table

logger = logging.getLogger(__name__)
# Removed setLevel as it's typically handled by the root logger config

# Initialize DynamoDB resource and table object - REMOVED
# try:
#     # The env var will be set in the Lambda function configuration
#     company_data_table_name = os.environ.get('COMPANY_DATA_TABLE')
#     
#     if company_data_table_name:
#         dynamodb = boto3.resource('dynamodb')
#         company_table = dynamodb.Table(company_data_table_name)
#         logger.info(f"Successfully initialized DynamoDB table: {company_data_table_name}")
#     else:
#         logger.warning("COMPANY_DATA_TABLE environment variable not set.")
#         company_table = None
#
# except Exception as e:
#     logger.error(f"Failed to initialize DynamoDB: {str(e)}")
#     company_table = None

# --- Helper function to handle Decimal types --- 
def replace_decimals(obj: Any) -> Any:
    """Recursively converts Decimal objects in a dict/list to int/float."""
    if isinstance(obj, list):
        return [replace_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: replace_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        # Convert Decimal to int if it's a whole number, otherwise float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj
# -----------------------------------------------

# Standard error return types
DATABASE_ERROR = "DATABASE_ERROR", "Failed to access the database"
COMPANY_NOT_FOUND = "COMPANY_NOT_FOUND", "Company and project combination not found"
PROJECT_INACTIVE = "PROJECT_INACTIVE", "Project is not active"
CONFIGURATION_ERROR = "CONFIGURATION_ERROR", "DynamoDB configuration error"

def get_company_config(
    company_id: str,
    project_id: str,
    # Add optional table argument for DI
    ddb_table: Optional['Table'] = None
) -> Union[Dict, Tuple[str, str]]:
    """
    Retrieve the active company configuration item from DynamoDB.
    
    Args:
        company_id (str): The company identifier.
        project_id (str): The project identifier.
        ddb_table (Table, optional): The DynamoDB table object. If None, attempts to initialize.
        
    Returns:
        Union[Dict, Tuple[str, str]]: Either a dictionary of the item (if found and active, 
                                    with Decimals converted) 
                                    or a tuple of (error_code, error_message).
    """
    # Initialize table inside function if not provided
    if ddb_table is None:
        company_data_table_name = os.environ.get('COMPANY_DATA_TABLE')
        if not company_data_table_name:
            logger.warning("COMPANY_DATA_TABLE environment variable not set.")
            return CONFIGURATION_ERROR
        try:
            dynamodb_resource: 'DynamoDBServiceResource' = boto3.resource('dynamodb')
            ddb_table = dynamodb_resource.Table(company_data_table_name)
            logger.debug(f"Initialized default DynamoDB table: {company_data_table_name}")
        except Exception as e:
            logger.error(f"Failed to initialize default DynamoDB table: {str(e)}")
            return CONFIGURATION_ERROR

    # Check again after attempting initialization
    if ddb_table is None:
        logger.error("DynamoDB table could not be initialized.")
        return CONFIGURATION_ERROR

    try:
        # Fetch the item from DynamoDB using the provided/initialized table
        logger.info(f"Fetching company configuration for company_id={company_id}, project_id={project_id}")
        response = ddb_table.get_item(
            Key={'company_id': company_id, 'project_id': project_id}
        )
        
        # Check if item exists
        if 'Item' not in response:
            logger.warning(f"Company not found: company_id={company_id}, project_id={project_id}")
            return COMPANY_NOT_FOUND
            
        company_data_raw = response['Item']
        
        # Check if project is active
        if company_data_raw.get('project_status') != 'active':
            logger.warning(f"Project is not active: company_id={company_id}, project_id={project_id}, status={company_data_raw.get('project_status')}")
            return PROJECT_INACTIVE
            
        # Convert Decimal types before returning
        company_data_processed = replace_decimals(company_data_raw)
        
        logger.info(f"Successfully retrieved and processed active configuration for company_id={company_id}, project_id={project_id}")
        return company_data_processed
        
    except ClientError as e:
        logger.error(f"DynamoDB ClientError: {str(e)}")
        return DATABASE_ERROR
    except Exception as e:
        logger.error(f"Unexpected error retrieving company data: {str(e)}")
        return DATABASE_ERROR 