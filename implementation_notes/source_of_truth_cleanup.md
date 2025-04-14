# Source of Truth & Cleanup Plan

This document outlines the files that constitute the active source code based on the successful deployment and testing configuration achieved on [Date - Please Fill In], and identifies files/directories that are likely safe to remove.

**Goal:** Clean up duplicate or unnecessary files within the Lambda source directories (`src_dev/.../app/lambda_pkg/`) to avoid confusion and ensure the repository reflects only the active code. **Perform this cleanup on a new branch.**

## Source of Truth Files

The following files/patterns represent the active code used by the current SAM configuration and passing unit tests:

**1. Channel Router (`src_dev/channel_router/app/`)**

*   **Dependencies:** `src_dev/channel_router/app/requirements.txt` (This file in the `app/` dir is used by `sam build`).
*   **Package Root:** `src_dev/channel_router/app/lambda_pkg/__init__.py`
*   **Handler Code:** `src_dev/channel_router/app/lambda_pkg/index.py`
*   **Core Logic:** Files directly within `src_dev/channel_router/app/lambda_pkg/core/` (e.g., `context_builder.py`)
*   **Services:** Files directly within `src_dev/channel_router/app/lambda_pkg/services/` (e.g., `dynamodb_service.py`, `sqs_service.py`)
*   **Utilities:** Files directly within `src_dev/channel_router/app/lambda_pkg/utils/` (e.g., `request_parser.py`, `response_builder.py`, `validators.py`)

**2. WhatsApp Processor (`src_dev/channel_processor/whatsapp/app/`)**

*   **Dependencies:** `src_dev/channel_processor/whatsapp/app/requirements.txt` (This file in the `app/` dir is used by `sam build`).
*   **Package Root:** `src_dev/channel_processor/whatsapp/app/lambda_pkg/__init__.py`
*   **Handler Code:** `src_dev/channel_processor/whatsapp/app/lambda_pkg/index.py`
*   **Services:** Files directly within `src_dev/channel_processor/whatsapp/app/lambda_pkg/services/` (e.g., `dynamodb_service.py`, `openai_service.py`, `secrets_manager_service.py`, `twilio_service.py`)
*   **Utilities:** Files directly within `src_dev/channel_processor/whatsapp/app/lambda_pkg/utils/` (e.g., `context_utils.py`, `sqs_heartbeat.py`)

## Files/Directories Likely Safe for Removal

Based on the file listing provided and the working configuration, the following items within the `lambda_pkg` directories (for both `channel_router` and `whatsapp_processor`) are likely **unused backups, artifacts, or duplicates** and should be reviewed and potentially deleted:

*   Any files with numbers appended (e.g., `index 2.py`, `index 3.py`, `requirements 2.txt`, `requirements 3.txt`).
*   Any `.zip` files (e.g., `whatsapp_processor_deployment_package.zip`). These are build artifacts, not source code.
*   The `samples/` directory *if it exists within `lambda_pkg`*. The main project `samples/` directory should be kept.
*   The `package/` directory *if it exists within `lambda_pkg`*. This often relates to older build methods.
*   Any other numbered or seemingly duplicated `.py` files within `utils/`, `services/`, `core/`.

**Cleanup Steps (on a new branch):**

1.  Navigate into `src_dev/channel_router/app/lambda_pkg/`.
2.  Carefully review and delete the numbered/duplicate/artifact files identified above.
3.  Navigate into `src_dev/channel_processor/whatsapp/app/lambda_pkg/`.
4.  Carefully review and delete the numbered/duplicate/artifact files identified above.
5.  After cleanup, run `pytest tests/unit/` again to ensure no active code was accidentally removed.
6.  Commit the changes on the new branch.

This cleanup will make the source directories much clearer and easier to maintain. 