import pytest
import os
import json
import time
# Import openai for exception types
import openai
from unittest.mock import patch, MagicMock, call
from openai.types.beta.thread import Thread
from openai.types.beta.threads.message import Message as ThreadMessage
from openai.types.beta.threads.message_content import TextContentBlock
# Import Run, Usage, and LastError
from openai.types.beta.threads.run import Run, Usage, LastError
from openai.pagination import SyncCursorPage # For mocking list responses

# Module to test
from src_dev.channel_processor.whatsapp.app.services import openai_service
# Reload the module to re-initialize client with mocked env vars/moto
from importlib import reload

# --- Test Data ---

@pytest.fixture
def mock_openai_credentials():
    return {"ai_api_key": "sk-testkey12345"}

@pytest.fixture
def mock_conversation_details():
    return {
        "conversation_id": "conv_openai_test_678",
        "assistant_id": "asst_mock_sender_abc",
        "project_data": {"product": "Gizmo", "offer": "10% off"},
        "recipient_data": {"recipient_tel": "+1112223333", "name": "Test User"},
        "company_name": "Test Corp",
        "project_name": "Gizmo Promo",
        "company_rep": {"name": "Sales Rep"},
        "all_channel_contact_info": {"whatsapp": "+19998887777"}
    }

@pytest.fixture
def mock_openai_client():
    mock_client = MagicMock()

    # Mock thread creation
    mock_client.beta.threads.create.return_value = Thread(
        id="thread_mock_123", created_at=int(time.time()), object="thread"
    )

    # Mock message creation
    mock_client.beta.threads.messages.create.return_value = ThreadMessage(
        id="msg_mock_user_456", thread_id="thread_mock_123", role="user",
        content=[], created_at=int(time.time()), object="thread.message",
        status="completed"
    )

    # Mock run creation and retrieval (simulate polling)
    mock_run_initial = Run(
        id="run_mock_789", thread_id="thread_mock_123", assistant_id="asst_mock_sender_abc",
        status="queued", created_at=int(time.time()), object="thread.run",
        instructions="", model="", parallel_tool_calls=False, tools=[],
        usage=None # Usage only populated on completion
    )
    mock_run_in_progress = Run(
        id="run_mock_789", thread_id="thread_mock_123", assistant_id="asst_mock_sender_abc",
        status="in_progress", created_at=int(time.time()), object="thread.run",
        instructions="", model="", parallel_tool_calls=False, tools=[],
        usage=None
    )
    mock_run_completed = Run(
        id="run_mock_789", thread_id="thread_mock_123", assistant_id="asst_mock_sender_abc",
        status="completed", created_at=int(time.time()+1), completed_at=int(time.time()+1),
        object="thread.run",
        instructions="", model="", parallel_tool_calls=False, tools=[],
        usage=Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
    )
    mock_client.beta.threads.runs.create.return_value = mock_run_initial
    # Simulate polling: queued -> in_progress -> completed
    mock_client.beta.threads.runs.retrieve.side_effect = [
        mock_run_initial,
        mock_run_in_progress,
        mock_run_completed
    ]

    # Mock message listing
    mock_assistant_response = {"1": "Hello", "2": "Test User", "3": "Gizmo", "4": "10% off"}
    mock_assistant_message = ThreadMessage(
        id="msg_mock_asst_abc", thread_id="thread_mock_123", role="assistant",
        content=[
            TextContentBlock(
                type='text',
                text={
                    'value': json.dumps(mock_assistant_response),
                    'annotations': []
                }
            )
        ],
        created_at=int(time.time()), object="thread.message",
        status="completed"
    )
    mock_user_message = ThreadMessage(
        id="msg_mock_user_456", thread_id="thread_mock_123", role="user",
        content=[], created_at=int(time.time()), object="thread.message",
        status="completed"
    )
    # Simulate SyncCursorPage response (important for .data access)
    # Note: .data contains list of messages, newest first
    message_list_page = SyncCursorPage(data=[mock_assistant_message, mock_user_message], _get_page=lambda: None)
    mock_client.beta.threads.messages.list.return_value = message_list_page

    return mock_client

# --- Auto-used Patch for OpenAI Client ---
@pytest.fixture(autouse=True)
def patch_openai_client(mock_openai_client):
    with patch('src_dev.channel_processor.whatsapp.app.services.openai_service.openai.OpenAI') as mock_openai_constructor:
        mock_openai_constructor.return_value = mock_openai_client
        yield mock_openai_constructor, mock_openai_client

# --- Test Cases ---

