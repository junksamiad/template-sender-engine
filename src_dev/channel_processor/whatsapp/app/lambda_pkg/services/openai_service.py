"""
Handles interactions with the OpenAI API, specifically using Assistants.
"""
import openai
import logging
import os
from typing import Dict, Any, Optional
import json
import time

# Initialize logger
logger = logging.getLogger(__name__)

# OpenAI client initialization
# The OpenAI client is typically initialized when needed, using the API key.
# It can be initialized globally or within the function call.
# For simplicity, let's initialize it within the function for now.

def process_message_with_ai(conversation_details: Dict[str, Any], 
                            openai_credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Processes the incoming message context using the OpenAI Assistant API.

    Args:
        conversation_details: A dictionary containing relevant conversation data 
                                (e.g., extracted from context_object and DynamoDB record,
                                including conversation_id, project_data, ai_config details).
        openai_credentials: A dictionary containing the OpenAI API key 
                             (e.g., {"ai_api_key": "sk-..."}).

    Returns:
        A dictionary containing the AI's response and potentially metadata,
        or None if processing fails.
    """
    logger.info(f"Starting OpenAI processing for conversation: {conversation_details.get('conversation_id')}")

    # --- Extract necessary info ---
    try:
        api_key = openai_credentials.get('ai_api_key')
        if not api_key:
            logger.error("Missing 'ai_api_key' in openai_credentials.")
            return None
        
        # We'll need the assistant ID (template sender or replies?) based on conversation state
        # We'll need the project_data to potentially pass to the assistant
        # For now, let's assume we get these from conversation_details dict
        assistant_id = conversation_details.get('assistant_id') # Need to determine which one based on logic
        project_data = conversation_details.get('project_data')
        conversation_id = conversation_details.get('conversation_id')

        if not assistant_id:
            logger.error(f"Missing Assistant ID for conversation {conversation_id}")
            return None

    except KeyError as e:
        logger.error(f"Missing expected key in conversation_details for OpenAI processing: {e}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error extracting data for OpenAI processing: {e}")
        return False

    # --- Initialize OpenAI Client ---
    try:
        client = openai.OpenAI(api_key=api_key)
        logger.debug("OpenAI client initialized.")
    except Exception as e:
        logger.exception(f"Failed to initialize OpenAI client: {e}")
        return None

    # --- Core OpenAI Logic --- 
    try:
        # This function ONLY handles the initial message send.
        # Therefore, we ALWAYS create a new thread for each invocation.
        # This avoids potential thread history pollution if retries occur after thread creation
        # but before successful completion.
        logger.info(f"Creating new thread for initial message. Conversation: {conversation_id}")
        thread = client.beta.threads.create()
        current_thread_id = thread.id
        logger.info(f"Created new thread with id: {current_thread_id} for conversation {conversation_id}")
            
        # 4. Add the user's message (derived from project_data/initial prompt) to the thread.
        # Extract required data pieces from conversation_details
        project_data = conversation_details.get('project_data')
        recipient_data = conversation_details.get('recipient_data')
        company_name = conversation_details.get('company_name')
        project_name = conversation_details.get('project_name')
        company_rep = conversation_details.get('company_rep')
        all_channel_contact_info = conversation_details.get('all_channel_contact_info')

        # Validate essential data
        if not project_data or not recipient_data:
            logger.error(f"Missing project_data or recipient_data for conversation {conversation_id}. Cannot create initial message.")
            return None
            
        try:
            # Serialize complex objects to JSON for clarity
            project_data_json = json.dumps(project_data, indent=2)
            recipient_data_json = json.dumps(recipient_data, indent=2)
            company_rep_json = json.dumps(company_rep, indent=2) if company_rep else "Not provided"
            contact_info_json = json.dumps(all_channel_contact_info, indent=2) if all_channel_contact_info else "Not provided"
            
            # Construct the initial message content - ONLY include the data context.
            # Instructions and output format are defined in the Assistant configuration.
            initial_message_content = f"""
Initial context:

**Company & Project:**
- Company Name: {company_name or 'Not provided'}
- Project Name: {project_name or 'Not provided'}

**Company Representative(s):**
```json
{company_rep_json}
```

**Recipient Data:**
```json
{recipient_data_json}
```

**Company Contact Info:**
```json
{contact_info_json}
```

**Project-Specific Data:**
```json
{project_data_json}
```
"""            
            logger.debug(f"Adding initial message to thread {current_thread_id}")
            message = client.beta.threads.messages.create(
                thread_id=current_thread_id,
                role="user", # The initial prompt is considered a user message
                content=initial_message_content
            )
            logger.info(f"Successfully added initial message {message.id} to thread {current_thread_id}")

        except Exception as msg_err:
            logger.exception(f"Failed to add initial message to thread {current_thread_id}: {msg_err}")
            # Optional: Could attempt to delete the created thread here if adding the first message fails
            # client.beta.threads.delete(current_thread_id)
            return None

        # 5. Run the assistant on the thread using the appropriate assistant_id.
        logger.info(f"Running assistant {assistant_id} on thread {current_thread_id}")
        run = client.beta.threads.runs.create(
            thread_id=current_thread_id,
            assistant_id=assistant_id
            # We don't override instructions/model here, relying on Assistant config.
        )
        logger.info(f"Created run {run.id} with status {run.status}")
        run_id = run.id

        # 6. Poll for the run status until completed (or failed/expired).
        logger.info(f"Polling run {run_id} status...")
        start_time = time.time()
        # Set a reasonable timeout (e.g., 540 seconds / 9 minutes) 
        # Should be less than Lambda timeout minus buffer, 
        # and align reasonably with OpenAI's default run expiration (10 mins)
        polling_timeout_seconds = 540 
        polling_interval_seconds = 1 # Check status every second

        while True:
            # Check for overall timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > polling_timeout_seconds:
                logger.error(f"Polling timeout exceeded for run {run_id} after {polling_timeout_seconds} seconds.")
                # Optionally attempt to cancel the run
                # try: client.beta.threads.runs.cancel(thread_id=current_thread_id, run_id=run_id)
                # except Exception: pass 
                return None

            # Retrieve the run status
            run = client.beta.threads.runs.retrieve(
                thread_id=current_thread_id,
                run_id=run_id
            )

            logger.debug(f"Run {run_id} status: {run.status}")

            # Check terminal states
            if run.status == 'completed':
                logger.info(f"Run {run_id} completed successfully.")
                break # Exit the loop, proceed to get messages
            elif run.status in ['failed', 'cancelled', 'expired']:
                logger.error(f"Run {run_id} ended with terminal status: {run.status}. Details: {run.last_error}")
                return None # Stop processing
            elif run.status == 'requires_action':
                # This example doesn't use function calling, so this status indicates an issue.
                logger.error(f"Run {run_id} requires action, but function calling is not implemented. Status: {run.status}")
                # Ensure we return None here to indicate failure/stop processing
                return None
            
            # If still in progress or queued, wait and poll again
            time.sleep(polling_interval_seconds)

        # 7. Retrieve the latest messages from the thread after the run completes.
        logger.info(f"Run {run_id} completed. Retrieving messages from thread {current_thread_id}.")
        messages_response = client.beta.threads.messages.list(
            thread_id=current_thread_id,
            order='desc' # Default is desc (newest first)
        )
        # The response object is a SyncCursorPage[Message] 
        # We can access the messages via the .data attribute
        thread_messages = messages_response.data 

        if not thread_messages:
             logger.error(f"No messages found in thread {current_thread_id} after run {run_id} completed.")
             return None

        logger.info(f"Retrieved {len(thread_messages)} messages from thread {current_thread_id}.")

        # 8. Extract the relevant assistant response message(s).
        assistant_message_content = None
        for message in thread_messages:
            if message.role == 'assistant':
                # Assuming the first piece of content is the text response
                if message.content and len(message.content) > 0 and hasattr(message.content[0], 'text'):
                    assistant_message_content = message.content[0].text.value
                    logger.info(f"Found assistant message {message.id} with content.")
                    break # Stop after finding the first (most recent) assistant message
                else:
                    logger.warning(f"Assistant message {message.id} found but has no text content.")
                    # Continue searching in case there are older valid messages?
                    # For now, let's take the first assistant role message regardless.
                    break 
        
        if assistant_message_content is None:
            logger.error(f"No assistant message with text content found in thread {current_thread_id} after run {run_id}. Messages dump: {thread_messages}")
            return None
            
        logger.debug(f"Extracted assistant content: {assistant_message_content[:200]}...") # Log snippet

        # 9. Parse the extracted content as JSON and validate structure
        content_variables = None
        try:
            parsed_response = json.loads(assistant_message_content)
            
            # Validate the structure - CHANGED to only check if it's a dictionary
            # Check if it has the expected keys directly (since the schema name doesn't create a top-level key here)
            # if isinstance(parsed_response, dict) and all(k in parsed_response for k in ["1", "2", "3", "4"]):
            if isinstance(parsed_response, dict):
                content_variables = parsed_response # USE PARSED RESPONSE DIRECTLY
                # logger.info(f"Successfully parsed response and found expected keys. Assigning to content_variables.")
                logger.info(f"Successfully parsed response as dictionary. Assigning to content_variables.") # Updated log
            else:
                # logger.error(f"Parsed JSON response is not a dictionary or does not contain the expected keys ('1', '2', '3', '4'). Parsed type: {type(parsed_response)}, Parsed content: {parsed_response}")
                logger.error(f"Parsed JSON response is not a dictionary. Parsed type: {type(parsed_response)}, Parsed content: {parsed_response}") # Updated log
                content_variables = None # Indicate failure
                
        except json.JSONDecodeError as json_err:
            logger.error(f"Failed to parse assistant message content as JSON. Error: {json_err}. Content: {assistant_message_content}")
            # No need to set content_variables = None, it's already None
        except Exception as e:
             # Catch any other unexpected errors during parsing/validation
             logger.exception(f"Unexpected error parsing/validating assistant response: {e}. Content: {assistant_message_content}")
             content_variables = None # Ensure failure state

        # If parsing or validation failed, stop processing
        if content_variables is None:
            # Previous error logs explain the reason
            return None 

        # 10. Return the response content and the thread_id (for saving back to DynamoDB).
        # Extract token usage from the final run status object (retrieved during polling)
        prompt_tokens = run.usage.prompt_tokens if run and run.usage else 0
        completion_tokens = run.usage.completion_tokens if run and run.usage else 0
        total_tokens = run.usage.total_tokens if run and run.usage else 0

        logger.info(f"OpenAI processing successful for conversation {conversation_id}. Returning variables and thread ID.")
        return {
            "content_variables": content_variables,
            "thread_id": current_thread_id,
            "prompt_tokens": prompt_tokens, 
            "completion_tokens": completion_tokens, 
            "total_tokens": total_tokens
        }

    except openai.APIError as e:
        # Handle API errors returned by OpenAI
        logger.error(f"OpenAI API Error for conversation {conversation_id}: {e}")
        return None
    except Exception as e:
        # Handle other unexpected errors during OpenAI interaction
        logger.exception(f"Unexpected error during OpenAI processing for conversation {conversation_id}: {e}")
        return None

# Example usage (for testing if needed)
# if __name__ == '__main__':
#     # Add mock environment variables, creds, and details for testing
#     logging.basicConfig(level=logging.INFO)
#     mock_creds = {"ai_api_key": os.environ.get("OPENAI_API_KEY")}
#     mock_details = {
#         "conversation_id": "test_conv_123",
#         "assistant_id": "asst_cv_clarification_abc123", # Use a real test assistant ID
#         "thread_id": None, # Test thread creation
#         "project_data": {"clarificationPoints": [{"point": "Test point?"}]}
#     }
#     if mock_creds.get("ai_api_key"):
#         result = process_message_with_ai(mock_details, mock_creds)
#         if result:
#             print(f"Success: {result}")
#         else:
#             print("Failed")
#     else:
#         print("Skipping test: OPENAI_API_KEY environment variable not set.") 