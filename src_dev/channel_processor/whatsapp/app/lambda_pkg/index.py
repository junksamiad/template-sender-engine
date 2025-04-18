"""
Channel Processor Lambda for the AI Multi-Communications Engine.

This Lambda function processes messages from SQS queues (starting with WhatsApp),
manages conversation state in DynamoDB, interacts with AI services (OpenAI),
and sends messages via the appropriate channel provider (e.g., Twilio for WhatsApp).
"""
import os
import json
import boto3
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone # For timestamp generation
import time # For processing time calculation

# --- Import utility and service modules using relative paths for package execution --- # Updated comment
# (Keep commented out lines for reference if needed)
# from utils.context_utils import deserialize_context, validate_context
# from utils.sqs_heartbeat import SQSHeartbeat
# from services.dynamodb_service import create_initial_conversation_record, update_conversation_after_send
# from services.secrets_manager_service import get_secret
# from services.openai_service import process_message_with_ai
# from services.twilio_service import send_whatsapp_template_message
from .utils import context_utils
from .utils.sqs_heartbeat import SQSHeartbeat
from .services import dynamodb_service
from .services import secrets_manager_service
from .services import openai_service
from .services import twilio_service

# Initialize logger
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Get environment variables - TO BE POPULATED in Lambda config
# Read inside handler to allow testing with patched environment
# CONVERSATIONS_TABLE = os.environ.get("CONVERSATIONS_TABLE") # e.g., conversations-dev
# WHATSAPP_QUEUE_URL = os.environ.get("WHATSAPP_QUEUE_URL") # e.g., url for ai-multi-comms-whatsapp-queue-dev

# COMPANY_TABLE_NAME = os.environ.get("COMPANY_TABLE_NAME")  # REMOVED: Not needed by processor
# Default to eu-north-1 as discussed
SECRETS_MANAGER_REGION = os.environ.get("SECRETS_MANAGER_REGION", "eu-north-1")
# Read inside handler
# SQS_HEARTBEAT_INTERVAL_MS = int(os.environ.get("SQS_HEARTBEAT_INTERVAL_MS", "300000")) # 5 minutes default, matches LLD
# Set default version as requested
VERSION = os.environ.get("VERSION", "processor-1.0.0") # Version of this Lambda

# Initialize AWS clients - REMOVED: To be initialized within service modules
# sqs_client = boto3.client("sqs")
# dynamodb = boto3.resource("dynamodb")
# secrets_manager = boto3.client("secretsmanager", region_name=SECRETS_MANAGER_REGION)

# Placeholder for DynamoDB Table resources (initialized if variables are set) - REMOVED
# conversations_table = None
# company_table = None
# if CONVERSATIONS_TABLE:
#     conversations_table = dynamodb.Table(CONVERSATIONS_TABLE)
# if COMPANY_TABLE_NAME:
#     company_table = dynamodb.Table(COMPANY_TABLE_NAME)

logger.info(f"Channel Processor Lambda initialized. Version: {VERSION}")
# logger.info(f"Target Conversations Table ENV: {CONVERSATIONS_TABLE}") # Removed log
# logger.info(f"Target Company Table ENV: {COMPANY_TABLE_NAME}") # REMOVED
# logger.info(f"WHATSAPP_QUEUE_URL: {WHATSAPP_QUEUE_URL}") # Removed log
logger.info(f"SECRETS_MANAGER_REGION: {SECRETS_MANAGER_REGION}")
# logger.info(f"SQS_HEARTBEAT_INTERVAL_MS: {SQS_HEARTBEAT_INTERVAL_MS}") # Removed log


