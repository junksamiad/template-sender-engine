import os
import time
import json
from openai import OpenAI
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
# Replace with your actual API key or use environment variables
# Never commit your actual API key to version control!
client = OpenAI(api_key="YOUR_OPENAI_API_KEY")
ASSISTANT_ID = "asst_abc..." # Replace with your specific Assistant ID
STRUCTURED_OUTPUT_NAME = "content_variables" # The name you gave the schema/function
# --- End Configuration ---

if not ASSISTANT_ID:
    logging.error("Error: ASSISTANT_ID is not set in the script.")
    exit(1)


def main():
    thread_id = None # Initialize thread_id
    try:
        # 1. Create a new thread
        logging.info("Creating new thread...")
        thread = client.beta.threads.create()
        thread_id = thread.id
        logging.info(f"Created thread: {thread_id}")

        # 2. Add a user message (Use a prompt that should trigger the structured output based on Assistant instructions)
        logging.info("Adding user message to thread...")
        user_message_content = "Please generate the content variables based on your instructions."
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message_content,
        )
        logging.info(f"Added message: '{user_message_content}'")

        # 3. Create a run (We rely on Assistant config/instructions for structured output)
        logging.info(f"Creating run for assistant {ASSISTANT_ID}...")
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
            # Instructions can be overridden here if needed for testing
            # instructions="Ensure your final output is ONLY the required JSON object."
        )
        run_id = run.id
        logging.info(f"Run created: {run_id}, Initial Status: {run.status}")

        # 4. Poll for run completion
        start_time = time.time()
        polling_timeout_seconds = 120 # 2 minutes timeout for polling

        while run.status in ["queued", "in_progress", "cancelling"]:
            elapsed_time = time.time() - start_time
            if elapsed_time > polling_timeout_seconds:
                logging.error(f"Polling timeout exceeded for run {run_id}.")
                return

            time.sleep(2) # Wait before polling again
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            logging.info(f"Run status: {run.status}")

        # 5. Check final run status and get messages
        if run.status == 'completed':
            logging.info("Run completed. Retrieving messages...")
            messages = client.beta.threads.messages.list(thread_id=thread_id, order="desc", limit=5)

            assistant_message_content = None
            for msg in messages.data:
                if msg.role == 'assistant':
                    if msg.content and len(msg.content) > 0 and hasattr(msg.content[0], 'text'):
                        assistant_message_content = msg.content[0].text.value
                        logging.info(f"Found assistant message {msg.id}. Content snippet: {assistant_message_content[:200]}...")
                        break # Found the latest assistant message
                    else:
                        logging.warning(f"Found assistant message {msg.id} but it has no text content.")

            if assistant_message_content:
                logging.info("Attempting to parse assistant message content as JSON...")
                try:
                    # Attempt to parse the *entire* text content as JSON
                    parsed_output = json.loads(assistant_message_content)
                    logging.info("Successfully parsed assistant message content as JSON.")
                    print("\n>>> Parsed Assistant Message Output:")
                    print(json.dumps(parsed_output, indent=2))

                    # Now, specifically check if it contains the desired structure
                    if isinstance(parsed_output, dict) and STRUCTURED_OUTPUT_NAME in parsed_output:
                        logging.info(f"Found expected key '{STRUCTURED_OUTPUT_NAME}'!")
                        content_vars = parsed_output[STRUCTURED_OUTPUT_NAME]
                        print("\n>>> Extracted Content Variables:")
                        print(json.dumps(content_vars, indent=2))
                    elif isinstance(parsed_output, dict) and all(k in parsed_output for k in ["1", "2", "3", "4"]):
                         logging.warning(f"Parsed output is a dictionary containing keys '1', '2', etc., but NOT nested under '{STRUCTURED_OUTPUT_NAME}'. This matches the schema but not the expected structure our Lambda code was looking for.")
                    else:
                        logging.warning(f"Parsed JSON does not contain the expected top-level key '{STRUCTURED_OUTPUT_NAME}'.")

                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse assistant message content as JSON: {e}")
                    print("\n>>> Raw Assistant Message Content (Not JSON):")
                    print(assistant_message_content)
            else:
                logging.error("No assistant message with text content found in the latest messages.")

        elif run.status == 'requires_action':
            logging.error("Run unexpectedly stopped requiring action. This indicates function/tool calling was triggered, which wasn't intended for this test.")
            logging.error(f"Required Action details: {run.required_action}")

        else:
            logging.error(f"Run failed with status: {run.status}. Error: {run.last_error}")

    except Exception as e:
        logging.exception(f"An error occurred: {e}")
    # finally:
        # Clean up the thread (optional - keep for inspection?)
        # try:
        #     if thread_id:
        #         logging.info(f"Deleting thread {thread_id}...")
        #         # client.beta.threads.delete(thread_id)
        # except Exception as e:
        #     logging.error(f"Failed to delete thread {thread_id}: {e}")
        # pass

if __name__ == "__main__":
    main() 