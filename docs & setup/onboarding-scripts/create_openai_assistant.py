import os
import json
from openai import OpenAI
import sys

# --- Helper Functions ---
def get_multiline_input(prompt):
    """Gets multiline input from the user."""
    print(prompt + " (Type DONE on a new line when finished):")
    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "DONE":
                break
            lines.append(line)
        except EOFError:
            # Keep EOFError as a fallback, though DONE is preferred
            print("\nEOF detected, finishing input.")
            break
        except KeyboardInterrupt:
            print("\nCancelled by user.")
            sys.exit(1)
    return "\n".join(lines)

def get_json_input(prompt):
    """Gets JSON input from the user and validates it."""
    while True:
        # Use the updated get_multiline_input which now looks for DONE
        json_string = get_multiline_input(prompt)
        if not json_string.strip(): # Handle case where user just types DONE
             print("Empty input received. Please enter valid JSON or type DONE after pasting.")
             continue
        try:
            json_data = json.loads(json_string)
            print("JSON Schema parsed successfully.")
            return json_data
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}. Please try again.")

# --- Main Script ---
def create_assistant():
    print("--- OpenAI Assistant Creation Script ---")
    print("\nEnsure you have the correct OpenAI API Key ready for the target channel (WhatsApp, SMS, or Email).")

    # 1. Get API Key
    api_key = input("\nEnter the OpenAI API Key: ").strip()
    if not api_key:
        print("API Key cannot be empty. Exiting.")
        sys.exit(1)

    try:
        client = OpenAI(api_key=api_key)
        # Test the key with a simple call (optional but recommended)
        # client.models.list() 
        # print("API Key validated successfully.")
    except Exception as e:
        print(f"Error initializing OpenAI client or validating key: {e}")
        print("Please check your API key and network connection. Exiting.")
        sys.exit(1)

    # 2. Get Assistant Name
    print("\nAssistant Name Format Hint: #CompanyName#ProjectName#AssistantPurpose")
    assistant_name = input("Enter the Assistant Name: ").strip()
    if not assistant_name:
        print("Assistant Name cannot be empty. Exiting.")
        sys.exit(1)

    # 3. Get Model
    model_id = input("Enter the Model ID [default: gpt-4o-mini]: ").strip() or "gpt-4o-mini"

    # 4. Get Instructions
    instructions = get_multiline_input("\nEnter the System Instructions:")

    # 5. Get Function Calling / JSON Schema (Optional)
    tools = []
    add_function = input("\nAdd a Function Calling tool for structured JSON output? (y/N): ").strip().lower()
    if add_function == 'y':
        print("\n--- Define Function Tool ---")
        func_name = input("Enter the Function Name (e.g., content_variables): ").strip()
        if not func_name:
            print("Function Name cannot be empty. Skipping function tool.")
        else:
            func_desc = input("Enter a brief Function Description (optional): ").strip()
            print("\nEnter the JSON Schema for the function parameters:")
            # Use the specific 'schema' part as the parameters
            param_schema = get_json_input("(Paste the content of the 'schema' key from the OpenAI example):")

            function_tool = {
                "type": "function",
                "function": {
                    "name": func_name,
                    "description": func_desc,
                    "parameters": param_schema
                }
            }
            tools.append(function_tool)
            print("Function tool definition added.")

    # Confirmation
    print("\n--- Confirm Details ---")
    print(f"Assistant Name: {assistant_name}")
    print(f"Model: {model_id}")
    print("Instructions:")
    print(instructions)
    if tools:
        print("Tools:")
        print(json.dumps(tools, indent=2))
    else:
        print("Tools: None")

    confirm = input("\nProceed with creation? (Y/n): ").strip().lower()
    if confirm == 'n':
        print("Creation cancelled.")
        sys.exit(0)

    # Create Assistant
    print("\nCreating Assistant...")
    try:
        assistant = client.beta.assistants.create(
            name=assistant_name,
            instructions=instructions,
            tools=tools,
            model=model_id
        )
        print("\n--- Assistant Created Successfully! ---")
        print("Assistant Details:")
        # Pretty print the response object
        print(assistant.model_dump_json(indent=2))
        print("\n*******************************************************")
        print(f"IMPORTANT: Record the Assistant ID: {assistant.id}")
        print("*******************************************************")
        print("\nAdd this ID to the relevant 'assistant_id_*' field in the company-data-dev DynamoDB table.")

    except Exception as e:
        print(f"\nError creating assistant: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_assistant() 