# Modify handler signature to accept dependencies with defaults
# def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
def lambda_handler(
    event: Dict[str, Any],
    context: Any,
    *, # Force keyword arguments for injected dependencies
    ctx_utils=context_utils,
    HeartbeatClass=SQSHeartbeat,
    db_service=dynamodb_service,
    sm_service=secrets_manager_service,
    ai_service=openai_service,
    msg_service=twilio_service,
    log=logger # Use the globally configured logger by default
) -> Dict[str, Any]:
    """
    Main Lambda handler function.
    Processes records from an SQS event.
    Injectable dependencies: ctx_utils, HeartbeatClass, db_service, sm_service, ai_service, msg_service, log
    """
    log.info(f"Received event: {json.dumps(event)}") # Use injected logger

    # Get critical environment variables inside the handler
    conversations_table_name = os.environ.get("CONVERSATIONS_TABLE")
    whatsapp_queue_url = os.environ.get("WHATSAPP_QUEUE_URL")
    # Also get heartbeat interval here
    try:
        sqs_heartbeat_interval_ms = int(os.environ.get("SQS_HEARTBEAT_INTERVAL_MS", "300000"))
    except (ValueError, TypeError):
        log.warning("Invalid SQS_HEARTBEAT_INTERVAL_MS environment variable. Using default 300000ms.")
        sqs_heartbeat_interval_ms = 300000

    # Check for essential environment variables
    # if not CONVERSATIONS_TABLE or not WHATSAPP_QUEUE_URL:
    if not conversations_table_name or not whatsapp_queue_url:
        log.error("Missing critical environment variables: CONVERSATIONS_TABLE, WHATSAPP_QUEUE_URL") # Use injected logger
        # In a real scenario, might return failure or raise exception
        return {"statusCode": 500, "body": "Missing environment variables"}
    else:
        # Log them now that we know they exist
        log.info(f"Using CONVERSATIONS_TABLE: {conversations_table_name}")
        log.info(f"Using WHATSAPP_QUEUE_URL: {whatsapp_queue_url}")

    successful_record_ids = []
    failed_record_ids = []

    for record in event.get("Records", []):
        record_id = record.get("messageId", "unknown")
        heartbeat = None # Initialize heartbeat to None for each record
        log.info(f"Processing record {record_id}...") # Use injected logger
        try:
            # --- Detailed Processing Steps ---
            log.debug(f"Raw record body: {record.get('body')}") # Use injected logger

            # Record start time for processing duration calculation
            processing_start_time = time.time()

            # Get ApproximateReceiveCount
            attributes = record.get('attributes', {})
            approx_receive_count_str = attributes.get('ApproximateReceiveCount', '1')
            try:
                approx_receive_count = int(approx_receive_count_str)
            except (ValueError, TypeError):
                log.warning(f"Could not parse ApproximateReceiveCount '{approx_receive_count_str}' for record {record_id}. Assuming 1.")
                approx_receive_count = 1
            log.info(f"Record {record_id} ApproximateReceiveCount: {approx_receive_count}")

            # 1. Parse SQS message body to get the Context Object JSON string
            context_json = record.get('body')
            if not context_json:
                log.error(f"Record {record_id} has empty body.") # Use injected logger
                raise ValueError("Empty record body")

            # 2. Deserialize and Validate Context Object
            #    - Calls functions from utils.context_utils via injected module
            # context_object = deserialize_context(context_json) # Will raise ValueError on JSON error
            # validation_errors = validate_context(context_object) # Returns list of errors or empty list
            context_object = ctx_utils.deserialize_context(context_json)
            validation_errors = ctx_utils.validate_context(context_object)


            if validation_errors:
                # Log specific errors and fail the record processing
                error_string = ", ".join(validation_errors)
                log.error(f"Context validation failed for {record_id}: {error_string}") # Use injected logger
                raise ValueError(f"Context validation failed: {error_string}")

            # Extract relevant IDs for logging now that validation passed
            req_id = context_object.get('frontend_payload', {}).get('request_data', {}).get('request_id', 'unknown_req_id')
            conv_id = context_object.get('conversation_data', {}).get('conversation_id', 'unknown_conv_id')
            channel_method = context_object.get('frontend_payload', {}).get('request_data', {}).get('channel_method') # Extract channel_method

            # Add a check to ensure channel_method was actually found after validation
            if not channel_method:
                log.error(f"Context validation passed but channel_method is missing for {record_id}") # Use injected logger
                raise ValueError("Missing channel_method in validated context")

            # --- Define ai_config and channel_ai_config early --- # Ensure in scope
            ai_config = context_object.get('company_data_payload', {}).get('ai_config', {}).get('openai_config', {})
            channel_ai_config = ai_config.get(channel_method, {})
            if not channel_ai_config:
                log.error(f"Missing 'openai_config.{channel_method}' in context_object. Cannot proceed.") # Use injected logger
                raise ValueError(f"Missing OpenAI channel configuration for {channel_method}")
            # --- End early definition ---

            log.info(f"Successfully deserialized and validated context for Request ID: {req_id}, Conversation ID: {conv_id}, Channel: {channel_method} (SQS ID: {record_id})") # Use injected logger

            # 3. Start SQS Heartbeat to extend visibility timeout
            #    - Uses injected HeartbeatClass
            receipt_handle = record.get('receiptHandle')
            if not receipt_handle:
                log.warning(f"Missing receiptHandle for record {record_id}, heartbeat disabled.") # Use injected logger
                # heartbeat remains None
            else:
                # Calculate interval in seconds using value read inside handler
                heartbeat_interval_sec = sqs_heartbeat_interval_ms / 1000
                # Validate interval is positive before creating heartbeat
                if heartbeat_interval_sec <= 0:
                     log.error(f"Invalid SQS_HEARTBEAT_INTERVAL_MS ({sqs_heartbeat_interval_ms}ms) resulted in non-positive interval ({heartbeat_interval_sec}s). Heartbeat disabled.") # Use injected logger
                     # heartbeat remains None
                else:
                    try:
                        # heartbeat = SQSHeartbeat( ... ) # Use injected class
                        heartbeat = HeartbeatClass(
                            # queue_url=WHATSAPP_QUEUE_URL, # Use variable read inside handler
                            queue_url=whatsapp_queue_url,
                            receipt_handle=receipt_handle,
                            interval_sec=int(heartbeat_interval_sec) # Ensure integer
                            # Default visibility timeout extension (600s) is used from SQSHeartbeat class
                        )
                        heartbeat.start()
                        log.info(f"SQS Heartbeat started for {record_id}") # Use injected logger
                    except Exception as hb_init_error:
                         log.exception(f"Failed to initialize or start SQS heartbeat for {record_id}: {hb_init_error}") # Use injected logger
                         # heartbeat remains None or becomes None if start failed within constructor potentially
                         heartbeat = None # Ensure it's None if init/start fails

            # 4. Create/Update DynamoDB Conversation Record (Idempotent)
            #    - Uses injected db_service module
            record_created_ok = db_service.create_initial_conversation_record(
                context_object=context_object, ddb_table=None
                )
            if not record_created_ok:
                # ConditionalCheckFailed or other error during create prevented record creation/returned False.
                # Check the receive count to determine the likely scenario.
                if approx_receive_count == 1:
                    # Likely a duplicate request via Router (Scenario 1)
                    log.warning(f"Halting processing for record {record_id} (Receive Count: 1) as record already exists (likely duplicate request).")
                else: 
                    # SQS Redelivery after previous failure (Scenario 2)
                    log.warning(f"Halting processing for redelivered record {record_id} (Receive Count: {approx_receive_count}) as record already exists.")
                
                # In both cases (duplicate request or redelivery), the current design is to stop processing.
                # We treat this as a success for SQS message deletion purposes to avoid infinite loops/DLQ for handled duplicates.
                successful_record_ids.append(record_id) 
                if heartbeat and heartbeat.running:
                    heartbeat.stop()
                    log.info(f"SQS Heartbeat stopped for halted record {record_id} (duplicate/redelivered).")
                
                # *** ADD EXTRA LOGGING BEFORE CONTINUE ***
                log.info(f"INTENTIONAL CONTINUE for duplicate/redelivered record {record_id}. Skipping rest of loop iteration.")
                continue # Skip rest of processing for this duplicate/redelivered message
            else:
                # Record created successfully
                log.info(f"DynamoDB record check/creation successful for conversation ID {conv_id} (SQS ID: {record_id})") # Use injected logger

            # 5. Fetch Credentials (Secrets Manager)
            #    - Uses injected sm_service module
            log.info(f"Initiating Step 5: Fetch credentials for {conv_id}")
            try:
                # --- Fetch and Process OpenAI Key ---
                openai_api_key_ref = context_object.get('company_data_payload', {}).get('ai_config', {}).get('openai_config', {}).get(channel_method, {}).get('api_key_reference')
                if not openai_api_key_ref:
                    raise ValueError("Missing OpenAI api_key_reference in context")
                
                openai_secret_value = sm_service.get_secret(openai_api_key_ref)
                if openai_secret_value is None:
                    raise ValueError("Failed to retrieve OpenAI credentials value")

                # Extract the actual key string (since we know it's stored as JSON: {'ai_api_key': 'sk-...'}) 
                openai_api_key_string = None
                if isinstance(openai_secret_value, dict):
                    # Look for the key used in openai_service.py
                    openai_api_key_string = openai_secret_value.get('ai_api_key') 
                    if not openai_api_key_string:
                        raise ValueError("OpenAI secret dictionary missing expected key 'ai_api_key'")
                elif isinstance(openai_secret_value, str):
                    # Handle case where secret might be stored as plain string unexpectedly
                    log.warning("OpenAI secret was retrieved as a string, not the expected dictionary format.")
                    openai_api_key_string = openai_secret_value 
                else:
                    raise ValueError(f"Unexpected type ({type(openai_secret_value)}) for OpenAI credentials value")

                # Log success *after* successfully processing/extracting the key
                log.info(f"Successfully processed OpenAI credentials for conversation {conv_id}") 

                # --- Fetch and Process Twilio Credentials ---
                twilio_creds_ref = context_object.get('company_data_payload', {}).get('channel_config', {}).get(channel_method, {}).get('whatsapp_credentials_id')
                if not twilio_creds_ref:
                    raise ValueError("Missing Twilio whatsapp_credentials_id in context")
                
                twilio_secret_value = sm_service.get_secret(twilio_creds_ref)
                if twilio_secret_value is None:
                    raise ValueError("Failed to retrieve Twilio credentials value")
                
                # Ensure we have a dictionary for Twilio credentials
                twilio_creds = {}
                if isinstance(twilio_secret_value, str):
                    try:
                        twilio_creds = json.loads(twilio_secret_value)
                        log.info(f"Successfully fetched and parsed Twilio credentials string for conversation {conv_id}")
                    except json.JSONDecodeError as json_err:
                        log.error(f"Failed to parse Twilio credentials JSON string for ref {twilio_creds_ref}: {json_err}")
                        raise ValueError(f"Failed to parse Twilio credentials JSON: {json_err}") from json_err
                elif isinstance(twilio_secret_value, dict):
                    twilio_creds = twilio_secret_value
                    log.info(f"Successfully fetched pre-parsed Twilio credentials dictionary for conversation {conv_id}")
                else:
                    raise ValueError(f"Unexpected type ({type(twilio_secret_value)}) for Twilio credentials value")
                
                # Validate required keys exist in the final dictionary
                if 'twilio_account_sid' not in twilio_creds or 'twilio_auth_token' not in twilio_creds:
                    raise ValueError("Processed Twilio credentials missing required keys (account_sid/auth_token)")
                    
            except (ValueError, sm_service.SecretsManagerError) as cred_error:
                log.error(f"Error fetching/processing credentials for Request ID {req_id}: {cred_error}")
                raise cred_error # Re-raise to be caught by main handler

            # 6. Core Message Processing Logic (OpenAI Interaction)
            #    - Uses injected ai_service module
            # --- Prepare details for OpenAI service ---
            log.debug("Preparing details for OpenAI service...") # Use injected logger
            
            # Extract the specific Assistant ID needed for this step
            assistant_id = channel_ai_config.get('assistant_id_template_sender')
            if not assistant_id:
                 log.error(f"Missing 'assistant_id_template_sender' in context_object for channel {channel_method}. Cannot proceed with AI step.") # Use injected logger
                 raise ValueError(f"Missing assistant_id_template_sender for {channel_method}")

            # Extract other required pieces from context_object
            # conv_id was defined earlier after context validation
            # project_data = context_object.get('frontend_payload', {}).get('project_data') # Redundant if already extracted?
            # recipient_data = context_object.get('frontend_payload', {}).get('recipient_data')
            # company_name = context_object.get('company_data_payload', {}).get('company_name')
            # project_name = context_object.get('company_data_payload', {}).get('project_name')
            # company_rep = context_object.get('company_data_payload', {}).get('company_rep')
            # ai_channel_config = ai_config.get(channel_method, {}) # Already have this
            # all_channel_contact_info = ... # We need to build this here

            # Build the conversation_details dictionary required by the service
            # Note: thread_id is explicitly set to None as this is the initial call
            conversation_details = {
                "conversation_id": conv_id, 
                "thread_id": None, 
                "assistant_id": assistant_id,
                "project_data": context_object.get('frontend_payload', {}).get('project_data'),
                "recipient_data": context_object.get('frontend_payload', {}).get('recipient_data'),
                "company_name": context_object.get('company_data_payload', {}).get('company_name'),
                "project_name": context_object.get('company_data_payload', {}).get('project_name'),
                "company_rep": context_object.get('company_data_payload', {}).get('company_rep'),
                "ai_channel_config": channel_ai_config,
                "all_channel_contact_info": {}
            }
            
            # --- Build all_channel_contact_info dictionary ---
            log.debug("Building all_channel_contact_info...") # Use injected logger
            built_contact_info = {}
            channel_config = context_object.get('company_data_payload', {}).get('channel_config', {})
            # Define mapping from channel type to its primary contact identifier key
            contact_key_map = {
                'whatsapp': 'company_whatsapp_number',
                'email': 'company_email_address'
                # Add mappings for other future channels here
            }
            
            for channel_name, config in channel_config.items():
                contact_key = contact_key_map.get(channel_name)
                if contact_key and isinstance(config, dict):
                    contact_value = config.get(contact_key)
                    # Check if value exists, is a string, and is not empty after stripping whitespace
                    if contact_value and isinstance(contact_value, str) and contact_value.strip():
                        built_contact_info[channel_name] = contact_value.strip()
                        log.debug(f"Added contact info for channel '{channel_name}'") # Use injected logger
                    else:
                         log.debug(f"No valid contact info found for channel '{channel_name}' using key '{contact_key}'") # Use injected logger
                elif contact_key:
                     log.warning(f"Config for channel '{channel_name}' is not a dictionary. Skipping contact info extraction.") # Use injected logger
            
            # Add the built dictionary to conversation_details
            conversation_details["all_channel_contact_info"] = built_contact_info

            log.debug(f"Conversation details prepared for OpenAI: { {k: v for k, v in conversation_details.items() if k != 'project_data'} }...") # Use injected logger # Avoid logging large project_data

            # --- Call OpenAI Service ---
            log.info(f"Calling OpenAI service for conversation {conv_id}...")
            # Pass the secret value (dict or potentially string) directly to the AI service
            openai_result = ai_service.process_message_with_ai(conversation_details, openai_secret_value)


            # --- Handle OpenAI Result ---
            if not openai_result:
                # The service function already logs detailed errors
                log.error(f"OpenAI processing failed for conversation {conv_id}. Raising error to fail SQS message.") # Use injected logger
                raise RuntimeError(f"OpenAI processing failed for conversation {conv_id}")
            else:
                # Extract results for potential use in later steps
                content_variables = openai_result.get('content_variables')
                thread_id = openai_result.get('thread_id') # Crucial for Step 8 (DB Update)
                # We might also use token counts later for logging/metrics
                log.info(f"OpenAI processing successful for conversation {conv_id}. Received thread_id: {thread_id}") # Use injected logger

            # 7. Send Message via Channel Provider (Twilio WhatsApp API)
            #    - Uses injected msg_service module
            log.info(f"Initiating Step 7: Send message via Twilio for conversation {conv_id}") # Use injected logger
            
            logger.info(f"Initiating Step 7: Send message via Twilio for conversation {conv_id}")
            
            # --- Extract required data for Twilio ---
            # We already have 'twilio_creds' from Step 5
            # We already have 'openai_result' containing 'content_variables' from Step 6
            
            # Get recipient telephone number from context object
            recipient_tel = context_object.get('frontend_payload', {}).get('recipient_data', {}).get('recipient_tel')
            if not recipient_tel:
                log.error(f"Missing recipient_tel in context_object for conversation {conv_id}. Cannot send Twilio message.") # Use injected logger
                raise ValueError("Missing recipient_tel for Twilio")

            # Get the Twilio sender number from context_object (company config)
            # channel_method was previously validated and exists
            company_channel_config = context_object.get('company_data_payload', {}).get('channel_config', {})
            whatsapp_config = company_channel_config.get(channel_method, {})
            twilio_sender_number = whatsapp_config.get('company_whatsapp_number')
            if not twilio_sender_number:
                log.error(f"Missing 'company_whatsapp_number' in company_data_payload.channel_config.{channel_method} for conversation {conv_id}. Cannot send Twilio message.") # Use injected logger
                raise ValueError(f"Missing Twilio sender number configuration for {channel_method}")

            # Get the content variables from the OpenAI result
            content_variables_dict = openai_result.get('content_variables')
            if content_variables_dict is None: # Check for None explicitly, as empty dict might be valid
                 log.error(f"Missing 'content_variables' in openai_result for conversation {conv_id}. Cannot send Twilio message.") # Use injected logger
                 raise ValueError("Missing content_variables from OpenAI result")

            # --- Call Twilio Service ---
            # Pass twilio_creds directly as it contains SID, token, and template SID
            # twilio_result = send_whatsapp_template_message( ... )
            twilio_result = msg_service.send_whatsapp_template_message(
                twilio_config=twilio_creds,
                recipient_tel=recipient_tel,
                twilio_sender_number=twilio_sender_number, # Pass sender number separately
                content_variables=content_variables_dict
            )

            # --- Handle Twilio Result ---
            if not twilio_result:
                # The twilio_service function already logs detailed errors
                log.error(f"Failed to send WhatsApp message via Twilio for conversation {conv_id}. Raising error to fail SQS message.") # Use injected logger
                raise RuntimeError(f"Failed to send Twilio message for conversation {conv_id}")
            else:
                # Extract SID and Body from the result dictionary
                message_sid = twilio_result.get('message_sid')
                message_body = twilio_result.get('body')
                log.info(f"Successfully sent message via Twilio for conversation {conv_id}. Message SID: {message_sid}") # Use injected logger
                log.debug(f"Twilio reported message body: {message_body}") # Use injected logger
                # Store the message_sid if needed for DB update in Step 8
                # conversation_data['last_twilio_message_sid'] = message_sid # Example

            # 8. Update DynamoDB with final status, message history, thread ID etc.
            #    - Uses injected db_service module
            log.info(f"Initiating Step 8: Finalize conversation record updates for {conv_id}") # Use injected logger (Placeholder removed)
            # --- Add logic here to update DynamoDB --- # Placeholder removed
            # --- Prepare data for DynamoDB Update ---
            # Generate timestamp for the message
            message_timestamp = datetime.now(timezone.utc).isoformat()

            # Construct the message object to append to the history
            new_message_object = {
                "message_id": message_sid,  # From twilio_result['message_sid']
                "timestamp": message_timestamp,
                "role": "assistant",      # This message is from the assistant
                "content": message_body,    # From twilio_result['body']
                # Token usage from OpenAI for this message generation
                "prompt_tokens": openai_result.get("prompt_tokens"),
                "completion_tokens": openai_result.get("completion_tokens"),
                "total_tokens": openai_result.get("total_tokens")
            }
            log.debug(f"Prepared new message object for DB history: {new_message_object}") # Use injected logger

            # Other fields to update (examples)
            openai_thread_id = openai_result.get('thread_id')
            new_conversation_status = "initial_message_sent"
            task_complete_status = 1 # Assuming 1 means complete for LSI
            final_updated_at = message_timestamp # Use the same timestamp
            # processing_time_ms = ... # Need to calculate total Lambda execution time

            # --- Determine Primary Key for Update ---
            if channel_method in ['whatsapp', 'sms']:
                primary_channel_key = recipient_tel # recipient_tel extracted in Step 7
            elif channel_method == 'email':
                # Need recipient_email if channel is email
                recipient_email = context_object.get('frontend_payload', {}).get('recipient_data', {}).get('recipient_email')
                if not recipient_email:
                     log.error(f"Missing recipient_email in context_object for email channel. Cannot determine primary_channel for update.") # Use injected logger
                     raise ValueError("Missing recipient_email for email channel update")
                primary_channel_key = recipient_email
            else:
                # Should not happen if validation passed, but good to check
                log.error(f"Unsupported channel_method '{channel_method}' encountered during update step.") # Use injected logger
                raise ValueError(f"Unsupported channel_method '{channel_method}' for update")

            # --- Calculate Processing Time ---
            processing_end_time = time.time()
            processing_duration_ms = int((processing_end_time - processing_start_time) * 1000)
            log.debug(f"Total processing time for record {record_id}: {processing_duration_ms} ms") # Use injected logger

            # --- Call DynamoDB Service function ---
            # update_successful = update_conversation_after_send( ... )
            update_successful = db_service.update_conversation_after_send(
                primary_channel_pk=primary_channel_key,
                conversation_id_sk=conv_id,
                new_status=new_conversation_status,
                updated_at_ts=final_updated_at, # Use the timestamp generated for the message
                thread_id=openai_thread_id,     # From openai_result
                processing_time_ms=processing_duration_ms,
                message_to_append=new_message_object # The constructed message map
            )

            if not update_successful:
                log.error(f"Failed to update DynamoDB record for conversation {conv_id} in Step 8.") # Use injected logger
                # Fail the SQS message processing if DB update fails - REMOVED as per LLD
                # raise RuntimeError(f"DynamoDB final update failed for {conv_id}")
                # Log CRITICALLY, but DO NOT raise an error. Allow SQS message deletion
                # to prevent duplicate Twilio sends.
                log.critical( # Use injected logger
                    f"CRITICAL: Message sent (SID: {message_sid}) for conversation {conv_id}, "
                    f"but final DynamoDB update failed. Manual intervention required to update record. "
                    f"Data to update: status='{new_conversation_status}', thread_id='{openai_thread_id}', "
                    f"timestamp='{final_updated_at}', processing_time='{processing_duration_ms}', "
                    f"message_object='{new_message_object}'"
                )
                # Note: We proceed without raising an error here.
            else:
                log.info(f"DynamoDB final update successful for {conv_id}") # Use injected logger

            # 9. Stop SQS Heartbeat (Success Path)
            if heartbeat and heartbeat.running:
                heartbeat.stop()
                log.info(f"SQS Heartbeat stopped for {record_id}") # Use injected logger
                # Check if the heartbeat itself encountered an error
                heartbeat_error = heartbeat.check_for_errors()
                if heartbeat_error:
                    # If heartbeat failed, we should probably consider the overall processing failed
                    # as the message might become visible again unexpectedly.
                    log.error(f"SQS Heartbeat for {record_id} encountered an error: {heartbeat_error}") # Use injected logger
                    raise heartbeat_error # Re-raise the error to fail the record processing
            elif heartbeat:
                 log.info(f"SQS Heartbeat for {record_id} was not running or already stopped before explicit stop call.") # Use injected logger
            else:
                 log.debug(f"No active SQS Heartbeat to stop for {record_id}.") # Use injected logger

            # 10. Delete SQS message (Handled by successful Lambda return with SQS trigger)
            log.info(f"Successfully processed record {record_id}") # Use injected logger
            successful_record_ids.append(record_id)
            # --- End Detailed Processing Steps ---

        except Exception as e:
            log.exception(f"Error processing record {record_id}: {str(e)}") # Use injected logger
            failed_record_ids.append(record_id)
            # Ensure heartbeat is stopped even on failure
            if heartbeat and heartbeat.running:
               heartbeat.stop()
               log.info(f"SQS Heartbeat stopped after error for {record_id}") # Use injected logger
            elif heartbeat:
                 log.info(f"SQS Heartbeat for {record_id} was not running or already stopped when error occurred.") # Use injected logger
            else:
                 log.debug(f"No active SQS Heartbeat during error handling for {record_id}.") # Use injected logger

            # --- ADDED: Attempt to update DynamoDB status on failure --- #
            # *** ADD EXTRA LOGGING IN EXCEPTION HANDLER ***
            log.error(f"Caught exception in main handler for record {record_id}. Type: {type(e).__name__}, Message: {str(e)}. Attempting to update status.")
            
            # We need primary_channel and conversation_id. These might not be set if
            # parsing/validation failed early. Add checks.
            primary_channel_val = None
            conv_id_val = None
            try:
                # Try to get IDs if context_object was parsed
                if 'context_object' in locals() and context_object:
                    conv_id_val = context_object.get('conversation_data', {}).get('conversation_id')
                    channel_method_val = context_object.get('frontend_payload', {}).get('request_data', {}).get('channel_method')
                    if channel_method_val in ['whatsapp', 'sms']:
                        primary_channel_val = context_object.get('frontend_payload', {}).get('recipient_data', {}).get('recipient_tel')
                    elif channel_method_val == 'email':
                         primary_channel_val = context_object.get('frontend_payload', {}).get('recipient_data', {}).get('recipient_email')
            except Exception as id_ex:
                log.warning(f"Could not reliably determine primary_channel/conversation_id during error handling: {id_ex}")

            if primary_channel_val and conv_id_val:
                failure_status_code = "failed_unknown"
                # Crude check for specific failure types based on exception
                if isinstance(e, ValueError) and ("credentials" in str(e).lower() or "secret" in str(e).lower()):
                    failure_status_code = "failed_secrets_fetch"
                elif isinstance(e, ValueError) and ("openai" in str(e).lower() or "ai process" in str(e).lower()):
                     failure_status_code = "failed_to_process_ai"
                elif isinstance(e, RuntimeError) and ("twilio" in str(e).lower() or "send message" in str(e).lower()):
                    failure_status_code = "failed_to_send_message"
                # Add more specific status codes based on potential exceptions
                
                # *** ADD EXTRA LOGGING BEFORE DB UPDATE ***
                log.info(f"Updating failure status for conv_id '{conv_id_val}' on channel '{primary_channel_val}' to '{failure_status_code}' due to caught exception.")
                
                db_service.update_conversation_status_on_failure(
                    primary_channel_pk=primary_channel_val,
                    conversation_id_sk=conv_id_val,
                    failure_status=failure_status_code,
                    failure_reason=f"Unhandled exception: {type(e).__name__} - {str(e)[:200]}", # Truncate long errors
                    log=log # Pass injected logger
                )
            else:
                 log.error(f"Cannot update DynamoDB failure status for record {record_id} as identifiers could not be determined.")
            # --- END ADDED SECTION --- #

    log.info(f"Processing complete. Successful: {len(successful_record_ids)}, Failed: {len(failed_record_ids)}") # Use injected logger

    # Return response indicating partial batch failure if any records failed
    response = {"batchItemFailures": []}
    if failed_record_ids:
        response["batchItemFailures"] = [{"itemIdentifier": item_id} for item_id in failed_record_ids]
        log.warning(f"Returning batch item failures for IDs: {failed_record_ids}") # Use injected logger

    return response