def test_process_message_success(mock_conversation_details, mock_openai_credentials, patch_openai_client):
    """Test the successful end-to-end flow."""
    _, mock_client = patch_openai_client
    expected_response = {"1": "Hello", "2": "Test User", "3": "Gizmo", "4": "10% off"}

    result = openai_service.process_message_with_ai(
        mock_conversation_details, mock_openai_credentials
    )

    assert result is not None
    assert result["content_variables"] == expected_response
    assert result["thread_id"] == "thread_mock_123"
    assert result["prompt_tokens"] == 100
    assert result["completion_tokens"] == 50
    assert result["total_tokens"] == 150

    # Verify client calls
    mock_client.beta.threads.create.assert_called_once()
    mock_client.beta.threads.messages.create.assert_called_once()
    # Check message content contains key details
    message_content = mock_client.beta.threads.messages.create.call_args[1]['content']
    assert "Test Corp" in message_content
    assert "Test User" in message_content
    assert "Gizmo" in message_content
    assert "Sales Rep" in message_content
    assert "+19998887777" in message_content
    mock_client.beta.threads.runs.create.assert_called_once_with(
        thread_id="thread_mock_123",
        assistant_id=mock_conversation_details['assistant_id']
    )
    # Called 3 times in the polling loop (queued, in_progress, completed)
    assert mock_client.beta.threads.runs.retrieve.call_count == 3
    mock_client.beta.threads.runs.retrieve.assert_called_with(thread_id="thread_mock_123", run_id="run_mock_789")
    mock_client.beta.threads.messages.list.assert_called_once_with(thread_id="thread_mock_123", order='desc')

def test_missing_api_key(mock_conversation_details, caplog):
    """Test failure when API key is missing."""
    result = openai_service.process_message_with_ai(mock_conversation_details, {})
    assert result is None
    assert "Missing 'ai_api_key' in openai_credentials." in caplog.text

def test_missing_assistant_id(mock_conversation_details, mock_openai_credentials, caplog):
    """Test failure when Assistant ID is missing."""
    details = mock_conversation_details.copy()
    del details['assistant_id']
    result = openai_service.process_message_with_ai(details, mock_openai_credentials)
    assert result is None
    assert f"Missing Assistant ID for conversation {mock_conversation_details['conversation_id']}" in caplog.text

def test_openai_init_fails(mock_conversation_details, mock_openai_credentials, patch_openai_client, caplog):
    """Test failure during OpenAI client initialization."""
    mock_constructor, _ = patch_openai_client
    mock_constructor.side_effect = Exception("Init Failed")
    result = openai_service.process_message_with_ai(mock_conversation_details, mock_openai_credentials)
    assert result is None
    assert "Failed to initialize OpenAI client" in caplog.text

def test_thread_create_fails(mock_conversation_details, mock_openai_credentials, patch_openai_client, caplog):
    """Test failure during thread creation."""
    _, mock_client = patch_openai_client
    # Use imported openai module
    mock_client.beta.threads.create.side_effect = openai.APIError("Create Thread Failed", request=None, body=None)
    result = openai_service.process_message_with_ai(mock_conversation_details, mock_openai_credentials)
    assert result is None
    assert "OpenAI API Error" in caplog.text
    assert "Create Thread Failed" in caplog.text

def test_message_create_fails(mock_conversation_details, mock_openai_credentials, patch_openai_client, caplog):
    """Test failure during message creation."""
    _, mock_client = patch_openai_client
    mock_client.beta.threads.messages.create.side_effect = Exception("Create Message Failed")
    result = openai_service.process_message_with_ai(mock_conversation_details, mock_openai_credentials)
    assert result is None
    assert "Failed to add initial message to thread" in caplog.text

def test_run_create_fails(mock_conversation_details, mock_openai_credentials, patch_openai_client, caplog):
    """Test failure during run creation."""
    _, mock_client = patch_openai_client
    # Use imported openai module
    mock_client.beta.threads.runs.create.side_effect = openai.APIError("Create Run Failed", request=None, body=None)
    result = openai_service.process_message_with_ai(mock_conversation_details, mock_openai_credentials)
    assert result is None
    assert "OpenAI API Error" in caplog.text
    assert "Create Run Failed" in caplog.text

@pytest.mark.parametrize("terminal_status", ["failed", "cancelled", "expired"])
def test_run_fails_terminally(mock_conversation_details, mock_openai_credentials, patch_openai_client, terminal_status, caplog):
    """Test failure when run enters a terminal failure state."""
    _, mock_client = patch_openai_client
    mock_run_failed = Run(
        id="run_mock_failed", thread_id="thread_mock_123", assistant_id="asst_mock_sender_abc",
        status=terminal_status, created_at=int(time.time()), object="thread.run",
        last_error=LastError(code="server_error", message="Simulated run failure"),
        instructions="", model="", parallel_tool_calls=False, tools=[]
    )
    # Directly mock create AND retrieve for this specific test case
    mock_client.beta.threads.runs.create.return_value = mock_run_failed
    mock_client.beta.threads.runs.retrieve.side_effect = [mock_run_failed] # Ensure retrieve returns failed state

    result = openai_service.process_message_with_ai(mock_conversation_details, mock_openai_credentials)
    assert result is None
    assert f"Run run_mock_failed ended with terminal status: {terminal_status}" in caplog.text

def test_run_requires_action(mock_conversation_details, mock_openai_credentials, patch_openai_client, caplog):
    """Test failure when run requires action (not implemented)."""
    _, mock_client = patch_openai_client
    mock_run_action = Run(
        id="run_mock_action", thread_id="thread_mock_123", assistant_id="asst_mock_sender_abc",
        status="requires_action", created_at=int(time.time()), object="thread.run",
        instructions="", model="", parallel_tool_calls=False, tools=[]
    )
    # Directly mock create AND retrieve for this specific test case
    mock_client.beta.threads.runs.create.return_value = mock_run_action
    mock_client.beta.threads.runs.retrieve.side_effect = [mock_run_action] # Ensure retrieve returns requires_action

    result = openai_service.process_message_with_ai(mock_conversation_details, mock_openai_credentials)
    assert result is None
    assert "Run run_mock_action requires action" in caplog.text

def test_run_polling_timeout(mock_conversation_details, mock_openai_credentials, patch_openai_client, caplog):
    """Test failure due to polling timeout."""
    _, mock_client = patch_openai_client
    # Mock retrieve to always return 'in_progress'
    mock_run_in_progress = Run(
        id="run_mock_timeout", thread_id="thread_mock_123", assistant_id="asst_mock_sender_abc",
        status="in_progress", created_at=int(time.time()), object="thread.run",
        instructions="", model="", parallel_tool_calls=False, tools=[]
    )
    mock_client.beta.threads.runs.create.return_value = mock_run_in_progress # Start in progress
    # Explicitly mock retrieve for this test to always return in_progress
    mock_client.beta.threads.runs.retrieve.side_effect = None # Clear previous fixture side_effect
    mock_client.beta.threads.runs.retrieve.return_value = mock_run_in_progress

    # Patch time.time and time.sleep to force a timeout
    # Make polling interval effectively 0 and advance time beyond timeout
    start_time = time.time()
    with patch('src_dev.channel_processor.whatsapp.app.services.openai_service.time.sleep'), \
         patch('src_dev.channel_processor.whatsapp.app.services.openai_service.time.time') as mock_time:
        # Use a function for side_effect to handle multiple calls
        call_count = 0
        def time_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 5: # Allow a few initial calls
                 return start_time + call_count
            else: # Then jump time forward to trigger timeout
                 return start_time + 600
        mock_time.side_effect = time_side_effect

        result = openai_service.process_message_with_ai(mock_conversation_details, mock_openai_credentials)

    assert result is None
    assert "Polling timeout exceeded for run run_mock_timeout" in caplog.text

def test_no_assistant_message(mock_conversation_details, mock_openai_credentials, patch_openai_client, caplog):
    """Test failure when no assistant message is found after successful run."""
    _, mock_client = patch_openai_client
    # Mock messages.list to return only the user message
    mock_user_message = ThreadMessage(
        id="msg_mock_user_456", thread_id="thread_mock_123", role="user",
        content=[], created_at=int(time.time()), object="thread.message",
        status="completed"
    )
    message_list_page = SyncCursorPage(data=[mock_user_message], _get_page=lambda: None)
    mock_client.beta.threads.messages.list.return_value = message_list_page

    result = openai_service.process_message_with_ai(mock_conversation_details, mock_openai_credentials)
    assert result is None
    assert "No assistant message with text content found" in caplog.text

def test_assistant_message_not_json(mock_conversation_details, mock_openai_credentials, patch_openai_client, caplog):
    """Test failure when the assistant message content is not valid JSON."""
    _, mock_client = patch_openai_client
    # Modify the message list return value
    not_json_content = "This is not JSON."
    mock_assistant_message_bad = ThreadMessage(
        id="msg_mock_asst_bad", thread_id="thread_mock_123", role="assistant",
        content=[
             TextContentBlock(
                 type='text',
                 text={
                     'value': not_json_content,
                     'annotations': []
                 }
             )
        ],
        created_at=int(time.time()), object="thread.message",
        status="completed"
    )
    message_list_page = SyncCursorPage(data=[mock_assistant_message_bad], _get_page=lambda: None)
    mock_client.beta.threads.messages.list.return_value = message_list_page

    result = openai_service.process_message_with_ai(mock_conversation_details, mock_openai_credentials)
    assert result is None
    assert "Failed to parse assistant message content as JSON" in caplog.text
    assert not_json_content in caplog.text

def test_assistant_message_wrong_json_structure(mock_conversation_details, mock_openai_credentials, patch_openai_client, caplog):
    """Test failure when the assistant message JSON lacks expected keys."""
    _, mock_client = patch_openai_client
    # Modify the message list return value
    wrong_json_content = json.dumps({"wrong_key": "value"}) # Missing "1", "2", etc.
    mock_assistant_message_wrong = ThreadMessage(
        id="msg_mock_asst_wrong", thread_id="thread_mock_123", role="assistant",
        content=[
             TextContentBlock(
                 type='text',
                 text={
                     'value': wrong_json_content,
                     'annotations': []
                 }
             )
        ],
        created_at=int(time.time()), object="thread.message",
        status="completed"
    )
    message_list_page = SyncCursorPage(data=[mock_assistant_message_wrong], _get_page=lambda: None)
    mock_client.beta.threads.messages.list.return_value = message_list_page

    result = openai_service.process_message_with_ai(mock_conversation_details, mock_openai_credentials)
    assert result is None
    assert "Parsed JSON response is not a dictionary or does not contain the expected keys" in caplog.text 