# Remove placeholder functions as they are now imported from service modules
# # --- Helper Function Placeholders ---
# ... (Remove all placeholder function definitions below) ...

if __name__ == '__main__':
    # Example for local testing (optional) - This section may need adjustment
    # It likely won't work directly without providing the injected dependencies
    # or ensuring the default imports work in this context.
    # Consider using actual unit tests instead for local validation.
    logger.setLevel(logging.DEBUG)
    logger.info("Running basic local test (Note: DI Refactoring may affect this)...")
    # ... (rest of __main__ block remains, but with the caveat) ...
    # Call the handler - THIS WILL LIKELY FAIL without providing mocks/dependencies
    # result = lambda_handler(dummy_event, {})
    logger.info(f"Local test needs review after DI refactoring.")


    # Create a dummy SQS event
    dummy_event = {
      "Records": [
        {
          "messageId": "dummy-message-id-1",
          "receiptHandle": "dummy-receipt-handle-1",
          "body": "{\"context_object\": {\"message\": \"Hello from local test\"}}", # Simplified context
          "attributes": {
            "ApproximateReceiveCount": "1",
            "SentTimestamp": "1523232000000",
            "SenderId": "dummy-sender-id",
            "ApproximateFirstReceiveTimestamp": "1523232000001"
          },
          "messageAttributes": {},
          "md5OfBody": "dummy-md5",
          "eventSource": "aws:sqs",
          "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:MyQueue",
          "awsRegion": "us-east-1"
        }
      ]
    }
    # Call the handler
    result = lambda_handler(dummy_event, {})
    logger.info(f"Local test result: {result}") 